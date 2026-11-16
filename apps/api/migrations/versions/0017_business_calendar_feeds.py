"""Add revocable private calendar subscriptions.

Revision ID: 0017_business_calendar_feeds
Revises: 0016_payment_ledger
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_business_calendar_feeds"
down_revision: str | None = "0016_payment_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "business_calendar_feeds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", name="uq_business_calendar_feeds_business"),
        sa.UniqueConstraint("token_hash", name="uq_business_calendar_feeds_token_hash"),
    )
    op.create_index("ix_business_calendar_feeds_token_hash", "business_calendar_feeds", ["token_hash"])
    op.execute("ALTER TABLE business_calendar_feeds ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE business_calendar_feeds FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON business_calendar_feeds
        USING (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)
        WITH CHECK (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)
    """)
    op.execute("""
        CREATE FUNCTION resolve_business_calendar_feed(p_token_hash text)
        RETURNS uuid
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT f.business_id
            FROM business_calendar_feeds AS f
            JOIN businesses AS b ON b.id = f.business_id
            WHERE f.token_hash = p_token_hash
              AND f.revoked_at IS NULL
              AND b.status = 'active'
            LIMIT 1
        $$
    """)
    op.execute("REVOKE ALL ON FUNCTION resolve_business_calendar_feed(text) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION resolve_business_calendar_feed(text) TO PUBLIC")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS resolve_business_calendar_feed(text)")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON business_calendar_feeds")
    op.execute("ALTER TABLE business_calendar_feeds NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE business_calendar_feeds DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_business_calendar_feeds_token_hash", table_name="business_calendar_feeds")
    op.drop_table("business_calendar_feeds")
