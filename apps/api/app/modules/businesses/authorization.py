import uuid

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Business, BusinessMembership, User
from app.modules.identity.router import get_current_user

ROLES = {"owner", "admin", "manager", "staff"}
ACTIVE_STATUSES = {"active", "suspended", "closed"}


def require_membership(
    business_id: uuid.UUID,
    user: User,
    db: Session,
) -> tuple[Business, BusinessMembership]:
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
    return row


def require_roles(
    business_id: uuid.UUID,
    allowed_roles: set[str],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> tuple[Business, BusinessMembership]:
    business, membership = require_membership(business_id, user, db)
    if membership.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="You do not have permission to perform this action")
    return business, membership
