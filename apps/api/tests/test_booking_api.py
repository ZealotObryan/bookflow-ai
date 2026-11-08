from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import (
    Business,
    BusinessMembership,
    BusinessWeeklyHours,
    Customer,
    Employee,
    EmployeeWeeklyHours,
    Service,
    User,
)
from app.modules.bookings.availability import get_availability
from app.modules.bookings.router import BookingInput, SegmentInput, create_booking


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


@pytest.fixture()
def booking_context(db_session: Session, monkeypatch):
    from app.modules.bookings import router as bookings_router

    business = Business(name="Test Studio", slug=f"test-studio-{uuid4().hex[:8]}")
    user = User(
        email=f"{uuid4().hex}@example.com",
        email_normalized=f"{uuid4().hex}@example.com",
        full_name="Test Owner",
        password_hash="not-used",
    )
    db_session.add_all([business, user])
    db_session.flush()
    membership = BusinessMembership(
        business_id=business.id, user_id=user.id, role="owner", status="active"
    )
    customer = Customer(business_id=business.id, display_name="Amina")
    employee = Employee(business_id=business.id, display_name="Thoko")
    service = Service(
        business_id=business.id,
        name="Consultation",
        duration_minutes=30,
        buffer_before_minutes=10,
        buffer_after_minutes=10,
        price_amount=Decimal("5000.00"),
    )
    db_session.add_all([membership, customer, employee, service])
    db_session.flush()
    db_session.add_all([
        BusinessWeeklyHours(
            business_id=business.id, weekday=0, opens_at=time(8), closes_at=time(17), is_closed=False
        ),
        EmployeeWeeklyHours(
            business_id=business.id, employee_id=employee.id, weekday=0,
            starts_at=time(8), ends_at=time(17), is_unavailable=False,
        ),
    ])
    db_session.commit()
    monkeypatch.setattr(
        bookings_router,
        "require_membership",
        lambda business_id, user, db: (business, membership),
    )
    return business, user, customer, employee, service


def request_for(customer, service, employee, starts_at, key="idempotency-0001"):
    return BookingInput(
        customer_id=customer.id,
        idempotency_key=key,
        segments=[
            SegmentInput(service_id=service.id, employee_id=employee.id, starts_at=starts_at)
        ],
    )


def test_booking_creation_holds_slot_and_includes_buffers(db_session, booking_context):
    business, user, customer, employee, service = booking_context
    start = datetime(2026, 11, 9, 8, tzinfo=UTC)

    result = create_booking(
        business_id=business.id,
        payload=request_for(customer, service, employee, start),
        user=user,
        db=db_session,
    )

    assert result["status"] == "held"
    assert result["total_amount"] == Decimal("5000.00")
    segment = result["segments"][0]
    assert segment["ends_at"].replace(tzinfo=UTC) == start + timedelta(minutes=30)
    assert segment["reserved_starts_at"].replace(tzinfo=UTC) == start - timedelta(minutes=10)
    assert segment["reserved_ends_at"].replace(tzinfo=UTC) == start + timedelta(minutes=40)


def test_booking_idempotency_prevents_duplicate_records(db_session, booking_context):
    business, user, customer, employee, service = booking_context
    start = datetime(2026, 11, 9, 8, tzinfo=UTC)
    payload = request_for(customer, service, employee, start)

    first = create_booking(business_id=business.id, payload=payload, user=user, db=db_session)
    second = create_booking(business_id=business.id, payload=payload, user=user, db=db_session)

    assert first["id"] == second["id"]


def test_overlapping_employee_reservation_is_rejected(db_session, booking_context):
    business, user, customer, employee, service = booking_context
    first_start = datetime(2026, 11, 9, 8, tzinfo=UTC)
    create_booking(
        business_id=business.id,
        payload=request_for(customer, service, employee, first_start, "idempotency-first"),
        user=user,
        db=db_session,
    )

    with pytest.raises(HTTPException) as error:
        create_booking(
            business_id=business.id,
            payload=request_for(
                customer, service, employee, first_start + timedelta(minutes=35), "idempotency-second"
            ),
            user=user,
            db=db_session,
        )
    assert error.value.status_code == 409


def test_booking_outside_business_hours_is_rejected(db_session, booking_context):
    business, user, customer, employee, service = booking_context
    with pytest.raises(HTTPException) as error:
        create_booking(
            business_id=business.id,
            payload=request_for(
                customer, service, employee, datetime(2026, 11, 9, 18, tzinfo=UTC)
            ),
            user=user,
            db=db_session,
        )
    assert error.value.status_code == 409



def test_availability_returns_only_valid_employee_slots(db_session, booking_context):
    business, user, _customer, employee, service = booking_context

    result = get_availability(
        business_id=business.id,
        service_id=service.id,
        target_date=date(2026, 11, 9),
        employee_id=None,
        slot_interval_minutes=30,
        user=user,
        db=db_session,
    )

    assert result["timezone"] == business.timezone
    assert result["slots"]
    assert all(slot["employee_id"] == employee.id for slot in result["slots"])
    assert all(slot["starts_at"] < slot["ends_at"] for slot in result["slots"])


def test_availability_excludes_existing_employee_hold(db_session, booking_context):
    business, user, customer, employee, service = booking_context
    booked_start = datetime(2026, 11, 9, 6, 30, tzinfo=UTC)
    create_booking(
        business_id=business.id,
        payload=request_for(customer, service, employee, booked_start, "availability-hold-01"),
        user=user,
        db=db_session,
    )

    result = get_availability(
        business_id=business.id,
        service_id=service.id,
        target_date=date(2026, 11, 9),
        employee_id=employee.id,
        slot_interval_minutes=30,
        user=user,
        db=db_session,
    )

    assert all(slot["starts_at"] != booked_start for slot in result["slots"])



def test_optional_employee_service_respects_requested_employee(db_session, booking_context):
    business, user, _customer, employee, service = booking_context
    service.requires_employee = False
    db_session.commit()

    result = get_availability(
        business_id=business.id,
        service_id=service.id,
        target_date=date(2026, 11, 9),
        employee_id=employee.id,
        slot_interval_minutes=30,
        user=user,
        db=db_session,
    )

    assert result["slots"]
    assert all(slot["employee_id"] == employee.id for slot in result["slots"])
