import asyncio
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException, Request
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import AuditEvent, Booking, Business, BusinessWeeklyHours, Customer, Service
from app.modules.public_booking import router as public_booking
from app.modules.public_booking.router import (
    PublicBookingSubmission,
    get_public_availability,
    get_public_business,
    submit_public_booking,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_public_business_returns_active_services_only(db_session):
    business = Business(
        name="Public Studio",
        slug=f"public-{uuid4().hex[:8]}",
        workflow_mode="bookings",
    )
    db_session.add(business)
    db_session.flush()
    active = Service(
        business_id=business.id,
        name="Consultation",
        duration_minutes=30,
        price_amount=Decimal("5000.00"),
        requires_employee=False,
        status="active",
    )
    inactive = Service(
        business_id=business.id,
        name="Old service",
        duration_minutes=30,
        price_amount=Decimal("1000.00"),
        requires_employee=False,
        status="inactive",
    )
    db_session.add_all([active, inactive])
    db_session.commit()

    result = get_public_business(business.slug, db_session)

    assert result.name == "Public Studio"
    assert [service.name for service in result.services] == ["Consultation"]
    assert result.services[0].price_amount == "5000.00"


def test_tracking_only_business_has_no_public_booking_page(db_session):
    business = Business(
        name="Private Projects",
        slug=f"tracking-{uuid4().hex[:8]}",
        workflow_mode="tracking",
    )
    db_session.add(business)
    db_session.commit()

    with pytest.raises(HTTPException) as error:
        get_public_business(business.slug, db_session)

    assert error.value.status_code == 404


def test_public_availability_returns_slots_for_public_business(db_session):
    business = Business(
        name="Public Studio",
        slug=f"public-{uuid4().hex[:8]}",
        workflow_mode="bookings",
    )
    db_session.add(business)
    db_session.flush()
    service = Service(
        business_id=business.id,
        name="Consultation",
        duration_minutes=30,
        price_amount=Decimal("5000.00"),
        requires_employee=False,
        status="active",
    )
    db_session.add(service)
    db_session.add(BusinessWeeklyHours(
        business_id=business.id,
        weekday=0,
        opens_at=time(8),
        closes_at=time(17),
        is_closed=False,
    ))
    db_session.commit()

    result = get_public_availability(
        slug=business.slug,
        service_id=service.id,
        target_date=date(2026, 11, 16),
        slot_interval_minutes=30,
        db=db_session,
    )

    assert result["timezone"] == business.timezone
    assert result["slots"]
    assert all(slot["starts_at"] < slot["ends_at"] for slot in result["slots"])

def test_public_booking_creates_held_request_after_turnstile_verification(db_session, monkeypatch):
    business = Business(name='Verified Studio', slug=f'verified-{uuid4().hex[:8]}', workflow_mode='bookings')
    db_session.add(business)
    db_session.flush()
    service = Service(business_id=business.id, name='Consultation', duration_minutes=30, price_amount=Decimal('5000.00'), requires_employee=False, status='active')
    appointment_day = date.today() + timedelta(days=3)
    db_session.add(service)
    db_session.add(BusinessWeeklyHours(business_id=business.id, weekday=appointment_day.weekday(), opens_at=time(8), closes_at=time(17), is_closed=False))
    db_session.commit()

    async def verified(_token, _ip):
        return None

    monkeypatch.setattr(public_booking, 'verify_turnstile_token', verified)
    starts_at = datetime.combine(appointment_day, time(10), tzinfo=ZoneInfo(business.timezone))
    payload = PublicBookingSubmission(customer_name='Alex Customer', customer_phone='+265991234567', customer_email='alex@example.com', service_id=service.id, starts_at=starts_at.isoformat(), idempotency_key=f'public-{uuid4().hex}', turnstile_token='verified-test-token')
    request = Request({'type': 'http', 'method': 'POST', 'path': '/api/v1/public/businesses/test/bookings', 'headers': [], 'query_string': b'', 'client': ('203.0.113.10', 12345)})

    receipt = asyncio.run(submit_public_booking(business.slug, payload, request, db_session))
    booking = db_session.scalar(select(Booking).where(Booking.business_id == business.id))
    audit = db_session.scalar(select(AuditEvent).where(AuditEvent.business_id == business.id))
    assert receipt.status == 'held'
    assert receipt.booking_reference.startswith('BF-')
    assert 'must confirm' in receipt.message
    assert booking is not None and booking.status == 'held'
    assert audit is not None and audit.actor_user_id is None



def test_public_booking_retry_replays_existing_hold_without_duplicate_records(db_session, monkeypatch):
    business = Business(
        name="Retry Studio",
        slug=f"retry-{uuid4().hex[:8]}",
        workflow_mode="bookings",
    )
    db_session.add(business)
    db_session.flush()
    service = Service(
        business_id=business.id,
        name="Consultation",
        duration_minutes=30,
        price_amount=Decimal("5000.00"),
        requires_employee=False,
        status="active",
    )
    appointment_day = date.today() + timedelta(days=3)
    db_session.add(service)
    db_session.add(
        BusinessWeeklyHours(
            business_id=business.id,
            weekday=appointment_day.weekday(),
            opens_at=time(8),
            closes_at=time(17),
            is_closed=False,
        )
    )
    db_session.commit()

    verification_calls = []

    async def verified(token, ip):
        verification_calls.append((token, ip))

    monkeypatch.setattr(public_booking, "verify_turnstile_token", verified)
    starts_at = datetime.combine(
        appointment_day, time(10), tzinfo=ZoneInfo(business.timezone)
    )
    payload = PublicBookingSubmission(
        customer_name="Alex Customer",
        customer_phone="+265991234567",
        customer_email="alex@example.com",
        service_id=service.id,
        starts_at=starts_at.isoformat(),
        idempotency_key=f"public-{uuid4().hex}",
        turnstile_token="fresh-turnstile-token",
    )
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/public/businesses/test/bookings",
            "headers": [],
            "query_string": b"",
            "client": ("203.0.113.10", 12345),
        }
    )

    first_receipt = asyncio.run(
        submit_public_booking(business.slug, payload, request, db_session)
    )
    retry_receipt = asyncio.run(
        submit_public_booking(business.slug, payload, request, db_session)
    )

    bookings = db_session.scalars(
        select(Booking).where(Booking.business_id == business.id)
    ).all()
    customers = db_session.scalars(
        select(Customer).where(Customer.business_id == business.id)
    ).all()

    assert retry_receipt.booking_reference == first_receipt.booking_reference
    assert retry_receipt.status == first_receipt.status == "held"
    assert len(bookings) == 1
    assert len(customers) == 1
    assert len(verification_calls) == 2
