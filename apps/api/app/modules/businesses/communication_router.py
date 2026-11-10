import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db, set_tenant_context
from app.models import AuditEvent, User
from app.models.communication import BusinessCommunicationSettings
from app.modules.businesses.authorization import require_membership, require_roles
from app.modules.businesses.communication_schemas import (
    CommunicationSettingsResponse,
    CommunicationSettingsUpdate,
)
from app.modules.identity.router import get_current_user

router = APIRouter(prefix="/businesses/{business_id}/communication-settings", tags=["Business communication"])


@router.get("", response_model=CommunicationSettingsResponse)
def get_communication_settings(
    business_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommunicationSettingsResponse:
    business, _ = require_membership(business_id, user, db)
    set_tenant_context(db, business.id)
    settings = db.scalar(
        select(BusinessCommunicationSettings).where(
            BusinessCommunicationSettings.business_id == business.id
        )
    )
    if settings is None:
        settings = BusinessCommunicationSettings(business_id=business.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.patch("", response_model=CommunicationSettingsResponse)
def update_communication_settings(
    business_id: uuid.UUID,
    payload: CommunicationSettingsUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommunicationSettingsResponse:
    business, _ = require_roles(business_id, {"owner", "admin"}, user, db)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Provide at least one setting to update")
    set_tenant_context(db, business.id)
    settings = db.scalar(
        select(BusinessCommunicationSettings)
        .where(BusinessCommunicationSettings.business_id == business.id)
        .with_for_update()
    )
    if settings is None:
        settings = BusinessCommunicationSettings(business_id=business.id)
        db.add(settings)
        db.flush()
    for field, value in changes.items():
        setattr(settings, field, value)
    db.add(AuditEvent(
        business_id=business.id,
        actor_user_id=user.id,
        action="business.communication_settings_updated",
        target_type="business_communication_settings",
        target_id=str(settings.id),
        event_metadata={"updated_fields": sorted(changes)},
    ))
    db.commit()
    db.refresh(settings)
    return settings
