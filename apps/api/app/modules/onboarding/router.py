import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db, set_tenant_context
from app.models import BusinessOnboardingProgress, User
from app.modules.businesses.authorization import require_roles
from app.modules.identity.router import get_current_user
from app.modules.onboarding.schemas import (
    OnboardingProgressResponse,
    OnboardingProgressUpdate,
)

router = APIRouter(prefix="/businesses/{business_id}/onboarding", tags=["Onboarding"])


@router.get("", response_model=OnboardingProgressResponse)
def get_onboarding_progress(
    business_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnboardingProgressResponse:
    business, _ = require_roles(business_id, {"owner", "admin", "manager"}, user, db)
    set_tenant_context(db, business.id)
    progress = db.scalar(
        select(BusinessOnboardingProgress).where(
            BusinessOnboardingProgress.business_id == business.id
        )
    )
    if progress is None:
        progress = BusinessOnboardingProgress(business_id=business.id)
        db.add(progress)
        db.commit()
        db.refresh(progress)
    return progress


@router.put("", response_model=OnboardingProgressResponse)
def update_onboarding_progress(
    business_id: uuid.UUID,
    payload: OnboardingProgressUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnboardingProgressResponse:
    business, _ = require_roles(business_id, {"owner", "admin"}, user, db)
    set_tenant_context(db, business.id)
    progress = db.scalar(
        select(BusinessOnboardingProgress)
        .where(BusinessOnboardingProgress.business_id == business.id)
        .with_for_update()
    )
    if progress is None:
        progress = BusinessOnboardingProgress(business_id=business.id)
        db.add(progress)
    progress.completed_steps = payload.completed_steps
    progress.dismissed = payload.dismissed
    db.commit()
    db.refresh(progress)
    return progress
