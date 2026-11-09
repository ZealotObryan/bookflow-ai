"""Add transactional booking segment resource allocations.

Revision ID: 0010_booking_resources
Revises: 0009_booking_engine
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_booking_resources"
down_revision: str | None = "0009_booking_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_booking_segments_business_id_id", "booking_segments", ["business_id", "id"]
    )
    op.create_table(
        "booking_segment_resources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("booking_segment_id", sa.Uuid(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="allocation_quantity_positive"),
        sa.ForeignKeyConstraint(["business_id", "booking_segment_id"], ["booking_segments.business_id", "booking_segments.id"], ondelete="CASCADE", name="fk_booking_segment_resources_segment"),
        sa.ForeignKeyConstraint(["business_id", "resource_id"], ["schedulable_resources.business_id", "schedulable_resources.id"], ondelete="RESTRICT", name="fk_booking_segment_resources_resource"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "booking_segment_id", "resource_id", name="uq_booking_segment_resource"),
    )
    op.create_index("ix_booking_segment_resources_resource", "booking_segment_resources", ["business_id", "resource_id", "booking_segment_id"])
    op.execute("ALTER TABLE booking_segment_resources ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE booking_segment_resources FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON booking_segment_resources
        USING (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)
        WITH CHECK (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON booking_segment_resources")
    op.execute("ALTER TABLE booking_segment_resources NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE booking_segment_resources DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_booking_segment_resources_resource", table_name="booking_segment_resources")
    op.drop_table("booking_segment_resources")
    op.drop_constraint(
        "uq_booking_segments_business_id_id", "booking_segments", type_="unique"
    )
