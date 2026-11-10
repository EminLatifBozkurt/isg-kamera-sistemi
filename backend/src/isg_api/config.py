"""Paylaşılabilir varsayılanlar ve bilgisayara özel ortam ayarları."""

from pydantic import Field, SecretStr
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
    database_host: str = "127.0.0.1"
    database_port: int = Field(default=5432, ge=1, le=65535)
    database_name: str = Field(default="isg_kamera", pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    database_user: str = Field(default="isg_app", pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    database_password: SecretStr | None = None
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_connect_timeout_seconds: int = Field(default=5, ge=1, le=30)

    @property
    def database_configured(self) -> bool:
        """Şifre yoksa veritabanını hazır kabul etmez."""
        return bool(self.database_password and self.database_password.get_secret_value().strip())
