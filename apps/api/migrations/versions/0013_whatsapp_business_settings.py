"""Add tenant-scoped WhatsApp channel preferences.

Revision ID: 0013_whatsapp_business_settings
Revises: 0012_projects
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_whatsapp_business_settings"
down_revision: str | None = "0012_projects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "business_whatsapp_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("assistant_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("greeting", sa.String(length=500), nullable=False,
                  server_default="Hello! Welcome. How can we help you today?"),
        sa.Column("booking_policy", sa.String(length=24), nullable=False, server_default="owner_approval"),
        sa.Column("business_whatsapp_number", sa.String(length=16), nullable=True),
        sa.Column("notify_owner", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("booking_policy IN ('owner_approval', 'automatic')", name="ck_whatsapp_settings_booking_policy"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", name="uq_business_whatsapp_settings_business"),
    )
    op.execute("ALTER TABLE business_whatsapp_settings ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE business_whatsapp_settings FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON business_whatsapp_settings
        USING (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)
        WITH CHECK (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON business_whatsapp_settings")
    op.execute("ALTER TABLE business_whatsapp_settings NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE business_whatsapp_settings DISABLE ROW LEVEL SECURITY")
    op.drop_table("business_whatsapp_settings")
