"""Alembic çalışma ortamı; parola migration dosyalarına veya loglara yazılmaz."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context

from isg_api.config import Settings
from isg_api.database import create_database_engine
from isg_api.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Bağlantı kurmadan PostgreSQL uyumlu SQL üretir."""
    context.configure(
        dialect_name="postgresql",
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Uygulamayla aynı güvenli ayarları kullanarak gerçek migration çalıştırır."""
    engine = create_database_engine(Settings())
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                render_as_batch=False,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
