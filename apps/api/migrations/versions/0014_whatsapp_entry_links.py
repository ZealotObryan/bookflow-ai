"""Add revocable, expiring WhatsApp business entry links.

Revision ID: 0014_whatsapp_entry_links
Revises: 0013_whatsapp_business_settings
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_whatsapp_entry_links"
down_revision: str | None = "0013_whatsapp_business_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "whatsapp_entry_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_whatsapp_entry_links_token_hash"),
    )
    op.create_index("ix_whatsapp_entry_links_business_id", "whatsapp_entry_links", ["business_id"])
    op.create_index("ix_whatsapp_entry_links_token_hash", "whatsapp_entry_links", ["token_hash"])
    op.execute("ALTER TABLE whatsapp_entry_links ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE whatsapp_entry_links FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON whatsapp_entry_links
        USING (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)
        WITH CHECK (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON whatsapp_entry_links")
    op.execute("ALTER TABLE whatsapp_entry_links NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE whatsapp_entry_links DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_whatsapp_entry_links_token_hash", table_name="whatsapp_entry_links")
    op.drop_index("ix_whatsapp_entry_links_business_id", table_name="whatsapp_entry_links")
    op.drop_table("whatsapp_entry_links")
