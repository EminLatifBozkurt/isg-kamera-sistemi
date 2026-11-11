"""Web sunucusunun giriş noktası. Bu modül GPU modeli yüklemez."""

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from isg_api import __version__
from isg_api.auth import router as auth_router
from isg_api.cameras import router as cameras_router
from isg_api.config import Settings
from isg_api.database import (
    DatabaseNotConfiguredError,
    check_database_connection,
    create_database_engine,
    create_session_factory,
)
from isg_api.employees import router as employees_router
from isg_api.events import router as events_router
from isg_api.media import router as media_router
from isg_api.rule_management import router as rule_management_router
from isg_api.users import router as users_router

DatabaseState = Literal["ok", "not_configured", "unavailable"]


class HealthResponse(BaseModel):
    service: str
    version: str
    status: Literal["ok"] = "ok"
    analysis: Literal["not_configured"] = "not_configured"
    database: DatabaseState


def get_database_status(settings: Settings) -> DatabaseState:
    """Parolayı veya sürücü hatasını dışarı sızdırmadan gerçek bağlantıyı sınar."""
    if not settings.database_configured:
        return "not_configured"

    engine = None
    try:
        engine = create_database_engine(settings)
        check_database_connection(engine)
    except (DatabaseNotConfiguredError, SQLAlchemyError, OSError):
        return "unavailable"
    finally:
        if engine is not None:
            engine.dispose()
    return "ok"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Her test veya çalıştırma için bağımsız uygulama oluşturur."""
    settings = settings if settings is not None else Settings()
    database_engine = None
    database_session_factory = None
    if settings.database_configured:
        try:
            database_engine = create_database_engine(settings)
            database_session_factory = create_session_factory(database_engine)
        except DatabaseNotConfiguredError:
            database_engine = None

    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        yield
        if database_engine is not None:
            database_engine.dispose()

    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "İSG kamera sistemi sunucusu. Hazır olmayan bileşenlerin durumu açıkça bildirilir."
        ),
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.state.database_session_factory = database_session_factory

    @application.get("/api/v1/health", response_model=HealthResponse, tags=["Sistem"])
    def health() -> HealthResponse:
        # Bu bir sunucu canlılık kontrolüdür; modelin hazır olduğunu iddia etmez.
        return HealthResponse(
            service=settings.app_name,
            version=__version__,
            database=get_database_status(settings),
        )

    application.include_router(auth_router)
    application.include_router(users_router)
    application.include_router(media_router)
    application.include_router(cameras_router)
    application.include_router(employees_router)
    application.include_router(rule_management_router)
    application.include_router(events_router)
    return application


app = create_app()
