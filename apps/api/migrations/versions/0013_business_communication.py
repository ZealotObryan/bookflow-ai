"""Add tenant-scoped business communication preferences.

Revision ID: 0013_business_communication
Revises: 0012_projects
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_business_communication"
down_revision: str | None = "0012_projects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "business_communication_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("assistant_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("assistant_greeting", sa.Text(), nullable=True),
        sa.Column("assistant_booking_policy", sa.String(length=24), nullable=False, server_default="owner_approval"),
        sa.Column("notification_phone", sa.String(length=20), nullable=True),
        sa.Column("business_whatsapp_number", sa.String(length=20), nullable=True),
        sa.Column("whatsapp_connection_status", sa.String(length=24), nullable=False, server_default="not_connected"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "assistant_booking_policy IN ('owner_approval', 'automatic')",
            name="ck_business_communication_settings_assistant_booking_policy",
        ),
        sa.CheckConstraint(
            "whatsapp_connection_status IN ('not_connected', 'setup_required', 'pending_approval', "
            "'connecting', 'connected', 'attention_required', 'disconnected')",
            name="ck_business_communication_settings_whatsapp_connection_status",
        ),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", name="uq_business_communication_settings_business_id"),
    )
    op.create_index(
        "ix_business_communication_settings_business_id",
        "business_communication_settings", ["business_id"]
    )
    op.execute("ALTER TABLE business_communication_settings ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE business_communication_settings FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON business_communication_settings
        USING (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)
        WITH CHECK (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON business_communication_settings")
    op.execute("ALTER TABLE business_communication_settings NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE business_communication_settings DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_business_communication_settings_business_id", table_name="business_communication_settings")
    op.drop_table("business_communication_settings")
