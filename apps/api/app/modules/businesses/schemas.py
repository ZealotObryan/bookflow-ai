from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BusinessCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)


class BusinessResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    timezone: str
    currency: str
    status: str
    role: str
    created_at: datetime
