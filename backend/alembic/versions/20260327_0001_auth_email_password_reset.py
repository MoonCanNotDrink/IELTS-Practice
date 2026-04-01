"""Add auth email and password reset support.

Revision ID: 20260327_0001
Revises:
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260327_0001"
down_revision = None
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    columns = sa.inspect(op.get_bind()).get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    indexes = sa.inspect(op.get_bind()).get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def upgrade() -> None:
    # This migration was introduced after legacy environments had already created
    # base tables from SQLAlchemy models. Treat pre-existing schema objects as
    # already applied so startup migrations remain safe across mixed histories.
    if _has_table("users"):
        if not _has_column("users", "email"):
            op.add_column("users", sa.Column("email", sa.String(length=255), nullable=True))
        if not _has_column("users", "email_verified_at"):
            op.add_column("users", sa.Column("email_verified_at", sa.DateTime(), nullable=True))
        if not _has_column("users", "token_version"):
            op.add_column(
                "users",
                sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
            )
        if not _has_index("users", "ix_users_email"):
            op.create_index("ix_users_email", "users", ["email"], unique=True)

        if not _has_table("password_reset_tokens"):
            op.create_table(
                "password_reset_tokens",
                sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
                sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
                sa.Column("token_hash", sa.String(length=64), nullable=False),
                sa.Column("expires_at", sa.DateTime(), nullable=False),
                sa.Column("used_at", sa.DateTime(), nullable=True),
                sa.Column("requested_ip", sa.String(length=64), nullable=True),
                sa.Column("requested_user_agent", sa.String(length=500), nullable=True),
                sa.Column("created_at", sa.DateTime(), nullable=False),
            )

        if not _has_index("password_reset_tokens", "ix_password_reset_tokens_user_id"):
            op.create_index(
                "ix_password_reset_tokens_user_id",
                "password_reset_tokens",
                ["user_id"],
                unique=False,
            )
        if not _has_index("password_reset_tokens", "ix_password_reset_tokens_expires_at"):
            op.create_index(
                "ix_password_reset_tokens_expires_at",
                "password_reset_tokens",
                ["expires_at"],
                unique=False,
            )
        if not _has_index("password_reset_tokens", "ix_password_reset_tokens_token_hash"):
            op.create_index(
                "ix_password_reset_tokens_token_hash",
                "password_reset_tokens",
                ["token_hash"],
                unique=True,
            )


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_expires_at", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "token_version")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "email")
