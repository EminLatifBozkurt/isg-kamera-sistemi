"""D4 kamera, çalışan ve sürümlü kural API'lerini gerçek PostgreSQL'de sınar."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from isg_api.config import Settings
from isg_api.database import create_database_engine
from isg_api.main import create_app
from isg_api.models import (
    AppUser,
    Camera,
    CameraSession,
    Employee,
    IdentityStatus,
    RuleVersion,
    SafetyEvent,
    UserRole,
    UserSession,
)
from isg_api.security import hash_password
from sqlalchemy import delete, select
from sqlalchemy.orm import Session


async def verify_http_flow(
    prefix: str, password: str, settings: Settings
) -> dict[str, Any]:
    app = create_app(settings)
    transport = httpx.ASGITransport(app=app)
    checks: list[str] = []
    camera_id: uuid.UUID | None = None
    employee_id: uuid.UUID | None = None

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/cameras")
        assert response.status_code == 401
        checks.append("unauthorized_management_rejected")

        response = await client.post(
            "/api/v1/auth/login",
            json={"username": f"{prefix}_admin", "password": password},
        )
        assert response.status_code == 200
        csrf_token = client.cookies.get("csrf")
        assert csrf_token is not None
        csrf_header = {"X-CSRF-Token": csrf_token}

        response = await client.post(
            "/api/v1/cameras",
            headers=csrf_header,
            json={
                "name": f"{prefix} geçersiz yol",
                "source_type": "recorded_video",
                "source_config": {"relative_path": "../gizli.mp4"},
            },
        )
        assert response.status_code == 422
        response = await client.post(
            "/api/v1/cameras",
            headers=csrf_header,
            json={
                "name": f"{prefix} RTSP",
                "source_type": "rtsp",
                "source_config": {
                    "url": "rtsp://kamera.example/live",
                    "password": "veritabanina-girmemeli",
                },
            },
        )
        assert response.status_code == 422
        checks.append("unsafe_sources_rejected")

        response = await client.post(
            "/api/v1/cameras",
            headers=csrf_header,
            json={
                "name": f"{prefix} Üretim Kamerası",
                "source_type": "recorded_video",
                "source_config": {"relative_path": "demo/uretim.mp4"},
            },
        )
        assert response.status_code == 201, response.text
        camera = response.json()
        camera_id = uuid.UUID(camera["id"])
        assert camera["source_config"] == {"relative_path": "demo/uretim.mp4"}
        checks.append("camera_created_without_secret")

        response = await client.post(
            "/api/v1/employees",
            headers=csrf_header,
            json={
                "employee_number": f"{prefix}-001",
                "full_name": "D4 Deneme Çalışanı",
                "department": "Üretim",
            },
        )
        assert response.status_code == 201, response.text
        employee_id = uuid.UUID(response.json()["id"])
        assert response.json()["employee_number"] == f"{prefix}-001".upper()
        checks.append("employee_created_and_normalized")

        rule_one = {"required_equipment": ["helmet"], "zones": []}
        response = await client.post(
            f"/api/v1/cameras/{camera_id}/rules",
            headers=csrf_header,
            json=rule_one,
        )
        assert response.status_code == 201, response.text
        first_rule_id = uuid.UUID(response.json()["id"])
        assert response.json()["version_number"] == 1

        # İlk olay birinci kurala bağlandıktan sonra yeni kural kaydedilir. Olayın
        # yabancı anahtarı özellikle eski sürümde kalmalıdır.
        now = datetime.now(UTC)
        engine = app.state.database_session_factory.kw["bind"]
        with Session(engine) as database:
            camera_session = CameraSession(
                camera_id=camera_id,
                source_type="recorded_video",
                started_at=now,
                source_start_time_ms=0,
            )
            database.add(camera_session)
            database.flush()
            event = SafetyEvent(
                camera_id=camera_id,
                camera_session_id=camera_session.id,
                rule_version_id=first_rule_id,
                track_id=1,
                identity_status=IdentityStatus.UNKNOWN,
                started_at=now,
                last_seen_at=now,
                source_time_ms=1000,
                model_version="d4-history-test",
            )
            database.add(event)
            database.commit()
            event_id = event.id

        rule_two = {
            "required_equipment": ["vest", "helmet"],
            "zones": [
                {
                    "id": "makine-cevresi",
                    "name": "Makine çevresi",
                    "polygon": [
                        {"x": 0.1, "y": 0.1},
                        {"x": 0.9, "y": 0.1},
                        {"x": 0.9, "y": 0.9},
                        {"x": 0.1, "y": 0.9},
                    ],
                    "required_equipment": ["goggles"],
                }
            ],
        }
        response = await client.post(
            f"/api/v1/cameras/{camera_id}/rules",
            headers=csrf_header,
            json=rule_two,
        )
        assert response.status_code == 201, response.text
        assert response.json()["version_number"] == 2

        response = await client.post(
            f"/api/v1/cameras/{camera_id}/rules",
            headers=csrf_header,
            json=rule_two,
        )
        assert response.status_code == 409

        # A -> B -> A geçişi de yeni tarih aralığıyla üçüncü sürüm olmalıdır.
        response = await client.post(
            f"/api/v1/cameras/{camera_id}/rules",
            headers=csrf_header,
            json=rule_one,
        )
        assert response.status_code == 201, response.text
        assert response.json()["version_number"] == 3

        response = await client.post(
            f"/api/v1/cameras/{camera_id}/rules",
            headers=csrf_header,
            json={
                "zones": [
                    {
                        "id": "kesisen",
                        "name": "Kesişen alan",
                        "polygon": [
                            {"x": 0.1, "y": 0.1},
                            {"x": 0.9, "y": 0.9},
                            {"x": 0.1, "y": 0.9},
                            {"x": 0.9, "y": 0.1},
                        ],
                    }
                ]
            },
        )
        assert response.status_code == 422
        checks.append("invalid_polygon_rejected")

        with Session(engine) as database:
            stored_event = database.get(SafetyEvent, event_id)
            first_rule = database.get(RuleVersion, first_rule_id)
            versions = database.scalars(
                select(RuleVersion)
                .where(RuleVersion.camera_id == camera_id)
                .order_by(RuleVersion.version_number)
            ).all()
            assert stored_event is not None
            assert stored_event.rule_version_id == first_rule_id
            assert first_rule is not None and first_rule.valid_until is not None
            assert [item.version_number for item in versions] == [1, 2, 3]
        checks.append("event_keeps_historical_rule_version")
        checks.append("historical_definition_can_be_reactivated")

        response = await client.patch(
            f"/api/v1/cameras/{camera_id}/active",
            headers=csrf_header,
            json={"is_active": False},
        )
        assert response.status_code == 200 and not response.json()["is_active"]
        response = await client.patch(
            f"/api/v1/employees/{employee_id}/active",
            headers=csrf_header,
            json={"is_active": False},
        )
        assert response.status_code == 200 and not response.json()["is_active"]
        checks.append("master_records_are_deactivated_not_deleted")

    app.state.database_session_factory.kw["bind"].dispose()
    return {"status": "ok", "checks": checks}


def prepare_user(prefix: str, password: str, settings: Settings) -> None:
    engine = create_database_engine(settings)
    try:
        with Session(engine) as database:
            database.add(
                AppUser(
                    username=f"{prefix}_admin",
                    display_name="D4 API Yöneticisi",
                    password_hash=hash_password(password),
                    role=UserRole.ADMIN,
                )
            )
            database.commit()
    finally:
        engine.dispose()


def cleanup(prefix: str, settings: Settings) -> None:
    engine = create_database_engine(settings)
    try:
        with engine.begin() as connection:
            camera_ids = select(Camera.id).where(Camera.name.like(f"{prefix}%"))
            employee_ids = select(Employee.id).where(
                Employee.employee_number.like(f"{prefix.upper()}%")
            )
            user_ids = select(AppUser.id).where(AppUser.username.like(f"{prefix}%"))
            connection.execute(
                delete(SafetyEvent).where(SafetyEvent.camera_id.in_(camera_ids))
            )
            connection.execute(
                delete(CameraSession).where(CameraSession.camera_id.in_(camera_ids))
            )
            connection.execute(
                delete(RuleVersion).where(RuleVersion.camera_id.in_(camera_ids))
            )
            connection.execute(delete(Employee).where(Employee.id.in_(employee_ids)))
            connection.execute(delete(Camera).where(Camera.id.in_(camera_ids)))
            connection.execute(
                delete(UserSession).where(UserSession.user_id.in_(user_ids))
            )
            connection.execute(delete(AppUser).where(AppUser.id.in_(user_ids)))
    finally:
        engine.dispose()


def main() -> int:
    prefix = f"d4_{uuid.uuid4().hex[:8]}"
    password = "D4-gercek-akis-deneme-parolasi"
    settings = Settings()
    prepare_user(prefix, password, settings)
    try:
        result = asyncio.run(verify_http_flow(prefix, password, settings))
    finally:
        cleanup(prefix, settings)
        password = ""
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
