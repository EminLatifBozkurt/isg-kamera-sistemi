"""D5 çalışan arama ve otomatik olay geçmişini gerçek PostgreSQL'de doğrular."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
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
    EventFinding,
    FindingAssessment,
    IdentityStatus,
    ReviewStatus,
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

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
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
                "name": f"{prefix} Geçmiş Kamerası",
                "source_type": "recorded_video",
                "source_config": {"relative_path": "demo/d5-gecmis.mp4"},
            },
        )
        assert response.status_code == 201, response.text
        camera_id = uuid.UUID(response.json()["id"])

        employee_ids: list[uuid.UUID] = []
        for suffix in ("001", "002"):
            response = await client.post(
                "/api/v1/employees",
                headers=csrf_header,
                json={
                    "employee_number": f"{prefix}-{suffix}",
                    "full_name": "Ortak İsimli Çalışan",
                    "department": "Üretim",
                },
            )
            assert response.status_code == 201, response.text
            employee_ids.append(uuid.UUID(response.json()["id"]))

        response = await client.get("/api/v1/employees", params={"q": "Ortak İsimli"})
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 2
        assert {item["employee_number"] for item in results} == {
            f"{prefix}-001".upper(),
            f"{prefix}-002".upper(),
        }
        checks.append("same_names_distinguished_by_employee_number")

        response = await client.post(
            f"/api/v1/cameras/{camera_id}/rules",
            headers=csrf_header,
            json={"required_equipment": ["helmet"], "zones": []},
        )
        assert response.status_code == 201, response.text
        rule_id = uuid.UUID(response.json()["id"])

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
            for index, review_status in enumerate(
                (ReviewStatus.CONFIRMED, ReviewStatus.PENDING), start=1
            ):
                event_time = now + timedelta(seconds=index)
                event = SafetyEvent(
                    camera_id=camera_id,
                    camera_session_id=camera_session.id,
                    rule_version_id=rule_id,
                    track_id=index,
                    employee_id=employee_ids[0],
                    identity_status=IdentityStatus.RECOGNIZED,
                    review_status=review_status,
                    started_at=event_time,
                    last_seen_at=event_time,
                    source_time_ms=index * 1000,
                    model_version="d5-history-test",
                )
                database.add(event)
                database.flush()
                database.add(
                    EventFinding(
                        event_id=event.id,
                        equipment_code="helmet",
                        assessment=FindingAssessment.VIOLATION,
                        first_observed_at=event_time,
                        last_observed_at=event_time,
                        observation_count=3,
                        evidence_summary={"source": "d5-test"},
                    )
                )
            database.commit()

        response = await client.get(f"/api/v1/employees/{employee_ids[0]}/events")
        assert response.status_code == 200
        history = response.json()
        assert len(history) == 2
        assert all(
            item["camera_name"] == f"{prefix} Geçmiş Kamerası" for item in history
        )
        assert all(item["identity_status"] == "recognized" for item in history)
        assert all(
            item["findings"][0]["equipment_code"] == "helmet" for item in history
        )

        response = await client.get(
            f"/api/v1/employees/{employee_ids[0]}/history-summary"
        )
        assert response.status_code == 200
        summary = response.json()
        assert summary["total_events"] == 2
        assert summary["confirmed_events"] == 1
        assert summary["pending_events"] == 1
        assert summary["false_alarm_events"] == 0
        checks.append("automatic_event_history_and_summary_visible")

        response = await client.patch(
            f"/api/v1/employees/{employee_ids[0]}/active",
            headers=csrf_header,
            json={"is_active": False},
        )
        assert response.status_code == 200 and not response.json()["is_active"]

        response = await client.get("/api/v1/employees", params={"q": "Ortak İsimli"})
        assert response.status_code == 200 and len(response.json()) == 1
        response = await client.get(
            "/api/v1/employees",
            params={"q": "Ortak İsimli", "include_inactive": True},
        )
        assert response.status_code == 200 and len(response.json()) == 2
        response = await client.get(f"/api/v1/employees/{employee_ids[0]}/events")
        assert response.status_code == 200 and len(response.json()) == 2
        checks.append("deactivation_preserves_history")

    app.state.database_session_factory.kw["bind"].dispose()
    return {"status": "ok", "checks": checks}


def prepare_user(prefix: str, password: str, settings: Settings) -> None:
    engine = create_database_engine(settings)
    try:
        with Session(engine) as database:
            database.add(
                AppUser(
                    username=f"{prefix}_admin",
                    display_name="D5 API Yöneticisi",
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
    prefix = f"d5_{uuid.uuid4().hex[:8]}"
    password = "D5-gercek-akis-deneme-parolasi"
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
