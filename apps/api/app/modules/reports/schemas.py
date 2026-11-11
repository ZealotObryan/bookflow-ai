from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DailyActivity(BaseModel):
    date: date
    bookings: int
    confirmed_bookings: int


class BusinessReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    business_id: UUID
    currency: str
    period: str
    bookings_total: int
    bookings_confirmed: int
    bookings_held: int
    bookings_cancelled: int
    confirmed_booking_value: Decimal
    project_count: int
    project_quoted_value: Decimal
    project_amount_recorded_paid: Decimal
    project_outstanding_value: Decimal
    daily_activity: list[DailyActivity]
