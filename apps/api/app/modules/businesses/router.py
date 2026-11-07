import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_refresh_token
from app.db.session import get_db, set_tenant_context
from app.integrations.email import EmailDeliveryError, send_transactional_email
from app.models import (
    AuditEvent,
    Business,
    BusinessInvitation,
    BusinessMembership,
    User,
)
from app.modules.businesses.authorization import require_membership, require_roles
from app.modules.businesses.schemas import (
    BusinessCreateRequest,
    BusinessResponse,
    InvitationAcceptRequest,
    InvitationCreateRequest,
    InvitationResponse,
    MemberResponse,
    MembershipUpdateRequest,
)
from app.modules.identity.router import get_current_user

router = APIRouter(prefix="/businesses", tags=["Businesses"])
_SLUG_RE = re.compile(r"[^a-z0-9]+")
INVITATION_LIFETIME_HOURS = 72
INVITABLE_ROLES = {"admin", "manager", "staff"}


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _slug_base(name: str) -> str:
    slug = _SLUG_RE.sub("-", name.casefold()).strip("-")
    return slug[:70] or "business"


def _membership_response(business: Business, membership: BusinessMembership) -> BusinessResponse:
    return BusinessResponse(
        id=business.id,
        name=business.name,
        slug=business.slug,
        timezone=business.timezone,
        currency=business.currency,
        status=business.status,
        role=membership.role,
        created_at=business.created_at,
    )


def _audit(
    db: Session, *, business_id: uuid.UUID, actor_id: uuid.UUID,
    action: str, target_type: str, target_id: str, metadata: dict | None = None,
) -> None:
    db.add(AuditEvent(
        business_id=business_id,
        actor_user_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        event_metadata=metadata or {},
    ))


@router.post("", response_model=BusinessResponse, status_code=status.HTTP_201_CREATED)
def create_business(
    payload: BusinessCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BusinessResponse:
    if user.email_verified_at is None:
        raise HTTPException(status_code=403, detail="Verify your email before creating a business")
    business = Business(
        name=payload.name.strip(),
        slug=f"{_slug_base(payload.name)}-{secrets.token_hex(4)}",
    )
    membership = BusinessMembership(user_id=user.id, role="owner", status="active")
    business.memberships.append(membership)
    db.add(business)
    try:
        db.flush()
        set_tenant_context(db, business.id)
        _audit(db, business_id=business.id, actor_id=user.id, action="business.created",
               target_type="business", target_id=str(business.id), metadata={"name": business.name})
        db.commit()
        db.refresh(business)
        db.refresh(membership)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Business could not be created") from None
    return _membership_response(business, membership)


@router.get("", response_model=list[BusinessResponse])
def list_my_businesses(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BusinessResponse]:
    rows = db.execute(
        select(Business, BusinessMembership)
        .join(BusinessMembership, BusinessMembership.business_id == Business.id)
        .where(BusinessMembership.user_id == user.id,
               BusinessMembership.status == "active", Business.status == "active")
        .order_by(Business.name.asc())
    ).all()
    return [_membership_response(business, membership) for business, membership in rows]


@router.get("/{business_id}", response_model=BusinessResponse)
def get_my_business(
    business_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BusinessResponse:
    business, membership = require_membership(business_id, user, db)
    return _membership_response(business, membership)


@router.get("/{business_id}/members", response_model=list[MemberResponse])
def list_members(
    business_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MemberResponse]:
    require_membership(business_id, user, db)
    rows = db.execute(
        select(BusinessMembership, User)
        .join(User, User.id == BusinessMembership.user_id)
        .where(BusinessMembership.business_id == business_id,
               BusinessMembership.status != "suspended")
        .order_by(BusinessMembership.created_at.asc())
    ).all()
    return [
        MemberResponse(membership_id=m.id, user_id=u.id, email=u.email,
                       full_name=u.full_name, role=m.role, status=m.status, created_at=m.created_at)
        for m, u in rows
    ]


@router.post("/{business_id}/invitations", response_model=InvitationResponse, status_code=201)
def create_invitation(
    business_id: uuid.UUID,
    payload: InvitationCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvitationResponse:
    business, actor = require_roles(business_id, {"owner", "admin"}, user, db)
    set_tenant_context(db, business.id)
    role = payload.role.casefold()
    if role not in INVITABLE_ROLES:
        raise HTTPException(status_code=422, detail="Invitation role must be admin, manager or staff")
    if actor.role == "admin" and role == "admin":
        raise HTTPException(status_code=403, detail="Only the owner can invite another administrator")
    email = str(payload.email).strip().casefold()
    existing_user = db.scalar(select(User).where(User.email_normalized == email))
    if existing_user is not None:
        existing_membership = db.scalar(
            select(BusinessMembership).where(
                BusinessMembership.business_id == business_id,
                BusinessMembership.user_id == existing_user.id,
            )
        )
        if existing_membership is not None and existing_membership.status == "active":
            raise HTTPException(status_code=409, detail="This person is already a member")
    now = datetime.now(UTC)
    previous = db.scalars(
        select(BusinessInvitation).where(
            BusinessInvitation.business_id == business_id,
            BusinessInvitation.email_normalized == email,
            BusinessInvitation.accepted_at.is_(None),
            BusinessInvitation.revoked_at.is_(None),
        ).with_for_update()
    ).all()
    for old in previous:
        old.revoked_at = now
    raw_token = secrets.token_urlsafe(48)
    invitation = BusinessInvitation(
        business_id=business_id,
        invited_by_user_id=user.id,
        email_normalized=email,
        role=role,
        token_hash=hash_refresh_token(raw_token),
        expires_at=now + timedelta(hours=INVITATION_LIFETIME_HOURS),
    )
    db.add(invitation)
    try:
        db.flush()
        accept_url = (
            f"{get_settings().frontend_base_url.rstrip('/')}/invitations/accept"
            f"#token={raw_token}"
        )
        send_transactional_email(
            recipient=email,
            subject=f"Invitation to join {business.name} on BookFlow AI",
            text_body=(
                f"You have been invited to join {business.name} as {role}.\n\n"
                f"Accept your invitation: {accept_url}\n\n"
                "Sign in with the invited email address to accept. "
                "This invitation expires in 72 hours and can only be used once."
            ),
        )
        _audit(db, business_id=business_id, actor_id=user.id, action="membership.invitation_created",
               target_type="invitation", target_id=str(invitation.id),
               metadata={"role": role, "email": email})
        db.commit()
        db.refresh(invitation)
    except EmailDeliveryError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Invitation email could not be delivered") from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Invitation could not be created") from None
    return InvitationResponse(id=invitation.id, email=email, role=role,
                              expires_at=invitation.expires_at, status="pending")


@router.post("/invitations/accept", response_model=MemberResponse)
def accept_invitation(
    payload: InvitationAcceptRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemberResponse:
    if user.email_verified_at is None:
        raise HTTPException(status_code=403, detail="Verify your email before accepting an invitation")
    token_hash = hash_refresh_token(payload.token)
    invitation = db.scalar(
        select(BusinessInvitation).where(
            BusinessInvitation.token_hash == token_hash
        ).with_for_update()
    )
    now = datetime.now(UTC)
    if (
        invitation is None or invitation.accepted_at is not None
        or invitation.revoked_at is not None or _as_utc(invitation.expires_at) <= now
        or invitation.email_normalized != user.email_normalized
    ):
        raise HTTPException(status_code=400, detail="Invitation is invalid or expired")
    business = db.get(Business, invitation.business_id)
    if business is None or business.status != "active":
        raise HTTPException(status_code=400, detail="Invitation is invalid or expired")
    set_tenant_context(db, business.id)
    membership = db.scalar(
        select(BusinessMembership).where(
            BusinessMembership.business_id == invitation.business_id,
            BusinessMembership.user_id == user.id,
        ).with_for_update()
    )
    if membership is None:
        membership = BusinessMembership(
            business_id=invitation.business_id, user_id=user.id,
            role=invitation.role, status="active",
        )
        db.add(membership)
    elif membership.status == "active":
        raise HTTPException(status_code=409, detail="You are already a member of this business")
    else:
        membership.role = invitation.role
        membership.status = "active"
    invitation.accepted_at = now
    _audit(db, business_id=business.id, actor_id=user.id, action="membership.invitation_accepted",
           target_type="membership", target_id=str(membership.id),
           metadata={"role": invitation.role})
    try:
        db.commit()
        db.refresh(membership)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Invitation could not be accepted") from None
    return MemberResponse(
        membership_id=membership.id, user_id=user.id, email=user.email,
        full_name=user.full_name, role=membership.role, status=membership.status,
        created_at=membership.created_at,
    )


@router.patch("/{business_id}/members/{membership_id}", response_model=MemberResponse)
def update_member(
    business_id: uuid.UUID,
    membership_id: uuid.UUID,
    payload: MembershipUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemberResponse:
    business, actor = require_roles(business_id, {"owner", "admin"}, user, db)
    set_tenant_context(db, business.id)
    target = db.scalar(
        select(BusinessMembership).where(
            BusinessMembership.id == membership_id,
            BusinessMembership.business_id == business_id,
        ).with_for_update()
    )
    if target is None:
        raise HTTPException(status_code=404, detail="Member not found")
    if target.role == "owner" or target.user_id == user.id:
        raise HTTPException(status_code=403, detail="This membership cannot be changed here")
    if actor.role == "admin" and target.role in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Administrators cannot manage another administrator")
    if payload.role is None and payload.status is None:
        raise HTTPException(status_code=422, detail="Provide a role or status change")
    if payload.role is not None:
        new_role = payload.role.casefold()
        allowed = {"manager", "staff"} if actor.role == "admin" else {"admin", "manager", "staff"}
        if new_role not in allowed:
            raise HTTPException(status_code=403, detail="You cannot assign this role")
        target.role = new_role
    if payload.status is not None:
        if payload.status not in {"active", "suspended"}:
            raise HTTPException(status_code=422, detail="Status must be active or suspended")
        target.status = payload.status
    _audit(db, business_id=business_id, actor_id=user.id, action="membership.updated",
           target_type="membership", target_id=str(target.id),
           metadata={"role": target.role, "status": target.status})
    db.commit()
    member = db.get(User, target.user_id)
    return MemberResponse(
        membership_id=target.id, user_id=target.user_id, email=member.email,
        full_name=member.full_name, role=target.role, status=target.status,
        created_at=target.created_at,
    )
