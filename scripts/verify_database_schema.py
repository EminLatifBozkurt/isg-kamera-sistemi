"""D2 şemasını gerçek PostgreSQL üzerinde veri bırakmadan doğrular."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from isg_api.config import Settings
from isg_api.database import create_database_engine
from isg_api.models import (
    Base,
    Camera,
    CameraSession,
    CameraSourceType,
    Employee,
    EquipmentDefinition,
    EventFinding,
    EventReviewRevision,
    FindingAssessment,
    IdentityStatus,
    MediaRecord,
    MediaStatus,
    MediaType,
    ReviewStatus,
    RuleVersion,
    SafetyEvent,
    TechnicalStatus,
)
from sqlalchemy import delete, inspect, select
from sqlalchemy.exc import IntegrityError

EXPECTED_TABLES = set(Base.metadata.tables) | {"alembic_version"}
EXPECTED_EQUIPMENT_CODES = {"helmet", "vest", "gloves", "goggles", "boots"}


def expect_integrity_error(connection: Any, statement: Any, label: str) -> None:
    """Beklenen kısıt ihlalini savepoint içinde sınar; ana deneme devam eder."""
    savepoint = connection.begin_nested()
    try:
        connection.execute(statement)
    except IntegrityError:
        savepoint.rollback()
        return
    savepoint.rollback()
    raise AssertionError(f"Veritabanı beklenen kısıt ihlalini reddetmedi: {label}")


def verify_schema() -> dict[str, Any]:
    engine = create_database_engine(Settings())
    checks: list[str] = []
    now = datetime.now(UTC)

    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        if tables != EXPECTED_TABLES:
            raise AssertionError(
                f"Tablo kümesi farklı: eksik={sorted(EXPECTED_TABLES - tables)}, "
                f"fazla={sorted(tables - EXPECTED_TABLES)}"
            )
        checks.append("table_set")

        with engine.connect() as connection, connection.begin() as transaction:
            equipment_codes = set(
                connection.execute(select(EquipmentDefinition.code)).scalars().all()
            )
            if equipment_codes != EXPECTED_EQUIPMENT_CODES:
                raise AssertionError(
                    f"Ekipman kataloğu farklı: {sorted(equipment_codes)}"
                )
            checks.append("equipment_seed")

            camera_id = uuid.uuid4()
            session_id = uuid.uuid4()
            employee_id = uuid.uuid4()
            rule_id = uuid.uuid4()
            event_id = uuid.uuid4()

            connection.execute(
                Camera.__table__.insert().values(
                    id=camera_id,
                    name=f"D2 doğrulama {camera_id}",
                    source_type=CameraSourceType.RECORDED_VIDEO,
                    source_config={"path": "demo.mp4"},
                )
            )
            connection.execute(
                Employee.__table__.insert().values(
                    id=employee_id,
                    employee_number=f"D2-{employee_id.hex[:12]}",
                    full_name="D2 Doğrulama Çalışanı",
                    department="Test",
                )
            )
            connection.execute(
                CameraSession.__table__.insert().values(
                    id=session_id,
                    camera_id=camera_id,
                    source_type=CameraSourceType.RECORDED_VIDEO,
                    started_at=now,
                    source_start_time_ms=0,
                )
            )
            connection.execute(
                RuleVersion.__table__.insert().values(
                    id=rule_id,
                    camera_id=camera_id,
                    version_number=1,
                    valid_from=now,
                    definition={"base_equipment": ["helmet"]},
                    definition_hash="a" * 64,
                )
            )
            connection.execute(
                SafetyEvent.__table__.insert().values(
                    id=event_id,
                    camera_id=camera_id,
                    camera_session_id=session_id,
                    rule_version_id=rule_id,
                    track_id=1,
                    identity_status=IdentityStatus.UNKNOWN,
                    technical_status=TechnicalStatus.ACTIVE,
                    review_status=ReviewStatus.PENDING,
                    started_at=now,
                    last_seen_at=now + timedelta(seconds=1),
                    model_version="d2-test",
                )
            )
            connection.execute(
                EventFinding.__table__.insert().values(
                    id=uuid.uuid4(),
                    event_id=event_id,
                    equipment_code="helmet",
                    assessment=FindingAssessment.VIOLATION,
                    first_observed_at=now,
                    last_observed_at=now + timedelta(seconds=1),
                    observation_count=3,
                    evidence_summary={"visible": True},
                )
            )
            connection.execute(
                MediaRecord.__table__.insert().values(
                    id=uuid.uuid4(),
                    event_id=event_id,
                    media_type=MediaType.SNAPSHOT,
                    status=MediaStatus.PREPARING,
                )
            )
            connection.execute(
                EventReviewRevision.__table__.insert().values(
                    id=uuid.uuid4(),
                    event_id=event_id,
                    revision_number=1,
                    previous_status=None,
                    new_status=ReviewStatus.PENDING,
                    note="D2 şema doğrulaması",
                )
            )
            checks.append("valid_record_graph")

            expect_integrity_error(
                connection,
                SafetyEvent.__table__.insert().values(
                    id=uuid.uuid4(),
                    camera_id=camera_id,
                    camera_session_id=session_id,
                    rule_version_id=rule_id,
                    track_id=2,
                    employee_id=None,
                    identity_status=IdentityStatus.RECOGNIZED,
                    technical_status=TechnicalStatus.ACTIVE,
                    review_status=ReviewStatus.PENDING,
                    started_at=now,
                    last_seen_at=now,
                    model_version="d2-test",
                ),
                "recognized_without_employee",
            )
            checks.append("identity_constraint")

            expect_integrity_error(
                connection,
                RuleVersion.__table__.insert().values(
                    id=uuid.uuid4(),
                    camera_id=camera_id,
                    version_number=2,
                    valid_from=now + timedelta(seconds=1),
                    valid_until=None,
                    definition={"base_equipment": ["vest"]},
                    definition_hash="b" * 64,
                ),
                "two_current_rules",
            )
            checks.append("single_current_rule")

            expect_integrity_error(
                connection,
                MediaRecord.__table__.insert().values(
                    id=uuid.uuid4(),
                    event_id=event_id,
                    media_type=MediaType.CLIP,
                    status=MediaStatus.READY,
                ),
                "ready_media_without_file_metadata",
            )
            checks.append("ready_media_constraint")

            expect_integrity_error(
                connection,
                delete(Camera).where(Camera.id == camera_id),
                "delete_camera_with_history",
            )
            checks.append("historical_delete_restricted")

            # Doğrulama verileri kalıcı değildir; yalnız migration'ın eklediği sabit
            # ekipman kataloğu veritabanında bırakılır.
            transaction.rollback()

        return {
            "status": "ok",
            "table_count": len(EXPECTED_TABLES),
            "equipment_codes": sorted(EXPECTED_EQUIPMENT_CODES),
            "checks": checks,
        }
    finally:
        engine.dispose()


def main() -> int:
    print(json.dumps(verify_schema(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
