import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.session import get_db, set_tenant_context
from app.models import Business, BusinessWhatsAppSettings, User, WhatsAppEntryLink
from app.modules.businesses.authorization import require_roles
from app.modules.identity.router import get_current_user

router = APIRouter(tags=["WhatsApp entry"])


class WhatsAppEntryLinkResponse(BaseModel):
    id: uuid.UUID
    entry_token: str
    entry_path: str
    expires_at: datetime


class WhatsAppEntryResolution(BaseModel):
    business_id: uuid.UUID
    business_name: str
    greeting: str


@router.post(
    "/businesses/{business_id}/whatsapp/entry-links",
    response_model=WhatsAppEntryLinkResponse,
)
def create_entry_link(
    business_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WhatsAppEntryLinkResponse:
    business, _ = require_roles(business_id, {"owner", "admin"}, user, db)
    set_tenant_context(db, business.id)
    settings = db.scalar(
        select(BusinessWhatsAppSettings).where(
            BusinessWhatsAppSettings.business_id == business.id
        )
    )
    if settings is None or not settings.assistant_enabled:
        raise HTTPException(status_code=409, detail="Enable the BookFlow assistant before creating a link")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(days=90)
    link = WhatsAppEntryLink(
        business_id=business.id,
        token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        expires_at=expires_at,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return WhatsAppEntryLinkResponse(
        id=link.id,
        entry_token=token,
        entry_path=f"/api/v1/whatsapp/entry/{token}",
        expires_at=expires_at,
    )


@router.post("/businesses/{business_id}/whatsapp/entry-links/{link_id}/revoke")
def revoke_entry_link(
    business_id: uuid.UUID,
    link_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    business, _ = require_roles(business_id, {"owner", "admin"}, user, db)
    set_tenant_context(db, business.id)
    link = db.scalar(
        select(WhatsAppEntryLink).where(
            WhatsAppEntryLink.id == link_id,
            WhatsAppEntryLink.business_id == business.id,
        ).with_for_update()
    )
    if link is None:
        raise HTTPException(status_code=404, detail="Entry link not found")
    if link.revoked_at is None:
        link.revoked_at = datetime.now(UTC)
        db.commit()
    return {"status": "revoked"}


@router.get("/whatsapp/entry/{token}", response_model=WhatsAppEntryResolution)
def resolve_entry_link(
    token: str,
    db: Session = Depends(get_db),
) -> WhatsAppEntryResolution:
    if len(token) < 32 or len(token) > 128:
        raise HTTPException(status_code=404, detail="Entry link is invalid or expired")
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now(UTC)
    business_id = db.scalar(
        text("SELECT resolve_whatsapp_entry_business(:token_hash)"),
        {"token_hash": token_hash},
    )
    if business_id is None:
        raise HTTPException(status_code=404, detail="Entry link is invalid or expired")
    set_tenant_context(db, business_id)
    business = db.get(Business, business_id)
    settings = db.scalar(
        select(BusinessWhatsAppSettings).where(
            BusinessWhatsAppSettings.business_id == business_id,
            BusinessWhatsAppSettings.assistant_enabled.is_(True),
        )
    )
    if business is None or settings is None:
        raise HTTPException(status_code=404, detail="Entry link is invalid or expired")
    return WhatsAppEntryResolution(
        business_id=business.id,
        business_name=business.name,
        greeting=settings.greeting,
    )
