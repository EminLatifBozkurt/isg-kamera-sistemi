"""PostgreSQL bağlantısını şifreyi loglamadan kuran ve sınayan yardımcılar."""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session, sessionmaker

from isg_api.config import Settings


class DatabaseNotConfiguredError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DatabaseTarget:
    host: str
    port: int
    database: str
    user: str


@dataclass(frozen=True, slots=True)
class DatabaseCheckResult:
    status: str
    latency_ms: float


def database_target(settings: Settings) -> DatabaseTarget:
    """Şifre içermeyen, güvenle gösterilebilir bağlantı hedefini döndürür."""
    return DatabaseTarget(
        host=settings.database_host,
        port=settings.database_port,
        database=settings.database_name,
        user=settings.database_user,
    )


def create_database_engine(settings: Settings) -> Any:
    """SQLAlchemy motorunu yalnız paketler kurulu ve şifre ayarlıysa oluşturur."""
    if not settings.database_configured:
        raise DatabaseNotConfiguredError(
            "ISG_DATABASE_PASSWORD ayarlı değil; veritabanı bağlantısı başlatılmadı"
        )
    try:
        from sqlalchemy import URL, create_engine
    except ImportError as error:
        raise DatabaseNotConfiguredError(
            "SQLAlchemy/psycopg paketleri kurulu değil; otomatik indirme yapılmadı"
        ) from error

    url = URL.create(
        "postgresql+psycopg",
        username=settings.database_user,
        password=settings.database_password.get_secret_value(),
        host=settings.database_host,
        port=settings.database_port,
        database=settings.database_name,
    )
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=0,
        # Sunucu kapalıysa panel uzun süre beklemesin; hata hızlı ve görünür olsun.
        connect_args={"connect_timeout": settings.database_connect_timeout_seconds},
    )


def check_database_connection(engine: Any) -> DatabaseCheckResult:
    """Gerçek bağlantıda basit sorgu çalıştırır; hatayı sağlıklı gibi gizlemez."""
    started = time.perf_counter()
    with engine.connect() as connection:
        value = connection.exec_driver_sql("SELECT 1").scalar_one()
    if value != 1:
        raise RuntimeError("PostgreSQL bağlantı kontrolü beklenmeyen sonuç döndürdü")
    return DatabaseCheckResult(
        status="ok",
        latency_ms=round((time.perf_counter() - started) * 1000, 3),
    )


def create_session_factory(engine: Any) -> sessionmaker[Session]:
    """API isteklerinin kullandığı kısa ömürlü SQLAlchemy oturumlarını üretir."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_database_session(request: Request) -> Iterator[Session]:
    """FastAPI bağımlılığı; veritabanı hazır değilse işlemi açıkça reddeder."""
    factory = getattr(request.app.state, "database_session_factory", None)
    if factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Veritabanı bağlantısı hazır değil",
        )

    with factory() as session:
        yield session
