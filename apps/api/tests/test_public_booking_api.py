from datetime import date, time
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Business, BusinessWeeklyHours, Service
from app.modules.public_booking.router import get_public_availability, get_public_business


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
