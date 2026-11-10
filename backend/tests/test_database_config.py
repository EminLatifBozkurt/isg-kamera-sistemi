from contextlib import contextmanager

import pytest
from pydantic import ValidationError

from isg_api.config import Settings
from isg_api.database import (
    DatabaseNotConfiguredError,
    check_database_connection,
    create_database_engine,
    database_target,
)


def test_database_is_not_configured_without_secret() -> None:
    # Bilgisayarda gerçek kullanıcı ortam değişkeni bulunsa da bu test parola yok
    # senaryosunu yalıtılmış biçimde sınar.
    settings = Settings(_env_file=None, database_password=None)

    assert not settings.database_configured
    with pytest.raises(DatabaseNotConfiguredError, match="PASSWORD"):
        create_database_engine(settings)


def test_database_secret_is_hidden_and_target_is_safe() -> None:
    settings = Settings(_env_file=None, database_password="very-secret-password")

    assert settings.database_configured
    assert "very-secret-password" not in repr(settings)
    target = database_target(settings)
    assert "very-secret-password" not in repr(target)
    assert target.host == "127.0.0.1"


@pytest.mark.parametrize("field", ["database_name", "database_user"])
def test_invalid_database_identifier_is_rejected(field) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: "bad-name;drop"})


class FakeResult:
    def scalar_one(self):
        return 1


class FakeConnection:
    def __init__(self) -> None:
        self.statement = None

    def exec_driver_sql(self, statement):
        self.statement = statement
        return FakeResult()


class FakeEngine:
    def __init__(self) -> None:
        self.connection = FakeConnection()

    @contextmanager
    def connect(self):
        yield self.connection


def test_database_check_executes_realistic_select_one() -> None:
    engine = FakeEngine()

    result = check_database_connection(engine)

    assert result.status == "ok"
    assert engine.connection.statement == "SELECT 1"


def test_database_engine_uses_short_configured_timeout(monkeypatch) -> None:
    captured = {}
    expected_engine = object()

    def fake_create_engine(url, **options):
        captured["url"] = url
        captured["options"] = options
        return expected_engine

    monkeypatch.setattr("sqlalchemy.create_engine", fake_create_engine)
    settings = Settings(
        _env_file=None,
        database_password="secret-that-must-not-leak",
        database_connect_timeout_seconds=7,
    )

    engine = create_database_engine(settings)

    assert engine is expected_engine
    assert captured["options"]["connect_args"] == {"connect_timeout": 7}
    assert "secret-that-must-not-leak" not in str(captured["url"])
