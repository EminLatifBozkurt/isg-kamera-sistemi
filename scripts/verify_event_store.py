"""E4 olay/değişiklik ve medya kayıtlarını gerçek PostgreSQL üzerinde doğrular."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from isg_api.config import Settings
from isg_api.database import create_database_engine
from isg_api.event_lifecycle import EventLifecycleKey, EventLifecycleTracker
from isg_api.event_store import (
    EventPersistenceContext,
    persist_event_transition,
    persist_evidence_job,
)
from isg_api.evidence_capture import (
    EvidenceArtifact,
    EvidenceCompletionReason,
    EvidenceJobSnapshot,
    EvidenceStatus,
    EvidenceWriteResult,
)
from isg_api.main import create_app
from isg_api.models import (
    AppUser,
    Camera,
    CameraSession,
    CameraSourceType,
    EventChange,
    IdentityStatus,
    MediaRecord,
    MediaStatus,
    RuleVersion,
    SafetyEvent,
    TechnicalStatus,
    UserRole,
    UserSession,
)
from isg_api.rules import Equipment
from isg_api.security import hash_password
from sqlalchemy import delete, select
from sqlalchemy.orm import Session


def artifact(path: str, mime_type: str) -> EvidenceArtifact:
    return EvidenceArtifact(
        relative_path=path,
        mime_type=mime_type,
        size_bytes=123,
        sha256="a" * 64,
    )


def cleanup(engine, camera_id: uuid.UUID, user_id: uuid.UUID) -> None:
    with engine.begin() as connection:
        connection.execute(
            delete(SafetyEvent).where(SafetyEvent.camera_id == camera_id)
        )
        connection.execute(
            delete(CameraSession).where(CameraSession.camera_id == camera_id)
        )
        connection.execute(
            delete(RuleVersion).where(RuleVersion.camera_id == camera_id)
        )
        connection.execute(delete(Camera).where(Camera.id == camera_id))
        connection.execute(delete(UserSession).where(UserSession.user_id == user_id))
        connection.execute(delete(AppUser).where(AppUser.id == user_id))


def main() -> int:
    settings = Settings()
    engine = create_database_engine(settings)
    camera_id = uuid.uuid4()
    event_id = uuid.uuid4()
    user_id = uuid.uuid4()
    username = f"e4_{user_id.hex[:8]}"
    password = "E4-gercek-akis-parolasi"
    now = datetime.now(UTC)
    try:
        with Session(engine) as database:
            camera = Camera(
                id=camera_id,
                name=f"E4 doğrulama {camera_id.hex[:8]}",
                source_type=CameraSourceType.RECORDED_VIDEO,
                source_config={"relative_path": "demo/e4.mp4"},
            )
            camera_session = CameraSession(
                id=uuid.uuid4(),
                camera_id=camera_id,
                source_type=CameraSourceType.RECORDED_VIDEO,
                started_at=now,
                source_start_time_ms=0,
            )
            rule = RuleVersion(
                id=uuid.uuid4(),
                camera_id=camera_id,
                version_number=1,
                valid_from=now,
                definition={"required_equipment": ["helmet", "vest"], "zones": []},
                definition_hash="b" * 64,
            )
            database.add_all([camera, camera_session, rule])
            database.add(
                AppUser(
                    id=user_id,
                    username=username,
                    display_name="E4 Doğrulama Görevlisi",
                    password_hash=hash_password(password),
                    role=UserRole.ISG,
                )
            )
            database.commit()

            identifiers = iter([event_id])
            tracker = EventLifecycleTracker(event_id_factory=lambda: next(identifiers))
            key = EventLifecycleKey(camera_session.id, rule.id, 7)
            context = EventPersistenceContext(
                camera_id=camera_id,
                identity_status=IdentityStatus.UNKNOWN,
                employee_id=None,
                model_version="e4-store-verification",
            )

            started = tracker.observe(key, [Equipment.HELMET], 1.0)[0]
            persist_event_transition(database, started, context)
            database.commit()
            # Tekrar oynatma ikinci olay, medya veya değişiklik oluşturmamalı.
            persist_event_transition(database, started, context)
            database.commit()

            updated = tracker.observe(key, [Equipment.HELMET, Equipment.VEST], 2.0)[0]
            persist_event_transition(database, updated, context)
            database.commit()
            clear_one = tracker.observe(key, [], 3.0)[0]
            persist_event_transition(database, clear_one, context)
            ended = tracker.observe(key, [], 4.1)[0]
            persist_event_transition(database, ended, context)
            database.commit()

            job = EvidenceJobSnapshot(
                event_id=event_id,
                session_id=str(camera_session.id),
                status=EvidenceStatus.READY,
                snapshot_source_time=1.0,
                clip_frame_count=10,
                clip_start_source_time=0.0,
                clip_end_source_time=6.0,
                completion_reason=EvidenceCompletionReason.POST_WINDOW_COMPLETE,
                is_partial=False,
                result=EvidenceWriteResult(
                    snapshot=artifact(f"events/{event_id}/snapshot.jpg", "image/jpeg"),
                    clip=artifact(f"events/{event_id}/clip.mp4", "video/mp4"),
                ),
                error_message=None,
            )
            persist_evidence_job(database, job, ready_at=now + timedelta(seconds=6))
            database.commit()

            stored_event = database.get(SafetyEvent, event_id)
            changes = database.scalars(
                select(EventChange)
                .where(EventChange.event_id == event_id)
                .order_by(EventChange.id)
            ).all()
            media = database.scalars(
                select(MediaRecord).where(MediaRecord.event_id == event_id)
            ).all()
            assert stored_event is not None
            assert stored_event.technical_status is TechnicalStatus.ENDED
            assert [item.change_kind.value for item in changes] == [
                "event_started",
                "event_updated",
                "event_ended",
                "media_ready",
            ]
            assert len(media) == 2
            assert all(item.status is MediaStatus.READY for item in media)
            assert len(stored_event.findings) == 2
            change_ids = [item.id for item in changes]
            change_kinds = [item.change_kind for item in changes]

        # Olay panel kapalıyken yukarıda commit edildi. Panel ancak şimdi açılır ve
        # hem tam listeyi hem de son sıra numarasından sonraki değişikliği alır.
        with TestClient(create_app(settings)) as client:
            login = client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": password},
            )
            assert login.status_code == 200, login.text
            events_response = client.get("/api/v1/events?limit=100")
            assert events_response.status_code == 200, events_response.text
            visible_ids = {item["id"] for item in events_response.json()["items"]}
            assert str(event_id) in visible_ids

            changes_response = client.get(
                f"/api/v1/events/changes?after_id={change_ids[0] - 1}"
            )
            assert changes_response.status_code == 200, changes_response.text
            returned_ids = [item["id"] for item in changes_response.json()["items"]]
            assert set(change_ids).issubset(returned_ids)

            with client.websocket_connect(
                f"/api/v1/events/live?after_id={change_ids[-2]}"
            ) as websocket:
                message = websocket.receive_json()
                assert message["type"] == "event_change"
                assert message["cursor"] == change_ids[-1]
                assert message["change"]["change_kind"] == "media_ready"

        print(
            json.dumps(
                {
                    "status": "ok",
                    "event_persisted_while_panel_absent": True,
                    "reconnected_list_contains_event": True,
                    "websocket_resumed_from_cursor": True,
                    "technical_status": TechnicalStatus.ENDED,
                    "change_ids": change_ids,
                    "change_kinds": change_kinds,
                    "media_statuses": [MediaStatus.READY, MediaStatus.READY],
                    "finding_count": 2,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        cleanup(engine, camera_id, user_id)
        engine.dispose()
        password = ""
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
