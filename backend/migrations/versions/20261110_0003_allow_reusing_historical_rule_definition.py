"""Tarihsel bir kural tanımının yeni sürüm olarak yeniden kullanılmasına izin ver.

Revision ID: 20261110_0003
Revises: 20261110_0002
Create Date: 2026-11-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261110_0003"
down_revision: str | None = "20261110_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # A -> B -> A geçişinde son A yeni zaman aralığına sahip ayrı bir sürümdür.
    # Aynı etkin tanımın tekrarını API engeller; tarihsel özet yalnız indekslenir.
    op.drop_constraint(
        "camera_definition_hash",
        "rule_version",
        type_="unique",
    )
    op.create_index(
        "ix_rule_version_camera_definition_hash",
        "rule_version",
        ["camera_id", "definition_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_rule_version_camera_definition_hash", table_name="rule_version")
    op.create_unique_constraint(
        "camera_definition_hash",
        "rule_version",
        ["camera_id", "definition_hash"],
    )
