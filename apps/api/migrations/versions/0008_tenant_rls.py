"""Force row-level tenant isolation for tenant-owned records.

Revision ID: 0008_tenant_rls
Revises: 0007_booking_foundation
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0008_tenant_rls"
down_revision: str | None = "0007_booking_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = (
    "audit_events",
    "services",
    "employees",
    "schedulable_resources",
    "service_employee_eligibility",
    "service_resource_requirements",
    "customers",
    "business_weekly_hours",
    "employee_weekly_hours",
    "employee_time_off",
    "bookings",
    "booking_segments",
)


def upgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (
                business_id = NULLIF(
                    current_setting('app.current_business_id', true), ''
                )::uuid
            )
            WITH CHECK (
                business_id = NULLIF(
                    current_setting('app.current_business_id', true), ''
                )::uuid
            )
            """
        )


def downgrade() -> None:
    for table in reversed(TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
