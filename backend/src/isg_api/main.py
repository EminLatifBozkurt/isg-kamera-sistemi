"""Web sunucusunun giriş noktası. Bu modül GPU modeli yüklemez."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from isg_api import __version__
from isg_api.config import Settings


class HealthResponse(BaseModel):
    service: str
    version: str
    status: Literal["ok"] = "ok"
    analysis: Literal["not_configured"] = "not_configured"
    database: Literal["not_configured"] = "not_configured"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Her test veya çalıştırma için bağımsız uygulama oluşturur."""
    settings = settings if settings is not None else Settings()
    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Başlangıç sunucusu. Kamera analizi, veritabanı ve bildirimler henüz bağlı değildir."
        ),
    )

    @application.get("/api/v1/health", response_model=HealthResponse, tags=["Sistem"])
    def health() -> HealthResponse:
        # Bu bir sunucu canlılık kontrolüdür; modelin hazır olduğunu iddia etmez.
        return HealthResponse(service=settings.app_name, version=__version__)

    return application


app = create_app()
