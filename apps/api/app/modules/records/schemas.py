import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CustomerCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=160)
    email: str | None = Field(default=None, max_length=320)
    phone_e164: str | None = Field(default=None, min_length=7, max_length=20)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Name must contain at least two characters")
        return value


class CustomerUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=160)
    email: str | None = Field(default=None, max_length=320)
    phone_e164: str | None = Field(default=None, min_length=7, max_length=20)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Name must contain at least two characters")
        return value


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    display_name: str
    email: str | None
    phone_e164: str | None
    notes: str | None
    created_at: datetime


class ServiceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    duration_minutes: int = Field(gt=0, le=1440)
    price_amount: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    requires_employee: bool = True
    status: str = "active"

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Service name must contain at least two characters")
        return value

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        if value not in {"active", "inactive"}:
            raise ValueError("Status must be active or inactive")
        return value


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    duration_minutes: int | None = Field(default=None, gt=0, le=1440)
    price_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    requires_employee: bool | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str | None) -> str | None:
        if value is not None and value not in {"active", "inactive"}:
            raise ValueError("Status must be active or inactive")
        return value


class ServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    description: str | None
    duration_minutes: int
    price_amount: Decimal
    requires_employee: bool
    status: str
    created_at: datetime
    updated_at: datetime
