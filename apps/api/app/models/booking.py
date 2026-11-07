import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Time,
    Uuid,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("business_id", "id", name="uq_customers_business_id_id"),
        Index("ix_customers_business_phone", "business_id", "phone_e164"),
        CheckConstraint("length(display_name) >= 2", name="display_name_min_length"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone_e164: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class BusinessWeeklyHours(Base):
    __tablename__ = "business_weekly_hours"
    __table_args__ = (
        ForeignKeyConstraint(["business_id"], ["businesses.id"], ondelete="CASCADE"),
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday_range"),
        CheckConstraint(
            "(is_closed = true AND opens_at IS NULL AND closes_at IS NULL) OR "
            "(is_closed = false AND opens_at IS NOT NULL AND closes_at IS NOT NULL AND opens_at < closes_at)",
            name="hours_valid",
        ),
    )

    business_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    weekday: Mapped[int] = mapped_column(Integer, primary_key=True)
    opens_at: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    closes_at: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    is_closed: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")


class EmployeeWeeklyHours(Base):
    __tablename__ = "employee_weekly_hours"
    __table_args__ = (
        ForeignKeyConstraint(
            ["business_id", "employee_id"],
            ["employees.business_id", "employees.id"],
            ondelete="CASCADE",
            name="fk_employee_weekly_hours_employee",
        ),
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday_range"),
        CheckConstraint(
            "(is_unavailable = true AND starts_at IS NULL AND ends_at IS NULL) OR "
            "(is_unavailable = false AND starts_at IS NOT NULL AND ends_at IS NOT NULL AND starts_at < ends_at)",
            name="hours_valid",
        ),
    )

    business_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    weekday: Mapped[int] = mapped_column(Integer, primary_key=True)
    starts_at: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    ends_at: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)
    is_unavailable: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")


class EmployeeTimeOff(Base):
    __tablename__ = "employee_time_off"
    __table_args__ = (
        UniqueConstraint("business_id", "id", name="uq_employee_time_off_business_id_id"),
        ForeignKeyConstraint(
            ["business_id", "employee_id"],
            ["employees.business_id", "employees.id"],
            ondelete="CASCADE",
            name="fk_employee_time_off_employee",
        ),
        CheckConstraint("ends_at > starts_at", name="time_off_range_valid"),
        Index("ix_employee_time_off_employee_range", "business_id", "employee_id", "starts_at", "ends_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("business_id", "id", name="uq_bookings_business_id_id"),
        UniqueConstraint("business_id", "idempotency_key", name="uq_bookings_business_idempotency_key"),
        ForeignKeyConstraint(
            ["business_id", "customer_id"],
            ["customers.business_id", "customers.id"],
            ondelete="RESTRICT",
            name="fk_bookings_customer",
        ),
        CheckConstraint(
            "status IN ('held', 'confirmed', 'cancelled', 'completed', 'no_show', 'expired')",
            name="booking_status",
        ),
        CheckConstraint("ends_at > starts_at", name="booking_range_valid"),
        CheckConstraint("total_amount >= 0", name="total_amount_nonnegative"),
        Index("ix_bookings_business_start", "business_id", "starts_at"),
        Index("ix_bookings_business_status", "business_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="held", server_default="held")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    hold_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class BookingSegment(Base):
    __tablename__ = "booking_segments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["business_id", "booking_id"],
            ["bookings.business_id", "bookings.id"],
            ondelete="CASCADE",
            name="fk_booking_segments_booking",
        ),
        ForeignKeyConstraint(
            ["business_id", "service_id"],
            ["services.business_id", "services.id"],
            ondelete="RESTRICT",
            name="fk_booking_segments_service",
        ),
        ForeignKeyConstraint(
            ["business_id", "employee_id"],
            ["employees.business_id", "employees.id"],
            ondelete="RESTRICT",
            name="fk_booking_segments_employee",
        ),
        CheckConstraint("ends_at > starts_at", name="segment_range_valid"),
        CheckConstraint("sequence_number > 0", name="sequence_number_positive"),
        CheckConstraint(
            "status IN ('held', 'confirmed', 'in_progress', 'completed', 'cancelled')",
            name="segment_status",
        ),
        UniqueConstraint("business_id", "booking_id", "sequence_number", name="uq_booking_segments_sequence"),
        Index("ix_booking_segments_business_employee_start", "business_id", "employee_id", "starts_at"),
        Index("ix_booking_segments_business_booking", "business_id", "booking_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    booking_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    service_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    employee_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="held", server_default="held")
    service_name_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)
    duration_minutes_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    price_amount_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
