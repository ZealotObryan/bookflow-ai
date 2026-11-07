import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import (
    Booking,
    BookingSegment,
    Business,
    Customer,
    Employee,
    Service,
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


def test_booking_segments_are_tenant_scoped(db_session: Session) -> None:
    business = Business(name="Booking Studio", slug="booking-studio")
    db_session.add(business)
    db_session.flush()
    customer = Customer(business_id=business.id, display_name="Amina")
    employee = Employee(business_id=business.id, display_name="Thoko")
    service = Service(
        business_id=business.id, name="Consultation", duration_minutes=30, price_amount="5000.00"
    )
    db_session.add_all([customer, employee, service])
    db_session.flush()
    booking = Booking(
        business_id=business.id, customer_id=customer.id, status="held",
        starts_at="2026-11-10T08:00:00+00:00", ends_at="2026-11-10T08:30:00+00:00",
        total_amount="5000.00", currency="MWK", idempotency_key="test-booking-1",
    )
    db_session.add(booking)
    db_session.flush()
    segment = BookingSegment(
        business_id=business.id, booking_id=booking.id, service_id=service.id,
        employee_id=employee.id, sequence_number=1,
        starts_at="2026-11-10T08:00:00+00:00", ends_at="2026-11-10T08:30:00+00:00",
        service_name_snapshot=service.name, duration_minutes_snapshot=service.duration_minutes,
        price_amount_snapshot=service.price_amount,
    )
    db_session.add(segment)
    db_session.commit()

    assert booking.status == "held"
    assert segment.service_name_snapshot == "Consultation"


def test_booking_cannot_reference_another_business_customer(db_session: Session) -> None:
    first = Business(name="First Booking Studio", slug="first-booking-studio")
    second = Business(name="Second Booking Studio", slug="second-booking-studio")
    db_session.add_all([first, second])
    db_session.flush()
    customer = Customer(business_id=second.id, display_name="Customer")
    db_session.add(customer)
    db_session.flush()
    booking = Booking(
        business_id=first.id, customer_id=customer.id, status="held",
        starts_at="2026-11-10T08:00:00+00:00", ends_at="2026-11-10T08:30:00+00:00",
        total_amount="0.00", currency="MWK",
    )
    db_session.add(booking)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_booking_segment_cannot_reference_cross_business_service(db_session: Session) -> None:
    first = Business(name="First Segment Studio", slug="first-segment-studio")
    second = Business(name="Second Segment Studio", slug="second-segment-studio")
    db_session.add_all([first, second])
    db_session.flush()
    customer = Customer(business_id=first.id, display_name="Customer")
    service = Service(
        business_id=second.id, name="Other Service", duration_minutes=30, price_amount="0.00"
    )
    db_session.add_all([customer, service])
    db_session.flush()
    booking = Booking(
        business_id=first.id, customer_id=customer.id, status="held",
        starts_at="2026-11-10T08:00:00+00:00", ends_at="2026-11-10T08:30:00+00:00",
        total_amount="0.00", currency="MWK",
    )
    db_session.add(booking)
    db_session.flush()
    segment = BookingSegment(
        business_id=first.id, booking_id=booking.id, service_id=service.id,
        employee_id=None, sequence_number=1,
        starts_at="2026-11-10T08:00:00+00:00", ends_at="2026-11-10T08:30:00+00:00",
        service_name_snapshot=service.name, duration_minutes_snapshot=30,
        price_amount_snapshot="0.00",
    )
    db_session.add(segment)
    with pytest.raises(IntegrityError):
        db_session.commit()
