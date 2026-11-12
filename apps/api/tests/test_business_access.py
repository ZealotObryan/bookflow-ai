from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import AuditEvent, Business, BusinessMembership, User
from app.modules.businesses.router import create_business, get_my_business, list_my_businesses
from app.modules.businesses.schemas import BusinessCreateRequest


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def make_user(*, verified: bool = True) -> User:
    return User(
        email=f"{uuid4()}@example.com",
        email_normalized=f"{uuid4()}@example.com",
        full_name="Test Owner",
        email_verified_at=datetime.now(UTC) if verified else None,
    )


def test_create_business_creates_owner_and_audit_atomically(db_session: Session) -> None:
    user = make_user()
    db_session.add(user)
    db_session.commit()

    response = create_business(BusinessCreateRequest(name="My Studio"), user, db_session)

    membership = db_session.scalar(
        select(BusinessMembership).where(BusinessMembership.business_id == response.id)
    )
    audit = db_session.scalar(
        select(AuditEvent).where(AuditEvent.business_id == response.id)
    )
    assert response.role == "owner"
    assert membership is not None
    assert membership.user_id == user.id
    assert membership.status == "active"
    assert audit is not None
    assert audit.actor_user_id == user.id
    assert audit.action == "business.created"


def test_unverified_user_cannot_create_business(db_session: Session) -> None:
    user = make_user(verified=False)
    db_session.add(user)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        create_business(BusinessCreateRequest(name="Blocked Studio"), user, db_session)

    assert exc.value.status_code == 403
    assert db_session.scalar(select(Business)) is None


def test_business_lookup_hides_other_tenants(db_session: Session) -> None:
    owner = make_user()
    outsider = make_user()
    business = Business(name="Private Studio", slug="private-studio")
    db_session.add_all([owner, outsider, business])
    db_session.flush()
    db_session.add(BusinessMembership(business_id=business.id, user_id=owner.id, role="owner"))
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        get_my_business(business.id, outsider, db_session)

    assert exc.value.status_code == 404


def test_business_list_only_returns_active_memberships(db_session: Session) -> None:
    user = make_user()
    active = Business(name="Active Studio", slug="active-studio")
    suspended = Business(name="Suspended Studio", slug="suspended-studio")
    db_session.add_all([user, active, suspended])
    db_session.flush()
    db_session.add_all([
        BusinessMembership(business_id=active.id, user_id=user.id, role="owner", status="active"),
        BusinessMembership(business_id=suspended.id, user_id=user.id, role="staff", status="suspended"),
    ])
    db_session.commit()

    results = list_my_businesses(user, db_session)

    assert [item.id for item in results] == [active.id]
