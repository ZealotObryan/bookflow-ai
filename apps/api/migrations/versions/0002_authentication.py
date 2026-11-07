"""Add password, phone identity and revocable authentication sessions.

Revision ID: 0002_authentication
Revises: 0001_identity_business
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_authentication"
down_revision: Union[str, None] = "0001_identity_business"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("phone_e164", sa.String(length=16), nullable=True))
    op.add_column("users", sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_users_phone_e164", "users", ["phone_e164"])

    op.create_table(
        "auth_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_auth_sessions"),
        sa.UniqueConstraint("refresh_token_hash", name="uq_auth_sessions_refresh_token_hash"),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])

    op.create_table(
        "phone_otp_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phone_e164", sa.String(length=16), nullable=False),
        sa.Column("purpose", sa.String(length=16), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_phone_otp_challenges"),
        sa.CheckConstraint("purpose IN ('login', 'link')", name="ck_phone_otp_challenges_purpose"),
        sa.CheckConstraint("attempts >= 0 AND attempts <= 5", name="ck_phone_otp_challenges_attempts"),
    )
    op.create_index("ix_phone_otp_challenges_phone_e164", "phone_otp_challenges", ["phone_e164"])


def downgrade() -> None:
    op.drop_index("ix_phone_otp_challenges_phone_e164", table_name="phone_otp_challenges")
    op.drop_table("phone_otp_challenges")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_constraint("uq_users_phone_e164", "users", type_="unique")
    op.drop_column("users", "phone_verified_at")
    op.drop_column("users", "phone_e164")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "password_hash")
