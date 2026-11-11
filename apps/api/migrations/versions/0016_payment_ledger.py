"""Create tenant-scoped payment ledger.

Revision ID: 0016_payment_ledger
Revises: 0015_merge_comm_whatsapp
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_payment_ledger"
down_revision: str | None = "0015_merge_comm_whatsapp"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("booking_id", sa.Uuid(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="succeeded", nullable=False),
        sa.Column("provider", sa.String(length=20), server_default="manual", nullable=False),
        sa.Column("payment_method", sa.String(length=20), server_default="other", nullable=False),
        sa.Column("provider_reference", sa.String(length=120), nullable=True),
        sa.Column("provider_payment_id", sa.String(length=120), nullable=True),
        sa.Column("recorded_by", sa.Uuid(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["business_id", "booking_id"], ["bookings.business_id", "bookings.id"], ondelete="RESTRICT", name="fk_payments_booking"),
        sa.ForeignKeyConstraint(["business_id", "project_id"], ["projects.business_id", "projects.id"], ondelete="RESTRICT", name="fk_payments_project"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("(booking_id IS NOT NULL AND project_id IS NULL) OR (booking_id IS NULL AND project_id IS NOT NULL)", name="payment_exactly_one_target"),
        sa.CheckConstraint("amount > 0", name="payment_amount_positive"),
        sa.CheckConstraint("length(currency) = 3", name="payment_currency_length"),
        sa.CheckConstraint("status IN ('pending', 'succeeded', 'failed', 'refunded')", name="payment_status"),
        sa.CheckConstraint("provider IN ('manual', 'paychangu')", name="payment_provider"),
        sa.CheckConstraint("payment_method IN ('cash', 'bank_transfer', 'card', 'mobile_money', 'other')", name="payment_method"),
        sa.UniqueConstraint("business_id", "provider", "provider_reference", name="uq_payments_provider_reference"),
    )
    op.create_index("ix_payments_business_created", "payments", ["business_id", "created_at"])
    op.create_index("ix_payments_business_status", "payments", ["business_id", "status"])
    op.create_index("ix_payments_booking", "payments", ["business_id", "booking_id"])
    op.create_index("ix_payments_project", "payments", ["business_id", "project_id"])
    op.execute("ALTER TABLE payments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE payments FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON payments
        USING (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)
        WITH CHECK (business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid)
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON payments")
    op.execute("ALTER TABLE payments NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE payments DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_payments_project", table_name="payments")
    op.drop_index("ix_payments_booking", table_name="payments")
    op.drop_index("ix_payments_business_status", table_name="payments")
    op.drop_index("ix_payments_business_created", table_name="payments")
    op.drop_table("payments")
