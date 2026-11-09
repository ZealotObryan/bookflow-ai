from datetime import datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class BusinessCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    business_type: str = Field(default="other", min_length=2, max_length=40)
    workflow_mode: Literal["bookings", "tracking", "both"] = "both"
    whatsapp_priority: Literal["essential", "important", "not_now"] = "important"


class BusinessProfileUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    business_type: str = Field(min_length=2, max_length=40)
    workflow_mode: Literal["bookings", "tracking", "both"]
    whatsapp_priority: Literal["essential", "important", "not_now"]


class BusinessResponse(BaseModel):
    id: UUID
    name: str
    business_type: str
    workflow_mode: str
    whatsapp_priority: str
    slug: str
    timezone: str
    currency: str
    status: str
    role: str
    created_at: datetime


class MemberResponse(BaseModel):
    membership_id: UUID
    user_id: UUID
    email: EmailStr
    full_name: str
    role: str
    status: str
    created_at: datetime


class InvitationCreateRequest(BaseModel):
    email: EmailStr
    role: str


class InvitationResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    expires_at: datetime
    status: str


class InvitationAcceptRequest(BaseModel):
    token: str = Field(min_length=32, max_length=128)


class MembershipUpdateRequest(BaseModel):
    role: str | None = None
    status: str | None = None
