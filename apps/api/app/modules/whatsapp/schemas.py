from datetime import datetime
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WhatsAppSettingsUpdate(BaseModel):
    assistant_enabled: bool
    greeting: str = Field(min_length=1, max_length=500)
    booking_policy: Literal["owner_approval", "automatic"]
    business_whatsapp_number: str | None = Field(default=None, max_length=16)
    notify_owner: bool = True

    @field_validator("greeting")
    @classmethod
    def clean_greeting(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Greeting cannot be empty")
        return value

    @field_validator("business_whatsapp_number")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        import re
        if not re.fullmatch(r"\+[1-9][0-9]{7,14}", value):
            raise ValueError("Enter a WhatsApp number in international format, for example +265991234567")
        return value


class WhatsAppSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_id: UUID
    assistant_enabled: bool
    greeting: str
    booking_policy: str
    business_whatsapp_number: str | None
    notify_owner: bool
    created_at: datetime
    updated_at: datetime
