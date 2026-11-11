import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db, set_tenant_context
from app.models import AuditEvent, Booking, Payment, Project, User
from app.modules.businesses.authorization import require_roles
from app.modules.identity.router import get_current_user
from app.modules.payments.schemas import ManualPaymentCreate, PaymentResponse

router = APIRouter(prefix="/businesses/{business_id}/payments", tags=["Payments"])


@router.get("", response_model=list[PaymentResponse])
def list_payments(
    business_id: uuid.UUID,
    payment_status: Literal["pending", "succeeded", "failed", "refunded"] | None = Query(default=None, alias="status"),
    booking_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=250),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Payment]:
    business, _ = require_roles(business_id, {"owner", "admin", "manager", "staff"}, user, db)
    set_tenant_context(db, business.id)
    query = select(Payment).where(Payment.business_id == business.id)
    if payment_status is not None:
        query = query.where(Payment.status == payment_status)
    if booking_id is not None:
        query = query.where(Payment.booking_id == booking_id)
    if project_id is not None:
        query = query.where(Payment.project_id == project_id)
    return list(db.scalars(query.order_by(Payment.created_at.desc()).limit(limit)).all())


@router.post("/manual", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def record_manual_payment(
    business_id: uuid.UUID,
    payload: ManualPaymentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Payment:
    business, _ = require_roles(business_id, {"owner", "admin", "manager", "staff"}, user, db)
    set_tenant_context(db, business.id)

    if payload.booking_id is not None:
        target = db.scalar(select(Booking).where(
            Booking.business_id == business.id, Booking.id == payload.booking_id
        ))
        if target is None:
            raise HTTPException(status_code=404, detail="Booking not found")
        target_type = "booking"
        target_id = target.id
    else:
        target = db.scalar(select(Project).where(
            Project.business_id == business.id, Project.id == payload.project_id
        ))
        if target is None:
            raise HTTPException(status_code=404, detail="Project not found")
        target_type = "project"
        target_id = target.id

    payment = Payment(
        business_id=business.id,
        booking_id=payload.booking_id,
        project_id=payload.project_id,
        amount=payload.amount,
        currency=business.currency,
        status="succeeded",
        provider="manual",
        payment_method=payload.payment_method,
        recorded_by=user.id,
        note=payload.note.strip() if payload.note else None,
    )
    db.add(payment)
    db.flush()
    db.add(AuditEvent(
        business_id=business.id,
        actor_user_id=user.id,
        action="payment.manual_recorded",
        target_type=target_type,
        target_id=str(target_id),
        event_metadata={
            "payment_id": str(payment.id),
            "amount": str(payment.amount),
            "currency": payment.currency,
            "payment_method": payment.payment_method,
            "verification": "manual_record_only",
        },
    ))
    db.commit()
    db.refresh(payment)
    return payment
