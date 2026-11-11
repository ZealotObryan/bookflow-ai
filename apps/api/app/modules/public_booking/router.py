import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rate_limit import auth_rate_limit
from app.core.turnstile import verify_turnstile_token
from app.db.session import get_db, set_tenant_context
from app.models import Booking, Business, Customer, Service
from app.modules.bookings.router import BookingInput, SegmentInput, create_booking_for_business
from app.modules.bookings.availability import get_availability

router = APIRouter(prefix="/public/businesses", tags=["Public booking"])


class PublicService(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    duration_minutes: int
    price_amount: str
    currency: str


class PublicBookingSubmission(BaseModel):
    customer_name: str = Field(min_length=2, max_length=160)
    customer_phone: str = Field(min_length=8, max_length=20)
    customer_email: EmailStr | None = None
    service_id: uuid.UUID
    starts_at: str
    idempotency_key: str = Field(min_length=16, max_length=100)
    turnstile_token: str = Field(min_length=1, max_length=2048)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator('customer_phone')
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith('+') or not normalized[1:].isdigit() or not 8 <= len(normalized[1:]) <= 15:
            raise ValueError('Enter a valid phone number in international format, for example +265991234567')
        return normalized

    @field_validator('starts_at')
    @classmethod
    def validate_start_time(cls, value: str) -> str:
        from datetime import datetime
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError('Appointment time must include a timezone')
        return parsed.isoformat()


class PublicBookingReceipt(BaseModel):
    booking_reference: str
    status: str
    message: str
    starts_at: str
    hold_expires_at: str | None


PUBLIC_BOOKING_LIMIT = auth_rate_limit('public-booking', ip_limit=8, ip_window=600)

class PublicBusinessProfile(BaseModel):
    name: str
    slug: str
    business_type: str
    timezone: str
    currency: str
    services: list[PublicService]


@router.get("/{slug}", response_model=PublicBusinessProfile)
def get_public_business(slug: str, db: Session = Depends(get_db)):
    business = db.scalar(
        select(Business).where(
            Business.slug == slug,
            Business.status == "active",
            Business.workflow_mode.in_(("bookings", "both")),
        )
    )
    if business is None:
        raise HTTPException(status_code=404, detail="Public booking page not found")

    set_tenant_context(db, business.id)
    services = db.scalars(
        select(Service).where(
            Service.business_id == business.id,
            Service.status == "active",
        ).order_by(Service.name.asc())
    ).all()
    return PublicBusinessProfile(
        name=business.name,
        slug=business.slug,
        business_type=business.business_type,
        timezone=business.timezone,
        currency=business.currency,
        services=[
            PublicService(
                id=service.id,
                name=service.name,
                description=service.description,
                duration_minutes=service.duration_minutes,
                price_amount=str(service.price_amount),
                currency=business.currency,
            )
            for service in services
        ],
    )



@router.get("/{slug}/availability")
def get_public_availability(
    slug: str,
    service_id: uuid.UUID,
    target_date: date = Query(alias="date"),
    slot_interval_minutes: int = Query(default=15, ge=5, le=60),
    db: Session = Depends(get_db),
):
    business = db.scalar(
        select(Business).where(
            Business.slug == slug,
            Business.status == "active",
            Business.workflow_mode.in_(("bookings", "both")),
        )
    )
    if business is None:
        raise HTTPException(status_code=404, detail="Public booking page not found")
    return get_availability(
        business_id=business.id,
        service_id=service_id,
        target_date=target_date,
        employee_id=None,
        slot_interval_minutes=slot_interval_minutes,
        user=None,
        db=db,
    )
@router.post('/{slug}/bookings', response_model=PublicBookingReceipt, status_code=status.HTTP_201_CREATED, dependencies=[Depends(PUBLIC_BOOKING_LIMIT)])
async def submit_public_booking(slug: str, payload: PublicBookingSubmission, request: Request, db: Session = Depends(get_db)):
    """Accept a verified customer booking request and create a short-lived hold."""
    business = db.scalar(select(Business).where(Business.slug == slug, Business.status == 'active', Business.workflow_mode.in_(('bookings', 'both'))))
    if business is None:
        raise HTTPException(status_code=404, detail='Public booking page not found')
    set_tenant_context(db, business.id)
    existing = db.scalar(select(Booking).where(Booking.business_id == business.id, Booking.idempotency_key == payload.idempotency_key))
    if existing is not None:
        return PublicBookingReceipt(booking_reference=f'BF-{existing.id.hex[:10].upper()}', status=existing.status, message='We have already received this booking request.', starts_at=existing.starts_at.isoformat(), hold_expires_at=existing.hold_expires_at.isoformat() if existing.hold_expires_at else None)
    client_ip = request.client.host if request.client else None
    await verify_turnstile_token(payload.turnstile_token, client_ip)
    service = db.scalar(select(Service).where(Service.id == payload.service_id, Service.business_id == business.id, Service.status == 'active'))
    if service is None:
        raise HTTPException(status_code=422, detail='The selected service is unavailable.')
    customer = db.scalar(select(Customer).where(Customer.business_id == business.id, Customer.phone_e164 == payload.customer_phone))
    if customer is None:
        customer = Customer(business_id=business.id, display_name=payload.customer_name.strip(), phone_e164=payload.customer_phone, email=str(payload.customer_email).lower() if payload.customer_email else None)
        db.add(customer)
        db.flush()
    booking_payload = BookingInput(customer_id=customer.id, segments=[SegmentInput(service_id=service.id, employee_id=None, starts_at=payload.starts_at)], idempotency_key=payload.idempotency_key, notes=payload.notes)
    result = create_booking_for_business(business=business, payload=booking_payload, actor_user_id=None, db=db)
    return PublicBookingReceipt(booking_reference=result['booking_reference'], status=result['status'], message='Your request has been received. The business must confirm your appointment.', starts_at=result['starts_at'].isoformat(), hold_expires_at=result['hold_expires_at'].isoformat() if result['hold_expires_at'] else None)

