import re
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import AuditEvent, Business, BusinessMembership, User
from app.modules.businesses.schemas import BusinessCreateRequest, BusinessResponse
from app.modules.identity.router import get_current_user

router = APIRouter(prefix="/businesses", tags=["Businesses"])
_SLUG_RE = re.compile(r"[^a-z0-9]+")


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
        db.add(
            AuditEvent(
                business_id=business.id,
                actor_user_id=user.id,
                action="business.created",
                target_type="business",
                target_id=str(business.id),
                event_metadata={"name": business.name},
            )
        )
        db.commit()
        db.refresh(business)
        db.refresh(membership)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="We could not create this business. Please try again.",
        ) from None
    return _membership_response(business, membership)


@router.get("", response_model=list[BusinessResponse])
def list_my_businesses(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BusinessResponse]:
    rows = db.execute(
        select(Business, BusinessMembership)
        .join(BusinessMembership, BusinessMembership.business_id == Business.id)
        .where(
            BusinessMembership.user_id == user.id,
            BusinessMembership.status == "active",
            Business.status == "active",
        )
        .order_by(Business.name.asc())
    ).all()
    return [_membership_response(business, membership) for business, membership in rows]


@router.get("/{business_id}", response_model=BusinessResponse)
def get_my_business(
    business_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BusinessResponse:
    row = db.execute(
        select(Business, BusinessMembership)
        .join(BusinessMembership, BusinessMembership.business_id == Business.id)
        .where(
            Business.id == business_id,
            BusinessMembership.user_id == user.id,
            BusinessMembership.status == "active",
            Business.status == "active",
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Business not found")
    return _membership_response(*row)
