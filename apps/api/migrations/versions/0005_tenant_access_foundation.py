"""Add audit events and business invitations.

Revision ID: 0005_tenant_access
Revises: 0004_email_auth_tokens
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_tenant_access"
down_revision: str | None = "0004_email_auth_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.String(length=80), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
        sa.CheckConstraint("length(action) > 0", name="ck_audit_events_action_nonempty"),
        sa.CheckConstraint("length(target_type) > 0", name="ck_audit_events_target_type_nonempty"),
    )
    op.create_index("ix_audit_events_business_created", "audit_events", ["business_id", "created_at"])
    op.create_index("ix_audit_events_actor_created", "audit_events", ["actor_user_id", "created_at"])

    op.create_table(
        "business_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email_normalized", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_business_invitations"),
        sa.UniqueConstraint("token_hash", name="uq_business_invitations_token_hash"),
        sa.CheckConstraint("role IN ('admin', 'manager', 'staff')", name="ck_business_invitations_invitable_role"),
    )
    op.create_index("ix_business_invitations_business_id", "business_invitations", ["business_id"])
    op.create_index("ix_business_invitations_email_normalized", "business_invitations", ["email_normalized"])


def downgrade() -> None:
    op.drop_index("ix_business_invitations_email_normalized", table_name="business_invitations")
    op.drop_index("ix_business_invitations_business_id", table_name="business_invitations")
    op.drop_table("business_invitations")
    op.drop_index("ix_audit_events_actor_created", table_name="audit_events")
    op.drop_index("ix_audit_events_business_created", table_name="audit_events")
    op.drop_table("audit_events")
