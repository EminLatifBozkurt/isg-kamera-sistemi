from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from isg_api.models import Base, SafetyEvent

EXPECTED_TABLES = {
    "app_user",
    "camera",
    "camera_session",
    "employee",
    "equipment_definition",
    "event_finding",
    "event_review_revision",
    "media_record",
    "rule_version",
    "safety_event",
    "user_session",
}


def test_core_schema_has_expected_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_every_table_compiles_for_postgresql() -> None:
    dialect = postgresql.dialect()

    for table in Base.metadata.sorted_tables:
        sql = str(CreateTable(table).compile(dialect=dialect))
        assert f"CREATE TABLE {table.name}" in sql


def test_event_identity_and_lifecycle_are_database_constraints() -> None:
    constraint_names = {constraint.name for constraint in SafetyEvent.__table__.constraints}

    assert "ck_safety_event_identity_matches_employee" in constraint_names
    assert "ck_safety_event_technical_status_matches_end" in constraint_names
    assert "ck_safety_event_last_seen_order" in constraint_names


def test_history_foreign_keys_do_not_cascade_from_master_records() -> None:
    protected_targets = {"camera", "camera_session", "employee", "rule_version"}
    event_foreign_keys = list(SafetyEvent.__table__.foreign_keys)

    assert {
        foreign_key.column.table.name for foreign_key in event_foreign_keys
    } == protected_targets
    assert all(foreign_key.ondelete == "RESTRICT" for foreign_key in event_foreign_keys)


def test_only_one_current_rule_index_is_partial_and_unique() -> None:
    rule_table = Base.metadata.tables["rule_version"]
    index = next(
        item for item in rule_table.indexes if item.name == "uq_rule_version_one_current_per_camera"
    )

    assert index.unique
    assert str(index.dialect_options["postgresql"]["where"]) == "valid_until IS NULL"


def test_auth_schema_stores_only_password_and_token_verifiers() -> None:
    user_table = Base.metadata.tables["app_user"]
    session_table = Base.metadata.tables["user_session"]

    assert "password_hash" in user_table.c
    assert "password" not in user_table.c
    assert {"verifier_hash", "csrf_hash"}.issubset(session_table.c.keys())
    assert "verifier" not in session_table.c
    assert "csrf_token" not in session_table.c

    constraint_names = {constraint.name for constraint in session_table.constraints}
    assert "ck_user_session_verifier_hash_sha256" in constraint_names
    assert "ck_user_session_csrf_hash_sha256" in constraint_names
    assert "ck_user_session_absolute_expiry_order" in constraint_names
