import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import (
    Business,
    Employee,
    SchedulableResource,
    Service,
    ServiceEmployeeEligibility,
    ServiceResourceRequirement,
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


def test_service_employee_and_resource_catalogue(db_session: Session) -> None:
    business = Business(name="Lilongwe Studio", slug="catalogue-studio")
    db_session.add(business)
    db_session.flush()
    service = Service(
        business_id=business.id,
        name="Haircut",
        duration_minutes=45,
        buffer_before_minutes=5,
        buffer_after_minutes=10,
        price_amount="15000.00",
    )
    employee = Employee(business_id=business.id, display_name="Tadala")
    resource = SchedulableResource(
        business_id=business.id, name="Chair 1", resource_type="chair"
    )
    db_session.add_all([service, employee, resource])
    db_session.flush()
    db_session.add_all([
        ServiceEmployeeEligibility(
            business_id=business.id, service_id=service.id, employee_id=employee.id
        ),
        ServiceResourceRequirement(
            business_id=business.id, service_id=service.id, resource_id=resource.id, quantity=1
        ),
    ])
    db_session.commit()

    assert service.price_amount == 15000
    assert service.duration_minutes == 45
    assert employee.status == "active"
    assert resource.capacity == 1


def test_service_employee_link_cannot_cross_businesses(db_session: Session) -> None:
    first = Business(name="First Studio", slug="first-catalogue-studio")
    second = Business(name="Second Studio", slug="second-catalogue-studio")
    db_session.add_all([first, second])
    db_session.flush()
    service = Service(
        business_id=first.id, name="Massage", duration_minutes=60, price_amount="25000.00"
    )
    employee = Employee(business_id=second.id, display_name="Cross Tenant Employee")
    db_session.add_all([service, employee])
    db_session.flush()

    db_session.add(ServiceEmployeeEligibility(
        business_id=first.id, service_id=service.id, employee_id=employee.id
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_invalid_service_duration_is_rejected(db_session: Session) -> None:
    business = Business(name="Duration Studio", slug="duration-studio")
    db_session.add(business)
    db_session.flush()
    db_session.add(Service(
        business_id=business.id, name="Invalid Service", duration_minutes=0, price_amount="0.00"
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_resource_capacity_must_be_positive(db_session: Session) -> None:
    business = Business(name="Resource Studio", slug="resource-studio")
    db_session.add(business)
    db_session.flush()
    db_session.add(SchedulableResource(
        business_id=business.id, name="Invalid Chair", resource_type="chair", capacity=0
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
