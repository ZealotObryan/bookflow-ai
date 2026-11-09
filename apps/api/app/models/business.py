import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Business(Base):
    __tablename__ = "businesses"
    __table_args__ = (
        CheckConstraint("length(currency) = 3", name="currency_length"),
        CheckConstraint(
            "business_type IN ('salon', 'nail_tech', 'barber', 'designer_tailor', "
            "'event_planner', 'photographer', 'fitness_wellness', 'consultant', 'other')",
            name="business_type",
        ),
        CheckConstraint("workflow_mode IN ('bookings', 'tracking', 'both')", name="workflow_mode"),
        CheckConstraint(
            "whatsapp_priority IN ('essential', 'important', 'not_now')",
            name="whatsapp_priority",
        ),
        CheckConstraint(
            "status IN ('active', 'suspended', 'closed')",
            name="business_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    business_type: Mapped[str] = mapped_column(String(40), nullable=False, default="other", server_default="other")
    workflow_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="both", server_default="both")
    whatsapp_priority: Mapped[str] = mapped_column(String(20), nullable=False, default="important", server_default="important")
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Africa/Blantyre", server_default="Africa/Blantyre"
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="MWK", server_default="MWK")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    memberships: Mapped[list["BusinessMembership"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )


class BusinessMembership(Base):
    __tablename__ = "business_memberships"
    __table_args__ = (
        UniqueConstraint("business_id", "user_id", name="uq_business_memberships_business_user"),
        CheckConstraint(
            "role IN ('owner', 'admin', 'manager', 'staff')",
            name="membership_role",
        ),
        CheckConstraint(
            "status IN ('invited', 'active', 'suspended')",
            name="membership_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    business: Mapped[Business] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")
