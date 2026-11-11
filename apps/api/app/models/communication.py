import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BusinessCommunicationSettings(Base):
    __tablename__ = "business_communication_settings"
    __table_args__ = (
        UniqueConstraint("business_id", name="uq_business_communication_settings_business_id"),
        CheckConstraint(
            "assistant_booking_policy IN ('owner_approval', 'automatic')",
            name="assistant_booking_policy",
        ),
        CheckConstraint(
            "whatsapp_connection_status IN ('not_connected', 'setup_required', 'pending_approval', "
            "'connecting', 'connected', 'attention_required', 'disconnected')",
            name="whatsapp_connection_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assistant_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    assistant_greeting: Mapped[str | None] = mapped_column(Text, nullable=True)
    assistant_booking_policy: Mapped[str] = mapped_column(
        String(24), nullable=False, default="owner_approval", server_default="owner_approval"
    )
    notification_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    business_whatsapp_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    whatsapp_connection_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="not_connected", server_default="not_connected"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
