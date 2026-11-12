"""Create tenant-scoped projects and work tracking.

Revision ID: 0012_projects
Revises: 0011_merge_heads
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_projects"
down_revision: str | None = "0011_merge_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("client_name", sa.String(length=160), nullable=False),
        sa.Column("client_phone", sa.String(length=30), nullable=True),
        sa.Column("client_email", sa.String(length=320), nullable=True),
        sa.Column("project_type", sa.String(length=80), nullable=False, server_default="general"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="enquiry"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("quoted_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("deposit_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("amount_paid", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="MWK"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('enquiry', 'quoted', 'booked', 'in_progress', 'editing', 'review', 'delivered', 'cancelled')", name="ck_projects_project_status"),
        sa.CheckConstraint("quoted_amount >= 0", name="ck_projects_project_quoted_amount_nonnegative"),
        sa.CheckConstraint("deposit_amount >= 0", name="ck_projects_project_deposit_nonnegative"),
        sa.CheckConstraint("amount_paid >= 0", name="ck_projects_project_amount_paid_nonnegative"),
        sa.CheckConstraint("deposit_amount <= quoted_amount", name="ck_projects_project_deposit_within_quote"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_business_status_due", "projects", ["business_id", "status", "due_date"])
    op.create_index("ix_projects_business_created", "projects", ["business_id", "created_at"])
    op.execute("ALTER TABLE projects ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE projects FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON projects
        USING (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)
        WITH CHECK (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON projects")
    op.execute("ALTER TABLE projects NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE projects DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_projects_business_created", table_name="projects")
    op.drop_index("ix_projects_business_status_due", table_name="projects")
    op.drop_table("projects")
