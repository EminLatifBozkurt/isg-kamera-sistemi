"""Paylaşılabilir varsayılanlar ve bilgisayara özel ortam ayarları."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env isteğe bağlıdır. İşlemi depo kökünde başlatıyoruz.
    model_config = SettingsConfigDict(
        env_prefix="ISG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "İSG Kamera Sistemi"
    environment: str = "development"
