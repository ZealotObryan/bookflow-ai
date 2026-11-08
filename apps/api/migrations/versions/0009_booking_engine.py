"""Add buffer-aware booking reservations and employee requirements.

Revision ID: 0009_booking_engine
Revises: 0008_tenant_rls
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_booking_engine"
down_revision: str | None = "0008_tenant_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("services", sa.Column("requires_employee", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column("booking_segments", sa.Column("reserved_starts_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("booking_segments", sa.Column("reserved_ends_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE booking_segments SET reserved_starts_at = starts_at, reserved_ends_at = ends_at")
    op.alter_column("booking_segments", "reserved_starts_at", nullable=False)
    op.alter_column("booking_segments", "reserved_ends_at", nullable=False)
    op.drop_constraint("ex_booking_segments_employee_no_overlap", "booking_segments", type_="exclude")
    op.execute("""
        ALTER TABLE booking_segments
        ADD CONSTRAINT ex_booking_segments_employee_no_overlap
        EXCLUDE USING gist (
            business_id WITH =,
            employee_id WITH =,
            tstzrange(reserved_starts_at, reserved_ends_at, '[)') WITH &&
        )
        WHERE (employee_id IS NOT NULL AND status IN ('held', 'confirmed', 'in_progress'))
    """)


def downgrade() -> None:
    op.drop_constraint("ex_booking_segments_employee_no_overlap", "booking_segments", type_="exclude")
    op.execute("""
        ALTER TABLE booking_segments
        ADD CONSTRAINT ex_booking_segments_employee_no_overlap
        EXCLUDE USING gist (
            business_id WITH =,
            employee_id WITH =,
            tstzrange(starts_at, ends_at, '[)') WITH &&
        )
        WHERE (employee_id IS NOT NULL AND status IN ('held', 'confirmed', 'in_progress'))
    """)
    op.drop_column("booking_segments", "reserved_ends_at")
    op.drop_column("booking_segments", "reserved_starts_at")
    op.drop_column("services", "requires_employee")
