import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "status IN ('enquiry', 'quoted', 'booked', 'in_progress', 'editing', 'review', 'delivered', 'cancelled')",
            name="project_status",
        ),
        CheckConstraint("quoted_amount >= 0", name="project_quoted_amount_nonnegative"),
        CheckConstraint("deposit_amount >= 0", name="project_deposit_nonnegative"),
        CheckConstraint("amount_paid >= 0", name="project_amount_paid_nonnegative"),
        CheckConstraint("deposit_amount <= quoted_amount", name="project_deposit_within_quote"),
        Index("ix_projects_business_status_due", "business_id", "status", "due_date"),
        Index("ix_projects_business_created", "business_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    client_name: Mapped[str] = mapped_column(String(160), nullable=False)
    client_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    client_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    project_type: Mapped[str] = mapped_column(String(80), nullable=False, default="general")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="enquiry", server_default="enquiry")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    quoted_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="MWK", server_default="MWK")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
