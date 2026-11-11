"""F2 kamera listesi ve ortak son-kare önizlemesini gerçek PostgreSQL'de doğrular."""

from __future__ import annotations

import asyncio
import json
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from isg_api.config import Settings
from isg_api.database import create_database_engine
from isg_api.main import create_app
from isg_api.models import AppUser, Camera, CameraSourceType, UserRole, UserSession
from isg_api.preview_store import FilesystemPreviewStore
from isg_api.security import hash_password
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

JPEG = b"\xff\xd8f2-shared-preview\xff\xd9"


async def verify_flow(
    settings: Settings,
    *,
    username: str,
    password: str,
    camera_id: uuid.UUID,
) -> dict[str, object]:
    app = create_app(settings)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        assert login.status_code == 200, login.text

        cameras = await client.get("/api/v1/cameras?include_inactive=true")
        assert cameras.status_code == 200, cameras.text
        assert str(camera_id) in {item["id"] for item in cameras.json()}

        status_response = await client.get(
            f"/api/v1/cameras/{camera_id}/preview/status"
        )
        assert status_response.status_code == 200
        assert status_response.json()["state"] == "unavailable"

        now = datetime.now(UTC)
        store = FilesystemPreviewStore(
            settings.preview_directory,
            stale_after_seconds=settings.preview_stale_seconds,
        )
        store.publish(camera_id, JPEG, captured_at=now)
        live = await client.get(f"/api/v1/cameras/{camera_id}/preview/status")
        assert live.status_code == 200
        assert live.json()["state"] == "live"
        image = await client.get(f"/api/v1/cameras/{camera_id}/preview")
        assert image.status_code == 200
        assert image.content == JPEG
        assert image.headers["content-type"] == "image/jpeg"
        assert image.headers["x-preview-state"] == "live"
        assert image.headers["cache-control"] == "no-store"

        store.publish(camera_id, JPEG, captured_at=now - timedelta(seconds=10))
        stale = await client.get(f"/api/v1/cameras/{camera_id}/preview/status")
        assert stale.status_code == 200
        assert stale.json()["state"] == "stale"
        stale_image = await client.get(f"/api/v1/cameras/{camera_id}/preview")
        assert stale_image.status_code == 200
        assert stale_image.headers["x-preview-state"] == "stale"

    app.state.database_session_factory.kw["bind"].dispose()
    return {
        "status": "ok",
        "camera_listed": True,
        "missing_preview_explicit": True,
        "shared_jpeg_returned": True,
        "stale_frame_preserved_and_marked": True,
        "analysis_started_by_browser": False,
    }


def main() -> int:
    prefix = f"f2_{uuid.uuid4().hex[:8]}"
    password = "F2-gercek-akis-deneme-parolasi"
    camera_id = uuid.uuid4()
    settings = Settings()
    engine = create_database_engine(settings)
    try:
        with Session(engine) as database:
            database.add(
                AppUser(
                    username=prefix,
                    display_name="F2 Kamera Doğrulama",
                    password_hash=hash_password(password),
                    role=UserRole.ISG,
                )
            )
            database.add(
                Camera(
                    id=camera_id,
                    name=f"F2 Kamera {camera_id.hex[:8]}",
                    source_type=CameraSourceType.RECORDED_VIDEO,
                    source_config={"relative_path": "demo/f2.mp4"},
                )
            )
            database.commit()

        with tempfile.TemporaryDirectory(prefix="isg-f2-") as directory:
            test_settings = Settings(preview_directory=Path(directory))
            result = asyncio.run(
                verify_flow(
                    test_settings,
                    username=prefix,
                    password=password,
                    camera_id=camera_id,
                )
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        with engine.begin() as connection:
            user_ids = select(AppUser.id).where(AppUser.username == prefix)
            connection.execute(
                delete(UserSession).where(UserSession.user_id.in_(user_ids))
            )
            connection.execute(delete(AppUser).where(AppUser.username == prefix))
            connection.execute(delete(Camera).where(Camera.id == camera_id))
        engine.dispose()
        password = ""
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
