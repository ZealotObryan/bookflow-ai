import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Service(Base):
    __tablename__ = "services"
    __table_args__ = (
        UniqueConstraint("business_id", "id", name="uq_services_business_id_id"),
        CheckConstraint("length(name) >= 2", name="name_min_length"),
        CheckConstraint("duration_minutes > 0", name="duration_positive"),
        CheckConstraint("buffer_before_minutes >= 0", name="buffer_before_nonnegative"),
        CheckConstraint("buffer_after_minutes >= 0", name="buffer_after_nonnegative"),
        CheckConstraint("price_amount >= 0", name="price_nonnegative"),
        CheckConstraint("status IN ('active', 'inactive')", name="service_status"),
        Index("ix_services_business_status", "business_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    buffer_before_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    buffer_after_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    price_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint("business_id", "id", name="uq_employees_business_id_id"),
        UniqueConstraint("business_id", "employee_code", name="uq_employees_business_employee_code"),
        CheckConstraint("length(display_name) >= 2", name="display_name_min_length"),
        CheckConstraint("status IN ('active', 'inactive')", name="employee_status"),
        Index("ix_employees_business_status", "business_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    employee_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone_e164: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class SchedulableResource(Base):
    __tablename__ = "schedulable_resources"
    __table_args__ = (
        UniqueConstraint("business_id", "id", name="uq_schedulable_resources_business_id_id"),
        UniqueConstraint("business_id", "resource_code", name="uq_schedulable_resources_business_code"),
        CheckConstraint("resource_type IN ('room', 'chair', 'bed', 'equipment', 'other')", name="resource_type"),
        CheckConstraint("length(name) >= 2", name="resource_name_min_length"),
        CheckConstraint("capacity > 0", name="resource_capacity_positive"),
        CheckConstraint("status IN ('active', 'inactive')", name="resource_status"),
        Index("ix_schedulable_resources_business_status", "business_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    resource_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class ServiceEmployeeEligibility(Base):
    __tablename__ = "service_employee_eligibility"
    __table_args__ = (
        ForeignKeyConstraint(
            ["business_id", "service_id"],
            ["services.business_id", "services.id"],
            ondelete="CASCADE",
            name="fk_service_employee_eligibility_service",
        ),
        ForeignKeyConstraint(
            ["business_id", "employee_id"],
            ["employees.business_id", "employees.id"],
            ondelete="CASCADE",
            name="fk_service_employee_eligibility_employee",
        ),
        Index("ix_service_employee_eligibility_employee", "business_id", "employee_id"),
    )

    business_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    service_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)


class ServiceResourceRequirement(Base):
    __tablename__ = "service_resource_requirements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["business_id", "service_id"],
            ["services.business_id", "services.id"],
            ondelete="CASCADE",
            name="fk_service_resource_requirements_service",
        ),
        ForeignKeyConstraint(
            ["business_id", "resource_id"],
            ["schedulable_resources.business_id", "schedulable_resources.id"],
            ondelete="CASCADE",
            name="fk_service_resource_requirements_resource",
        ),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        Index("ix_service_resource_requirements_resource", "business_id", "resource_id"),
    )

    business_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    service_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    resource_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
