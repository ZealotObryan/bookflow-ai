import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PaymentMethod = Literal["cash", "bank_transfer", "card", "mobile_money", "other"]


class ManualPaymentCreate(BaseModel):
    booking_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payment_method: PaymentMethod = "other"
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_one_target(self):
        if (self.booking_id is None) == (self.project_id is None):
            raise ValueError("Provide exactly one booking_id or project_id")
        return self


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    booking_id: uuid.UUID | None
    project_id: uuid.UUID | None
    amount: Decimal
    currency: str
    status: str
    provider: str
    payment_method: str
    provider_reference: str | None
    provider_payment_id: str | None
    recorded_by: uuid.UUID | None
    verified_at: datetime | None
    note: str | None
    created_at: datetime
    updated_at: datetime
