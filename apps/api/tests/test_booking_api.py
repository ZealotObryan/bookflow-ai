from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import (
    Booking,
    BookingSegmentResource,
    Business,
    BusinessMembership,
    BusinessWeeklyHours,
    Customer,
    Employee,
    EmployeeWeeklyHours,
    SchedulableResource,
    Service,
    ServiceResourceRequirement,
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
        target_date=date(2026, 11, 16),
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
        target_date=date(2026, 11, 16),
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
        target_date=date(2026, 11, 16),
        employee_id=employee.id,
        slot_interval_minutes=30,
        user=user,
        db=db_session,
    )

    assert result["slots"]
    assert all(slot["employee_id"] == employee.id for slot in result["slots"])


def test_resource_capacity_is_reserved_with_booking(db_session, booking_context):
    business, user, customer, employee, service = booking_context
    resource = SchedulableResource(business_id=business.id, name="Treatment bed", resource_type="bed", capacity=1)
    db_session.add(resource)
    db_session.flush()
    db_session.add(ServiceResourceRequirement(
        business_id=business.id, service_id=service.id, resource_id=resource.id, quantity=1
    ))
    db_session.commit()
    result = create_booking(
        business_id=business.id,
        payload=request_for(customer, service, employee, datetime(2026, 11, 9, 8, tzinfo=UTC), "resource-reservation-01"),
        user=user, db=db_session,
    )
    allocation = db_session.query(BookingSegmentResource).filter_by(
        business_id=business.id, resource_id=resource.id
    ).one()
    assert result["status"] == "held"
    assert allocation.quantity == 1


def test_resource_capacity_prevents_overlapping_booking(db_session, booking_context):
    business, user, customer, employee, service = booking_context
    service.buffer_before_minutes = 0
    service.buffer_after_minutes = 0
    service.requires_employee = False
    resource = SchedulableResource(business_id=business.id, name="Consultation room", resource_type="room", capacity=1)
    db_session.add(resource)
    db_session.flush()
    db_session.add(ServiceResourceRequirement(
        business_id=business.id, service_id=service.id, resource_id=resource.id, quantity=1
    ))
    db_session.commit()
    start = datetime(2026, 11, 9, 8, tzinfo=UTC)
    first_payload = BookingInput(
        customer_id=customer.id,
        idempotency_key="resource-first-01",
        segments=[SegmentInput(service_id=service.id, employee_id=None, starts_at=start)],
    )
    second_payload = BookingInput(
        customer_id=customer.id,
        idempotency_key="resource-second-01",
        segments=[SegmentInput(service_id=service.id, employee_id=None, starts_at=start + timedelta(minutes=5))],
    )
    create_booking(business_id=business.id, payload=first_payload, user=user, db=db_session)
    with pytest.raises(HTTPException) as error:
        create_booking(business_id=business.id, payload=second_payload, user=user, db=db_session)
    assert error.value.status_code == 409


def test_availability_excludes_slots_when_required_resource_is_full(db_session, booking_context):
    business, user, customer, employee, service = booking_context
    service.buffer_before_minutes = 0
    service.buffer_after_minutes = 0
    resource = SchedulableResource(
        business_id=business.id, name="One treatment bed", resource_type="bed", capacity=1
    )
    db_session.add(resource)
    db_session.flush()
    db_session.add(ServiceResourceRequirement(
        business_id=business.id, service_id=service.id, resource_id=resource.id, quantity=1
    ))
    db_session.commit()
    booked_start = datetime(2026, 11, 9, 8, tzinfo=UTC)
    create_booking(
        business_id=business.id,
        payload=request_for(customer, service, employee, booked_start, "availability-resource-full"),
        user=user,
        db=db_session,
    )
    result = get_availability(
        business_id=business.id,
        service_id=service.id,
        target_date=date(2026, 11, 16),
        employee_id=employee.id,
        slot_interval_minutes=30,
        user=user,
        db=db_session,
    )
    assert all(slot["starts_at"] != booked_start for slot in result["slots"])



def test_booking_can_be_confirmed_and_hold_is_cleared(db_session, booking_context):
    from app.modules.bookings.router import confirm_booking

    business, user, customer, employee, service = booking_context
    created = create_booking(
        business_id=business.id,
        payload=request_for(customer, service, employee, datetime(2026, 11, 9, 8, tzinfo=UTC)),
        user=user, db=db_session,
    )
    confirmed = confirm_booking(business.id, created["id"], user, db_session)
    assert confirmed["status"] == "confirmed"
    assert confirmed["hold_expires_at"] is None
    assert db_session.query(BookingSegmentResource).count() == 0


def test_confirmed_booking_can_be_cancelled_and_releases_reservations(db_session, booking_context):
    from app.models import BookingSegment
    from app.modules.bookings.router import cancel_booking, confirm_booking

    business, user, customer, employee, service = booking_context
    resource = SchedulableResource(
        business_id=business.id, name="Room", resource_type="room", capacity=1
    )
    db_session.add(resource)
    db_session.flush()
    db_session.add(ServiceResourceRequirement(
        business_id=business.id, service_id=service.id, resource_id=resource.id, quantity=1
    ))
    db_session.commit()
    created = create_booking(
        business_id=business.id,
        payload=request_for(customer, service, employee, datetime(2026, 11, 9, 8, tzinfo=UTC)),
        user=user, db=db_session,
    )
    confirm_booking(business.id, created["id"], user, db_session)
    cancelled = cancel_booking(business.id, created["id"], user, db_session)
    assert cancelled["status"] == "cancelled"
    segment = db_session.query(BookingSegment).filter_by(booking_id=created["id"]).one()
    assert segment.status == "cancelled"


def test_expired_booking_hold_cannot_be_confirmed(db_session, booking_context):
    from app.modules.bookings.router import confirm_booking

    business, user, customer, employee, service = booking_context
    created = create_booking(
        business_id=business.id,
        payload=request_for(customer, service, employee, datetime(2026, 11, 9, 8, tzinfo=UTC)),
        user=user, db=db_session,
    )
    booking = db_session.get(__import__("app.models", fromlist=["Booking"]).Booking, created["id"])
    booking.hold_expires_at = datetime(2020, 1, 1, tzinfo=UTC)
    db_session.commit()
    with pytest.raises(HTTPException) as error:
        confirm_booking(business.id, created["id"], user, db_session)
    assert error.value.status_code == 409
    assert booking.status == "expired"



def test_scheduled_hold_cleanup_expires_booking_and_segments(db_session, booking_context):
    from app.core.maintenance import expire_booking_holds
    from app.models import BookingSegment

    business, user, customer, employee, service = booking_context
    created = create_booking(
        business_id=business.id,
        payload=request_for(customer, service, employee, datetime(2026, 11, 9, 8, tzinfo=UTC)),
        user=user, db=db_session,
    )
    booking = db_session.get(Booking, created["id"])
    booking.hold_expires_at = datetime(2020, 1, 1, tzinfo=UTC)
    db_session.commit()

    result = expire_booking_holds(db_session)
    db_session.refresh(booking)
    segment = db_session.query(BookingSegment).filter_by(booking_id=booking.id).one()

    assert result["expired_bookings"] == 1
    assert booking.status == "expired"
    assert segment.status == "cancelled"


def test_booking_list_is_scoped_to_authenticated_business(db_session, booking_context):
    from app.modules.bookings.router import list_bookings

    business, user, customer, employee, service = booking_context
    created = create_booking(
        business_id=business.id,
        payload=request_for(
            customer, service, employee, datetime(2026, 11, 9, 8, tzinfo=UTC),
            "booking-list-test-0001",
        ),
        user=user,
        db=db_session,
    )

    rows = list_bookings(
        business_id=business.id,
        limit=100,
        user=user,
        db=db_session,
    )

    assert len(rows) == 1
    assert rows[0]["id"] == created["id"]
    assert rows[0]["customer_id"] == customer.id
    assert rows[0]["customer_name"] == customer.display_name
    assert rows[0]["segments"][0]["service_name"] == service.name


def test_scheduling_options_only_returns_active_business_resources(db_session, booking_context):
    from app.models import SchedulableResource
    from app.modules.records.router import list_scheduling_options

    business, user, _customer, employee, _service = booking_context
    inactive_employee = Employee(
        business_id=business.id, display_name="Inactive teammate", status="inactive"
    )
    resource = SchedulableResource(
        business_id=business.id, name="Studio room", resource_type="room", capacity=1
    )
    db_session.add_all([inactive_employee, resource])
    db_session.commit()

    result = list_scheduling_options(
        business_id=business.id,
        user=user,
        db=db_session,
    )

    assert result["employees"] == [{"id": employee.id, "display_name": employee.display_name}]
    assert result["resources"] == [{
        "id": resource.id,
        "name": resource.name,
        "resource_type": resource.resource_type,
        "capacity": resource.capacity,
    }]
