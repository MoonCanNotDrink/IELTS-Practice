"""Add learning-loop fields to recordings.

Revision ID: 20260331_0002
Revises: 20260327_0001
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20260331_0002"
down_revision = "20260327_0001"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    columns = sa.inspect(op.get_bind()).get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def upgrade() -> None:
    if not _has_table("recordings"):
        return

    if not _has_column("recordings", "prompt_match_type"):
        op.add_column(
            "recordings",
            sa.Column("prompt_match_type", sa.String(length=50), nullable=True),
        )
    if not _has_column("recordings", "prompt_match_key"):
        op.add_column(
            "recordings",
            sa.Column("prompt_match_key", sa.String(length=255), nullable=True),
        )
    if not _has_column("recordings", "prompt_source"):
        op.add_column(
            "recordings",
            sa.Column("prompt_source", sa.String(length=100), nullable=True),
        )
    if not _has_column("recordings", "weakness_tags"):
        op.add_column("recordings", sa.Column("weakness_tags", sa.JSON(), nullable=True))
    if not _has_column("recordings", "coaching_payload"):
        op.add_column("recordings", sa.Column("coaching_payload", sa.JSON(), nullable=True))
    if not _has_column("recordings", "analysis_version"):
        op.add_column(
            "recordings",
            sa.Column("analysis_version", sa.String(length=50), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("recordings", "analysis_version")
    op.drop_column("recordings", "coaching_payload")
    op.drop_column("recordings", "weakness_tags")
    op.drop_column("recordings", "prompt_source")
    op.drop_column("recordings", "prompt_match_key")
    op.drop_column("recordings", "prompt_match_type")
