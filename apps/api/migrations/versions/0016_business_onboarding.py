"""Persist business onboarding progress.

Revision ID: 0016_business_onboarding
Revises: 0015_merge_comm_whatsapp
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_business_onboarding"
down_revision: str | None = "0015_merge_comm_whatsapp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "business_onboarding_progress",
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("completed_steps", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("dismissed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("business_id"),
    )
    op.execute("ALTER TABLE business_onboarding_progress ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE business_onboarding_progress FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON business_onboarding_progress
        USING (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)
        WITH CHECK (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON business_onboarding_progress")
    op.execute("ALTER TABLE business_onboarding_progress NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE business_onboarding_progress DISABLE ROW LEVEL SECURITY")
    op.drop_table("business_onboarding_progress")
