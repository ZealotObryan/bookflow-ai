import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db, set_tenant_context
from app.models import AuditEvent, BusinessWhatsAppSettings, User
from app.modules.businesses.authorization import require_roles
from app.modules.identity.router import get_current_user
from app.modules.whatsapp.schemas import WhatsAppSettingsResponse, WhatsAppSettingsUpdate

router = APIRouter(prefix="/businesses/{business_id}/whatsapp/settings", tags=["WhatsApp"])


@router.get("", response_model=WhatsAppSettingsResponse)
def get_whatsapp_settings(
    business_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WhatsAppSettingsResponse:
    business, _ = require_roles(business_id, {"owner", "admin", "manager"}, user, db)
    set_tenant_context(db, business.id)
    settings = db.scalar(select(BusinessWhatsAppSettings).where(
        BusinessWhatsAppSettings.business_id == business.id
    ))
    if settings is None:
        settings = BusinessWhatsAppSettings(business_id=business.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.put("", response_model=WhatsAppSettingsResponse)
def update_whatsapp_settings(
    business_id: uuid.UUID,
    payload: WhatsAppSettingsUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WhatsAppSettingsResponse:
    business, _ = require_roles(business_id, {"owner", "admin"}, user, db)
    set_tenant_context(db, business.id)
    settings = db.scalar(select(BusinessWhatsAppSettings).where(
        BusinessWhatsAppSettings.business_id == business.id
    ).with_for_update())
    if settings is None:
        settings = BusinessWhatsAppSettings(business_id=business.id)
        db.add(settings)
    for field, value in payload.model_dump().items():
        setattr(settings, field, value)
    db.add(AuditEvent(
        business_id=business.id,
        actor_user_id=user.id,
        action="whatsapp.settings_updated",
        target_type="whatsapp_settings",
        target_id=str(settings.id),
        event_metadata={
            "assistant_enabled": settings.assistant_enabled,
            "booking_policy": settings.booking_policy,
            "business_number_configured": bool(settings.business_whatsapp_number),
        },
    ))
    db.commit()
    db.refresh(settings)
    return settings
