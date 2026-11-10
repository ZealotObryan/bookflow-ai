import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BusinessWhatsAppSettings(Base):
    __tablename__ = "business_whatsapp_settings"
    __table_args__ = (
        UniqueConstraint("business_id", name="uq_business_whatsapp_settings_business"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    assistant_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    greeting: Mapped[str] = mapped_column(
        String(500), nullable=False,
        default="Hello! Welcome. How can we help you today?",
        server_default="Hello! Welcome. How can we help you today?",
    )
    booking_policy: Mapped[str] = mapped_column(String(24), nullable=False, default="owner_approval", server_default="owner_approval")
    business_whatsapp_number: Mapped[str | None] = mapped_column(String(16), nullable=True)
    notify_owner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
