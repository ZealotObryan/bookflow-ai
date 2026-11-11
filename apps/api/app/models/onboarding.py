import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BusinessOnboardingProgress(Base):
    __tablename__ = "business_onboarding_progress"

    business_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        primary_key=True,
    )
    completed_steps: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    dismissed: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
