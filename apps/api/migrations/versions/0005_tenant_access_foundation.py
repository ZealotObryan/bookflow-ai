"""Add database primitives for tenant audit and access foundations.

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


def downgrade() -> None:
    op.drop_index("ix_audit_events_actor_created", table_name="audit_events")
    op.drop_index("ix_audit_events_business_created", table_name="audit_events")
    op.drop_table("audit_events")
