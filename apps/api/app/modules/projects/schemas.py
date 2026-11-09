import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ProjectStatus = Literal[
    "enquiry", "quoted", "booked", "in_progress", "editing", "review", "delivered", "cancelled"
]


class ProjectCreate(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    client_name: str = Field(min_length=2, max_length=160)
    client_phone: str | None = Field(default=None, max_length=30)
    client_email: str | None = Field(default=None, max_length=320)
    project_type: str = Field(default="general", min_length=2, max_length=80)
    status: ProjectStatus = "enquiry"
    description: str | None = Field(default=None, max_length=5000)
    due_date: date | None = None
    quoted_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    deposit_amount: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    amount_paid: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)

    @field_validator("title", "client_name", "project_type")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Must contain at least two characters")
        return value

    @model_validator(mode="after")
    def validate_money(self):
        if self.deposit_amount > self.quoted_amount:
            raise ValueError("Deposit cannot exceed the quoted amount")
        if self.amount_paid > self.quoted_amount:
            raise ValueError("Amount paid cannot exceed the quoted amount")
        return self


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=180)
    client_name: str | None = Field(default=None, min_length=2, max_length=160)
    client_phone: str | None = Field(default=None, max_length=30)
    client_email: str | None = Field(default=None, max_length=320)
    project_type: str | None = Field(default=None, min_length=2, max_length=80)
    status: ProjectStatus | None = None
    description: str | None = Field(default=None, max_length=5000)
    due_date: date | None = None
    quoted_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    deposit_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    amount_paid: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)

    @model_validator(mode="after")
    def validate_money(self):
        quote = self.quoted_amount
        deposit = self.deposit_amount
        paid = self.amount_paid
        if quote is not None and deposit is not None and deposit > quote:
            raise ValueError("Deposit cannot exceed the quoted amount")
        if quote is not None and paid is not None and paid > quote:
            raise ValueError("Amount paid cannot exceed the quoted amount")
        return self


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    title: str
    client_name: str
    client_phone: str | None
    client_email: str | None
    project_type: str
    status: str
    description: str | None
    due_date: date | None
    quoted_amount: Decimal
    deposit_amount: Decimal
    amount_paid: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime
