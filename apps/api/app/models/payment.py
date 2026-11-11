import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        ForeignKeyConstraint(["business_id", "booking_id"], ["bookings.business_id", "bookings.id"], ondelete="RESTRICT", name="fk_payments_booking"),
        ForeignKeyConstraint(["business_id", "project_id"], ["projects.business_id", "projects.id"], ondelete="RESTRICT", name="fk_payments_project"),
        CheckConstraint("(booking_id IS NOT NULL AND project_id IS NULL) OR (booking_id IS NULL AND project_id IS NOT NULL)", name="payment_exactly_one_target"),
        CheckConstraint("amount > 0", name="payment_amount_positive"),
        CheckConstraint("length(currency) = 3", name="payment_currency_length"),
        CheckConstraint("status IN ('pending', 'succeeded', 'failed', 'refunded')", name="payment_status"),
        CheckConstraint("provider IN ('manual', 'paychangu')", name="payment_provider"),
        CheckConstraint("payment_method IN ('cash', 'bank_transfer', 'card', 'mobile_money', 'other')", name="payment_method"),
        Index("ix_payments_business_created", "business_id", "created_at"),
        Index("ix_payments_business_status", "business_id", "status"),
        Index("ix_payments_booking", "business_id", "booking_id"),
        Index("ix_payments_project", "business_id", "project_id"),
        UniqueConstraint("business_id", "provider", "provider_reference", name="uq_payments_provider_reference"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="succeeded", server_default="succeeded")
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="manual", server_default="manual")
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False, default="other", server_default="other")
    provider_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
