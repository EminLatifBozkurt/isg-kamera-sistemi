"""Web sunucusunun giriş noktası. Bu modül GPU modeli yüklemez."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from isg_api import __version__
from isg_api.config import Settings
from isg_api.database import (
    DatabaseNotConfiguredError,
    check_database_connection,
    create_database_engine,
)

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
    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "İSG kamera sistemi sunucusu. Hazır olmayan bileşenlerin durumu açıkça bildirilir."
        ),
    )

    @application.get("/api/v1/health", response_model=HealthResponse, tags=["Sistem"])
    def health() -> HealthResponse:
        # Bu bir sunucu canlılık kontrolüdür; modelin hazır olduğunu iddia etmez.
        return HealthResponse(
            service=settings.app_name,
            version=__version__,
            database=get_database_status(settings),
        )

    return application


app = create_app()
