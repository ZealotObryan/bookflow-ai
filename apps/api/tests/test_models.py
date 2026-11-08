import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Business, BusinessMembership, User


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_user_can_belong_to_multiple_businesses(db_session: Session) -> None:
    user = User(
        email="owner@example.com",
        email_normalized="owner@example.com",
        full_name="Business Owner",
    )
    first = Business(name="First Studio", slug="first-studio")
    second = Business(name="Second Studio", slug="second-studio")
    db_session.add_all([user, first, second])
    db_session.flush()

    db_session.add_all(
        [
            BusinessMembership(business_id=first.id, user_id=user.id, role="owner"),
            BusinessMembership(business_id=second.id, user_id=user.id, role="admin"),
        ]
    )
    db_session.commit()

    memberships = db_session.scalars(
        select(BusinessMembership).where(BusinessMembership.user_id == user.id)
    ).all()

    assert len(memberships) == 2
    assert {membership.role for membership in memberships} == {"owner", "admin"}


def test_duplicate_membership_is_rejected(db_session: Session) -> None:
    user = User(
        email="member@example.com",
        email_normalized="member@example.com",
        full_name="Member",
    )
    business = Business(name="Example Studio", slug="example-studio")
    db_session.add_all([user, business])
    db_session.flush()

    db_session.add(
        BusinessMembership(business_id=business.id, user_id=user.id, role="owner")
    )
    db_session.commit()

    db_session.add(
        BusinessMembership(business_id=business.id, user_id=user.id, role="staff")
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_business_defaults_to_malawi_settings(db_session: Session) -> None:
    business = Business(name="Lilongwe Studio", slug="lilongwe-studio")
    db_session.add(business)
    db_session.commit()
    db_session.refresh(business)

    assert business.timezone == "Africa/Blantyre"
    assert business.currency == "MWK"


def test_invalid_membership_role_is_rejected(db_session: Session) -> None:
    user = User(
        email="invalid-role@example.com",
        email_normalized="invalid-role@example.com",
        full_name="Invalid Role",
    )
    business = Business(name="Role Test Studio", slug="role-test-studio")
    db_session.add_all([user, business])
    db_session.flush()

    db_session.add(
        BusinessMembership(business_id=business.id, user_id=user.id, role="superuser")
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_user_id_is_uuid(db_session: Session) -> None:
    user = User(
        email="uuid@example.com",
        email_normalized="uuid@example.com",
        full_name="UUID User",
    )
    db_session.add(user)
    db_session.commit()

    assert isinstance(user.id, uuid.UUID)
