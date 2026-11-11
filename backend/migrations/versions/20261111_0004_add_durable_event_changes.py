"""add durable event changes

Revision ID: 20261111_0004
Revises: 20261110_0003
Create Date: 2026-11-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261111_0004"
down_revision: str | None = "20261110_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Her olayda bir fotoğraf ve bir kısa klip kaydı bulunur. Tekrar oynatılan
    # komutlar ikinci bir medya satırı oluşturamaz.
    op.create_unique_constraint("event_media_type", "media_record", ["event_id", "media_type"])
    op.create_table(
        "event_change",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column(
            "change_kind",
            sa.Enum(
                "event_started",
                "event_updated",
                "event_ended",
                "media_ready",
                "media_failed",
                name="event_change_kind",
                native_enum=False,
                create_constraint=True,
                length=24,
            ),
            nullable=False,
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name=op.f("ck_event_change_payload_object"),
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["safety_event.id"],
            name=op.f("fk_event_change_event_id_safety_event"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event_change")),
    )
    op.create_index(
        "ix_event_change_created",
        "event_change",
        [sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_event_change_event_id",
        "event_change",
        ["event_id", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_event_change_event_id", table_name="event_change")
    op.drop_index("ix_event_change_created", table_name="event_change")
    op.drop_table("event_change")
    op.drop_constraint("event_media_type", "media_record", type_="unique")
