"""Add tenant-scoped service, employee and resource catalog.

Revision ID: 0006_scheduling_catalog
Revises: 0005_tenant_access
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_scheduling_catalog"
down_revision: str | None = "0005_tenant_access"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    timestamp = sa.DateTime(timezone=True)

    op.create_table(
        "services",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("business_id", uuid_type, nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("buffer_before_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("buffer_after_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("price_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_services"),
        sa.UniqueConstraint("business_id", "id", name="uq_services_business_id_id"),
        sa.CheckConstraint("length(name) >= 2", name="ck_services_name_min_length"),
        sa.CheckConstraint("duration_minutes > 0", name="ck_services_duration_positive"),
        sa.CheckConstraint("buffer_before_minutes >= 0", name="ck_services_buffer_before_nonnegative"),
        sa.CheckConstraint("buffer_after_minutes >= 0", name="ck_services_buffer_after_nonnegative"),
        sa.CheckConstraint("price_amount >= 0", name="ck_services_price_nonnegative"),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_services_service_status"),
    )
    op.create_index("ix_services_business_status", "services", ["business_id", "status"])

    op.create_table(
        "employees",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("business_id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=True),
        sa.Column("employee_code", sa.String(40), nullable=True),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("phone_e164", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_employees"),
        sa.UniqueConstraint("business_id", "id", name="uq_employees_business_id_id"),
        sa.UniqueConstraint("business_id", "employee_code", name="uq_employees_business_employee_code"),
        sa.CheckConstraint("length(display_name) >= 2", name="ck_employees_display_name_min_length"),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_employees_employee_status"),
    )
    op.create_index("ix_employees_business_status", "employees", ["business_id", "status"])

    op.create_table(
        "schedulable_resources",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("business_id", uuid_type, nullable=False),
        sa.Column("resource_code", sa.String(40), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("resource_type", sa.String(20), nullable=False),
        sa.Column("capacity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_schedulable_resources"),
        sa.UniqueConstraint("business_id", "id", name="uq_schedulable_resources_business_id_id"),
        sa.UniqueConstraint("business_id", "resource_code", name="uq_schedulable_resources_business_code"),
        sa.CheckConstraint("resource_type IN ('room', 'chair', 'bed', 'equipment', 'other')", name="ck_schedulable_resources_resource_type"),
        sa.CheckConstraint("length(name) >= 2", name="ck_schedulable_resources_resource_name_min_length"),
        sa.CheckConstraint("capacity > 0", name="ck_schedulable_resources_resource_capacity_positive"),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_schedulable_resources_resource_status"),
    )
    op.create_index("ix_schedulable_resources_business_status", "schedulable_resources", ["business_id", "status"])

    op.create_table(
        "service_employee_eligibility",
        sa.Column("business_id", uuid_type, nullable=False),
        sa.Column("service_id", uuid_type, nullable=False),
        sa.Column("employee_id", uuid_type, nullable=False),
        sa.ForeignKeyConstraint(
            ["business_id", "service_id"], ["services.business_id", "services.id"],
            ondelete="CASCADE", name="fk_service_employee_eligibility_service",
        ),
        sa.ForeignKeyConstraint(
            ["business_id", "employee_id"], ["employees.business_id", "employees.id"],
            ondelete="CASCADE", name="fk_service_employee_eligibility_employee",
        ),
        sa.PrimaryKeyConstraint("business_id", "service_id", "employee_id", name="pk_service_employee_eligibility"),
    )
    op.create_index("ix_service_employee_eligibility_employee", "service_employee_eligibility", ["business_id", "employee_id"])

    op.create_table(
        "service_resource_requirements",
        sa.Column("business_id", uuid_type, nullable=False),
        sa.Column("service_id", uuid_type, nullable=False),
        sa.Column("resource_id", uuid_type, nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(
            ["business_id", "service_id"], ["services.business_id", "services.id"],
            ondelete="CASCADE", name="fk_service_resource_requirements_service",
        ),
        sa.ForeignKeyConstraint(
            ["business_id", "resource_id"], ["schedulable_resources.business_id", "schedulable_resources.id"],
            ondelete="CASCADE", name="fk_service_resource_requirements_resource",
        ),
        sa.PrimaryKeyConstraint("business_id", "service_id", "resource_id", name="pk_service_resource_requirements"),
        sa.CheckConstraint("quantity > 0", name="ck_service_resource_requirements_quantity_positive"),
    )
    op.create_index("ix_service_resource_requirements_resource", "service_resource_requirements", ["business_id", "resource_id"])


def downgrade() -> None:
    op.drop_index("ix_service_resource_requirements_resource", table_name="service_resource_requirements")
    op.drop_table("service_resource_requirements")
    op.drop_index("ix_service_employee_eligibility_employee", table_name="service_employee_eligibility")
    op.drop_table("service_employee_eligibility")
    op.drop_index("ix_schedulable_resources_business_status", table_name="schedulable_resources")
    op.drop_table("schedulable_resources")
    op.drop_index("ix_employees_business_status", table_name="employees")
    op.drop_table("employees")
    op.drop_index("ix_services_business_status", table_name="services")
    op.drop_table("services")
