"""Add customers, operating hours and booking records.

Revision ID: 0007_booking_foundation
Revises: 0006_scheduling_catalog
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_booking_foundation"
down_revision: str | None = "0006_scheduling_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uid = postgresql.UUID(as_uuid=True)
    ts = sa.DateTime(timezone=True)

    op.create_table(
        "customers",
        sa.Column("id", uid, nullable=False),
        sa.Column("business_id", uid, nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("phone_e164", sa.String(20), nullable=True),
        sa.Column("notes", sa.String(2000), nullable=True),
        sa.Column("created_at", ts, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_customers"),
        sa.UniqueConstraint("business_id", "id", name="uq_customers_business_id_id"),
        sa.CheckConstraint("length(display_name) >= 2", name="ck_customers_display_name_min_length"),
    )
    op.create_index("ix_customers_business_phone", "customers", ["business_id", "phone_e164"])

    op.create_table(
        "business_weekly_hours",
        sa.Column("business_id", uid, nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("opens_at", sa.Time(), nullable=True),
        sa.Column("closes_at", sa.Time(), nullable=True),
        sa.Column("is_closed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("business_id", "weekday", name="pk_business_weekly_hours"),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_business_weekly_hours_weekday_range"),
        sa.CheckConstraint(
            "(is_closed = true AND opens_at IS NULL AND closes_at IS NULL) OR "
            "(is_closed = false AND opens_at IS NOT NULL AND closes_at IS NOT NULL AND opens_at < closes_at)",
            name="ck_business_weekly_hours_hours_valid",
        ),
    )

    op.create_table(
        "employee_weekly_hours",
        sa.Column("business_id", uid, nullable=False),
        sa.Column("employee_id", uid, nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.Time(), nullable=True),
        sa.Column("ends_at", sa.Time(), nullable=True),
        sa.Column("is_unavailable", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.ForeignKeyConstraint(
            ["business_id", "employee_id"], ["employees.business_id", "employees.id"],
            ondelete="CASCADE", name="fk_employee_weekly_hours_employee",
        ),
        sa.PrimaryKeyConstraint("business_id", "employee_id", "weekday", name="pk_employee_weekly_hours"),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_employee_weekly_hours_weekday_range"),
        sa.CheckConstraint(
            "(is_unavailable = true AND starts_at IS NULL AND ends_at IS NULL) OR "
            "(is_unavailable = false AND starts_at IS NOT NULL AND ends_at IS NOT NULL AND starts_at < ends_at)",
            name="ck_employee_weekly_hours_hours_valid",
        ),
    )

    op.create_table(
        "employee_time_off",
        sa.Column("id", uid, nullable=False),
        sa.Column("business_id", uid, nullable=False),
        sa.Column("employee_id", uid, nullable=False),
        sa.Column("starts_at", ts, nullable=False),
        sa.Column("ends_at", ts, nullable=False),
        sa.Column("reason", sa.String(300), nullable=True),
        sa.Column("created_at", ts, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["business_id", "employee_id"], ["employees.business_id", "employees.id"],
            ondelete="CASCADE", name="fk_employee_time_off_employee",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_employee_time_off"),
        sa.UniqueConstraint("business_id", "id", name="uq_employee_time_off_business_id_id"),
        sa.CheckConstraint("ends_at > starts_at", name="ck_employee_time_off_time_off_range_valid"),
    )
    op.create_index(
        "ix_employee_time_off_employee_range", "employee_time_off",
        ["business_id", "employee_id", "starts_at", "ends_at"],
    )

    op.create_table(
        "bookings",
        sa.Column("id", uid, nullable=False),
        sa.Column("business_id", uid, nullable=False),
        sa.Column("customer_id", uid, nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), server_default="held", nullable=False),
        sa.Column("starts_at", ts, nullable=False),
        sa.Column("ends_at", ts, nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("hold_expires_at", ts, nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("created_at", ts, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", ts, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["business_id", "customer_id"], ["customers.business_id", "customers.id"],
            ondelete="RESTRICT", name="fk_bookings_customer",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_bookings"),
        sa.UniqueConstraint("business_id", "id", name="uq_bookings_business_id_id"),
        sa.UniqueConstraint("business_id", "idempotency_key", name="uq_bookings_business_idempotency_key"),
        sa.CheckConstraint(
            "status IN ('held', 'confirmed', 'cancelled', 'completed', 'no_show', 'expired')",
            name="ck_bookings_booking_status",
        ),
        sa.CheckConstraint("ends_at > starts_at", name="ck_bookings_booking_range_valid"),
        sa.CheckConstraint("total_amount >= 0", name="ck_bookings_total_amount_nonnegative"),
    )
    op.create_index("ix_bookings_business_start", "bookings", ["business_id", "starts_at"])
    op.create_index("ix_bookings_business_status", "bookings", ["business_id", "status"])

    op.create_table(
        "booking_segments",
        sa.Column("id", uid, nullable=False),
        sa.Column("business_id", uid, nullable=False),
        sa.Column("booking_id", uid, nullable=False),
        sa.Column("service_id", uid, nullable=False),
        sa.Column("employee_id", uid, nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("starts_at", ts, nullable=False),
        sa.Column("ends_at", ts, nullable=False),
        sa.Column("status", sa.String(20), server_default="held", nullable=False),
        sa.Column("service_name_snapshot", sa.String(120), nullable=False),
        sa.Column("duration_minutes_snapshot", sa.Integer(), nullable=False),
        sa.Column("price_amount_snapshot", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", ts, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["business_id", "booking_id"], ["bookings.business_id", "bookings.id"],
            ondelete="CASCADE", name="fk_booking_segments_booking",
        ),
        sa.ForeignKeyConstraint(
            ["business_id", "service_id"], ["services.business_id", "services.id"],
            ondelete="RESTRICT", name="fk_booking_segments_service",
        ),
        sa.ForeignKeyConstraint(
            ["business_id", "employee_id"], ["employees.business_id", "employees.id"],
            ondelete="RESTRICT", name="fk_booking_segments_employee",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_booking_segments"),
        sa.CheckConstraint("ends_at > starts_at", name="ck_booking_segments_segment_range_valid"),
        sa.CheckConstraint("sequence_number > 0", name="ck_booking_segments_sequence_number_positive"),
        sa.CheckConstraint(
            "status IN ('held', 'confirmed', 'in_progress', 'completed', 'cancelled')",
            name="ck_booking_segments_segment_status",
        ),
        sa.UniqueConstraint(
            "business_id", "booking_id", "sequence_number",
            name="uq_booking_segments_sequence",
        ),
    )
    op.create_index(
        "ix_booking_segments_business_employee_start", "booking_segments",
        ["business_id", "employee_id", "starts_at"],
    )
    op.create_index(
        "ix_booking_segments_business_booking", "booking_segments", ["business_id", "booking_id"]
    )

    # A database-level exclusion constraint prevents concurrent overlapping active
    # assignments for the same employee. Resource capacity > 1 is enforced by the
    # booking service using a locked resource row and a transactional occupancy count.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
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


def downgrade() -> None:
    op.drop_constraint(
        "ex_booking_segments_employee_no_overlap", "booking_segments", type_="exclude"
    )
    op.drop_index("ix_booking_segments_business_booking", table_name="booking_segments")
    op.drop_index("ix_booking_segments_business_employee_start", table_name="booking_segments")
    op.drop_table("booking_segments")
    op.drop_index("ix_bookings_business_status", table_name="bookings")
    op.drop_index("ix_bookings_business_start", table_name="bookings")
    op.drop_table("bookings")
    op.drop_index("ix_employee_time_off_employee_range", table_name="employee_time_off")
    op.drop_table("employee_time_off")
    op.drop_table("employee_weekly_hours")
    op.drop_table("business_weekly_hours")
    op.drop_index("ix_customers_business_phone", table_name="customers")
    op.drop_table("customers")
