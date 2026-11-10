import uuid

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db, set_tenant_context
from app.models import Business, Service
from app.modules.bookings.availability import get_availability

router = APIRouter(prefix="/public/businesses", tags=["Public booking"])


class PublicService(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    duration_minutes: int
    price_amount: str
    currency: str


class PublicBusinessProfile(BaseModel):
    name: str
    slug: str
    business_type: str
    timezone: str
    currency: str
    services: list[PublicService]


@router.get("/{slug}", response_model=PublicBusinessProfile)
def get_public_business(slug: str, db: Session = Depends(get_db)):
    business = db.scalar(
        select(Business).where(
            Business.slug == slug,
            Business.status == "active",
            Business.workflow_mode.in_(("bookings", "both")),
        )
    )
    if business is None:
        raise HTTPException(status_code=404, detail="Public booking page not found")

    set_tenant_context(db, business.id)
    services = db.scalars(
        select(Service).where(
            Service.business_id == business.id,
            Service.status == "active",
        ).order_by(Service.name.asc())
    ).all()
    return PublicBusinessProfile(
        name=business.name,
        slug=business.slug,
        business_type=business.business_type,
        timezone=business.timezone,
        currency=business.currency,
        services=[
            PublicService(
                id=service.id,
                name=service.name,
                description=service.description,
                duration_minutes=service.duration_minutes,
                price_amount=str(service.price_amount),
                currency=business.currency,
            )
            for service in services
        ],
    )



@router.get("/{slug}/availability")
def get_public_availability(
    slug: str,
    service_id: uuid.UUID,
    target_date: date = Query(alias="date"),
    slot_interval_minutes: int = Query(default=15, ge=5, le=60),
    db: Session = Depends(get_db),
):
    business = db.scalar(
        select(Business).where(
            Business.slug == slug,
            Business.status == "active",
            Business.workflow_mode.in_(("bookings", "both")),
        )
    )
    if business is None:
        raise HTTPException(status_code=404, detail="Public booking page not found")
    return get_availability(
        business_id=business.id,
        service_id=service_id,
        target_date=target_date,
        employee_id=None,
        slot_interval_minutes=slot_interval_minutes,
        user=None,
        db=db,
    )
