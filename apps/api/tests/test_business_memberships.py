from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.security import hash_refresh_token
from app.db.base import Base
from app.models import AuditEvent, Business, BusinessInvitation, BusinessMembership, User
from app.modules.businesses.router import accept_invitation, create_invitation, update_member
from app.modules.businesses.schemas import (
    InvitationAcceptRequest,
    InvitationCreateRequest,
    MembershipUpdateRequest,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def make_user(email: str, verified: bool = True) -> User:
    return User(
        email=email, email_normalized=email.casefold(), full_name=email.split("@")[0],
        email_verified_at=datetime.now(UTC) if verified else None,
    )


def make_business(db: Session, owner: User) -> Business:
    business = Business(name="Access Studio", slug=f"access-{uuid4().hex[:8]}")
    db.add(business)
    db.flush()
    db.add(BusinessMembership(
        business_id=business.id, user_id=owner.id, role="owner", status="active"
    ))
    db.commit()
    return business


def test_owner_can_invite_staff_and_token_is_not_stored_plaintext(db_session, monkeypatch) -> None:
    owner = make_user("owner@example.com")
    db_session.add(owner)
    db_session.commit()
    business = make_business(db_session, owner)
    delivered = {}
    monkeypatch.setattr(
        "app.modules.businesses.router.send_transactional_email",
        lambda **kwargs: delivered.update(kwargs),
    )

    response = create_invitation(
        business.id, InvitationCreateRequest(email="staff@example.com", role="staff"),
        owner, db_session,
    )
    invitation = db_session.scalar(select(BusinessInvitation))
    assert response.status == "pending"
    assert invitation is not None
    raw_token = delivered["text_body"].split("token=", 1)[1].split()[0]
    assert invitation.token_hash != raw_token
    assert (invitation.expires_at.replace(tzinfo=UTC) if invitation.expires_at.tzinfo is None else invitation.expires_at) > datetime.now(UTC)


def test_admin_cannot_invite_another_admin(db_session, monkeypatch) -> None:
    admin = make_user("admin@example.com")
    db_session.add(admin)
    db_session.commit()
    business = Business(name="Admin Studio", slug="admin-studio")
    db_session.add(business)
    db_session.flush()
    db_session.add(BusinessMembership(
        business_id=business.id, user_id=admin.id, role="admin", status="active"
    ))
    db_session.commit()
    monkeypatch.setattr("app.modules.businesses.router.send_transactional_email", lambda **kwargs: None)

    with pytest.raises(HTTPException) as exc:
        create_invitation(
            business.id, InvitationCreateRequest(email="other@example.com", role="admin"),
            admin, db_session,
        )
    assert exc.value.status_code == 403


def test_invitation_requires_matching_verified_email_and_is_single_use(db_session, monkeypatch) -> None:
    owner = make_user("owner@example.com")
    invitee = make_user("staff@example.com")
    wrong_user = make_user("wrong@example.com")
    db_session.add_all([owner, invitee, wrong_user])
    db_session.commit()
    business = make_business(db_session, owner)
    delivered = {}
    monkeypatch.setattr(
        "app.modules.businesses.router.send_transactional_email",
        lambda **kwargs: delivered.update(kwargs),
    )
    create_invitation(
        business.id, InvitationCreateRequest(email="staff@example.com", role="staff"),
        owner, db_session,
    )
    raw_token = delivered["text_body"].split("token=", 1)[1].split()[0]

    with pytest.raises(HTTPException) as wrong:
        accept_invitation(InvitationAcceptRequest(token=raw_token), wrong_user, db_session)
    assert wrong.value.status_code == 400

    accepted = accept_invitation(InvitationAcceptRequest(token=raw_token), invitee, db_session)
    assert accepted.role == "staff"
    with pytest.raises(HTTPException) as reused:
        accept_invitation(InvitationAcceptRequest(token=raw_token), invitee, db_session)
    assert reused.value.status_code == 400


def test_expired_invitation_cannot_be_accepted(db_session) -> None:
    owner = make_user("owner2@example.com")
    invitee = make_user("invitee2@example.com")
    db_session.add_all([owner, invitee])
    db_session.commit()
    business = make_business(db_session, owner)
    invitation = BusinessInvitation(
        business_id=business.id, invited_by_user_id=owner.id,
        email_normalized=invitee.email_normalized, role="staff",
        token_hash=hash_refresh_token("expired-invitation-token-value-1234567890"),
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db_session.add(invitation)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        accept_invitation(
            InvitationAcceptRequest(token="expired-invitation-token-value-1234567890"), invitee, db_session
        )
    assert exc.value.status_code == 400


def test_admin_cannot_promote_staff_or_suspend_owner(db_session) -> None:
    admin = make_user("admin2@example.com")
    staff = make_user("staff2@example.com")
    owner = make_user("owner2b@example.com")
    db_session.add_all([admin, staff, owner])
    db_session.commit()
    business = Business(name="Role Studio", slug="role-studio")
    db_session.add(business)
    db_session.flush()
    admin_member = BusinessMembership(
        business_id=business.id, user_id=admin.id, role="admin", status="active"
    )
    staff_member = BusinessMembership(
        business_id=business.id, user_id=staff.id, role="staff", status="active"
    )
    owner_member = BusinessMembership(
        business_id=business.id, user_id=owner.id, role="owner", status="active"
    )
    db_session.add_all([admin_member, staff_member, owner_member])
    db_session.commit()

    with pytest.raises(HTTPException) as promotion:
        update_member(
            business.id, staff_member.id, MembershipUpdateRequest(role="admin"),
            admin, db_session,
        )
    assert promotion.value.status_code == 403

    with pytest.raises(HTTPException) as owner_change:
        update_member(
            business.id, owner_member.id, MembershipUpdateRequest(status="suspended"),
            admin, db_session,
        )
    assert owner_change.value.status_code == 403


def test_membership_update_is_audited(db_session) -> None:
    owner = make_user("owner3@example.com")
    staff = make_user("staff3@example.com")
    db_session.add_all([owner, staff])
    db_session.commit()
    business = Business(name="Audit Studio", slug="audit-studio")
    db_session.add(business)
    db_session.flush()
    owner_member = BusinessMembership(
        business_id=business.id, user_id=owner.id, role="owner", status="active"
    )
    staff_member = BusinessMembership(
        business_id=business.id, user_id=staff.id, role="staff", status="active"
    )
    db_session.add_all([owner_member, staff_member])
    db_session.commit()

    result = update_member(
        business.id, staff_member.id, MembershipUpdateRequest(status="suspended"),
        owner, db_session,
    )
    audit = db_session.scalar(select(AuditEvent).where(AuditEvent.action == "membership.updated"))
    assert result.status == "suspended"
    assert audit is not None
    assert audit.actor_user_id == owner.id
