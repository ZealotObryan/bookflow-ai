from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CommunicationSettingsUpdate(BaseModel):
    assistant_enabled: bool | None = None
    assistant_greeting: str | None = Field(default=None, max_length=1000)
    assistant_booking_policy: Literal["owner_approval", "automatic"] | None = None
    notification_phone: str | None = Field(default=None, max_length=20)
    business_whatsapp_number: str | None = Field(default=None, max_length=20)

    @field_validator("assistant_greeting")
    @classmethod
    def clean_greeting(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("notification_phone", "business_whatsapp_number")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        import re
        if not re.fullmatch(r"\+[1-9][0-9]{7,14}", value):
            raise ValueError("Phone number must use international E.164 format")
        return value


class CommunicationSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    assistant_enabled: bool
    assistant_greeting: str | None
    assistant_booking_policy: str
    notification_phone: str | None
    business_whatsapp_number: str | None
    whatsapp_connection_status: str
    created_at: datetime
    updated_at: datetime
