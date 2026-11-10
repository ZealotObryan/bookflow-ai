import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db, set_tenant_context
from app.models import (
    AuditEvent,
    Booking,
    BookingSegment,
    BookingSegmentResource,
    Business,
    BusinessWeeklyHours,
    Customer,
    Employee,
    EmployeeTimeOff,
    EmployeeWeeklyHours,
    SchedulableResource,
    Service,
    ServiceEmployeeEligibility,
    ServiceResourceRequirement,
    User,
)
from app.modules.businesses.authorization import require_membership
from app.modules.identity.router import get_current_user

router = APIRouter(prefix="/businesses/{business_id}/bookings", tags=["Bookings"])
ACTIVE_SEGMENTS = ("held", "confirmed", "in_progress")
HOLD_MINUTES = 10


class SegmentInput(BaseModel):
    service_id: uuid.UUID
    employee_id: uuid.UUID | None = None
    starts_at: datetime

    @field_validator("starts_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("starts_at must include a timezone offset")
        return value


class BookingInput(BaseModel):
    customer_id: uuid.UUID
    segments: list[SegmentInput] = Field(min_length=1, max_length=20)
    idempotency_key: str = Field(min_length=8, max_length=100)
    notes: str | None = Field(default=None, max_length=1000)


def _response(db: Session, booking: Booking) -> dict:
    set_tenant_context(db, booking.business_id)
    segments = db.scalars(
        select(BookingSegment)
        .where(BookingSegment.business_id == booking.business_id, BookingSegment.booking_id == booking.id)
        .order_by(BookingSegment.sequence_number)
    ).all()
    return {
        "id": booking.id,
        "booking_reference": f"BF-{booking.id.hex[:10].upper()}",
        "customer_id": booking.customer_id,
        "status": booking.status,
        "starts_at": booking.starts_at,
        "ends_at": booking.ends_at,
        "total_amount": booking.total_amount,
        "currency": booking.currency,
        "hold_expires_at": booking.hold_expires_at,
        "segments": [
            {
                "id": s.id,
                "service_id": s.service_id,
                "service_name": s.service_name_snapshot,
                "employee_id": s.employee_id,
                "starts_at": s.starts_at,
                "ends_at": s.ends_at,
                "reserved_starts_at": s.reserved_starts_at,
                "reserved_ends_at": s.reserved_ends_at,
                "duration_minutes": s.duration_minutes_snapshot,
                "price_amount": s.price_amount_snapshot,
            }
            for s in segments
        ],
    }


def _local(dt: datetime, timezone_name: str) -> datetime:
    try:
        return dt.astimezone(ZoneInfo(timezone_name))
    except ZoneInfoNotFoundError:
        raise HTTPException(status_code=500, detail="Business timezone is invalid") from None


def _check_hours(db: Session, business: Business, employee_id: uuid.UUID | None,
                 service_start: datetime, service_end: datetime,
                 reserved_start: datetime, reserved_end: datetime) -> None:
    local_start = _local(service_start, business.timezone)
    local_end = _local(service_end, business.timezone)
    if local_start.date() != local_end.date():
        raise HTTPException(status_code=422, detail="A service must finish on the same local day it starts")
    hours = db.get(BusinessWeeklyHours, (business.id, local_start.weekday()))
    if (hours is None or hours.is_closed or hours.opens_at is None or hours.closes_at is None
        or local_start.time().replace(tzinfo=None) < hours.opens_at
        or local_end.time().replace(tzinfo=None) > hours.closes_at):
        raise HTTPException(status_code=409, detail="The requested time is outside business opening hours")
    if employee_id is not None:
        employee_hours = db.get(EmployeeWeeklyHours, (business.id, employee_id, local_start.weekday()))
        local_reserved_start = _local(reserved_start, business.timezone)
        local_reserved_end = _local(reserved_end, business.timezone)
        if (employee_hours is None or employee_hours.is_unavailable
            or employee_hours.starts_at is None or employee_hours.ends_at is None
            or local_reserved_start.time().replace(tzinfo=None) < employee_hours.starts_at
            or local_reserved_end.time().replace(tzinfo=None) > employee_hours.ends_at):
            raise HTTPException(status_code=409, detail="The employee is not available for the full reserved interval")


@router.post("", response_model=None, status_code=status.HTTP_201_CREATED)
def create_booking(
    business_id: uuid.UUID,
    payload: BookingInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    business, _membership = require_membership(business_id, user, db)
    set_tenant_context(db, business.id)
    now = datetime.now(UTC)
    expired_ids = select(Booking.id).where(
        Booking.business_id == business.id,
        Booking.status == "held",
        Booking.hold_expires_at.is_not(None),
        Booking.hold_expires_at <= now,
    )
    db.execute(
        update(BookingSegment)
        .where(BookingSegment.business_id == business.id, BookingSegment.booking_id.in_(expired_ids))
        .values(status="cancelled")
    )
    db.execute(
        update(Booking)
        .where(Booking.business_id == business.id, Booking.id.in_(expired_ids))
        .values(status="expired")
    )

    existing = db.scalar(select(Booking).where(
        Booking.business_id == business.id, Booking.idempotency_key == payload.idempotency_key
    ))
    if existing is not None:
        return _response(db, existing)

    customer = db.scalar(select(Customer).where(
        Customer.id == payload.customer_id, Customer.business_id == business.id
    ))
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    prepared: list[dict] = []
    total = Decimal("0.00")
    for item in payload.segments:
        service = db.scalar(select(Service).where(
            Service.id == item.service_id, Service.business_id == business.id, Service.status == "active"
        ))
        if service is None:
            raise HTTPException(status_code=422, detail="One or more selected services are unavailable")
        employee = None
        if service.requires_employee and item.employee_id is None:
            raise HTTPException(status_code=422, detail=f"An employee is required for {service.name}")
        if item.employee_id is not None:
            employee = db.scalar(select(Employee).where(
                Employee.id == item.employee_id, Employee.business_id == business.id, Employee.status == "active"
            ))
            if employee is None:
                raise HTTPException(status_code=422, detail="The selected employee is not active in this business")
            has_rules = db.scalar(select(ServiceEmployeeEligibility.employee_id).where(
                ServiceEmployeeEligibility.business_id == business.id,
                ServiceEmployeeEligibility.service_id == service.id,
            ).limit(1))
            if has_rules is not None and db.get(
                ServiceEmployeeEligibility, (business.id, service.id, employee.id)
            ) is None:
                raise HTTPException(status_code=422, detail="The employee is not eligible for this service")

        resource_requirements = db.scalars(select(ServiceResourceRequirement).where(
            ServiceResourceRequirement.business_id == business.id,
            ServiceResourceRequirement.service_id == service.id,
        ).order_by(ServiceResourceRequirement.resource_id)).all()

        start = item.starts_at.astimezone(UTC)
        if start <= now:
            raise HTTPException(status_code=409, detail="The requested appointment time must be in the future")
        end = start + timedelta(minutes=service.duration_minutes)
        reserved_start = start - timedelta(minutes=service.buffer_before_minutes)
        reserved_end = end + timedelta(minutes=service.buffer_after_minutes)
        _check_hours(db, business, employee.id if employee else None, start, end, reserved_start, reserved_end)

        if employee is not None:
            time_off = db.scalar(select(EmployeeTimeOff.id).where(
                EmployeeTimeOff.business_id == business.id,
                EmployeeTimeOff.employee_id == employee.id,
                EmployeeTimeOff.starts_at < reserved_end,
                EmployeeTimeOff.ends_at > reserved_start,
            ).limit(1))
            if time_off is not None:
                raise HTTPException(status_code=409, detail="The employee is unavailable during this time")
            conflict = db.scalar(select(BookingSegment.id).where(
                BookingSegment.business_id == business.id,
                BookingSegment.employee_id == employee.id,
                BookingSegment.status.in_(ACTIVE_SEGMENTS),
                BookingSegment.reserved_starts_at < reserved_end,
                BookingSegment.reserved_ends_at > reserved_start,
            ).limit(1))
            if conflict is not None:
                raise HTTPException(status_code=409, detail="The employee is already booked during this time")
            if any(
                p["employee_id"] == employee.id
                and p["reserved_start"] < reserved_end and p["reserved_end"] > reserved_start
                for p in prepared
            ):
                raise HTTPException(status_code=409, detail="This appointment contains overlapping services for the same employee")

        prepared.append({
            "service": service, "employee_id": employee.id if employee else None,
            "start": start, "end": end, "reserved_start": reserved_start, "reserved_end": reserved_end,
            "resource_requirements": [(r.resource_id, r.quantity) for r in resource_requirements],
        })
        total += Decimal(service.price_amount)

    required_resource_ids = sorted({
        resource_id for p in prepared for resource_id, _quantity in p["resource_requirements"]
    }, key=str)
    locked_resources = db.scalars(
        select(SchedulableResource)
        .where(SchedulableResource.business_id == business.id, SchedulableResource.id.in_(required_resource_ids))
        .order_by(SchedulableResource.id)
        .with_for_update()
    ).all() if required_resource_ids else []
    resources_by_id = {r.id: r for r in locked_resources}
    if len(resources_by_id) != len(required_resource_ids):
        raise HTTPException(status_code=409, detail="A required resource is no longer available")
    for resource in locked_resources:
        if resource.status != "active":
            raise HTTPException(status_code=409, detail=f"Required resource {resource.name} is inactive")

    for p in prepared:
        for resource_id, quantity in p["resource_requirements"]:
            resource = resources_by_id[resource_id]
            if quantity > resource.capacity:
                raise HTTPException(status_code=409, detail=f"Required quantity exceeds capacity for resource {resource.name}")
            occupied = db.scalar(
                select(func.coalesce(func.sum(BookingSegmentResource.quantity), 0))
                .join(BookingSegment,
                    (BookingSegment.business_id == BookingSegmentResource.business_id)
                    & (BookingSegment.id == BookingSegmentResource.booking_segment_id))
                .join(Booking,
                    (Booking.business_id == BookingSegment.business_id)
                    & (Booking.id == BookingSegment.booking_id))
                .where(
                    BookingSegmentResource.business_id == business.id,
                    BookingSegmentResource.resource_id == resource_id,
                    BookingSegment.status.in_(ACTIVE_SEGMENTS),
                    Booking.status.in_(("held", "confirmed")),
                    (Booking.status != "held") | (Booking.hold_expires_at.is_(None)) | (Booking.hold_expires_at > now),
                    BookingSegment.reserved_starts_at < p["reserved_end"],
                    BookingSegment.reserved_ends_at > p["reserved_start"],
                )
            )
            requested_together = sum(
                other_quantity
                for other in prepared
                if other["reserved_start"] < p["reserved_end"] and other["reserved_end"] > p["reserved_start"]
                for other_resource_id, other_quantity in other["resource_requirements"]
                if other_resource_id == resource_id
            )
            if occupied + requested_together > resource.capacity:
                raise HTTPException(status_code=409, detail=f"Resource {resource.name} does not have enough capacity at the requested time")

    now = datetime.now(UTC)
    booking = Booking(
        business_id=business.id,
        customer_id=customer.id,
        idempotency_key=payload.idempotency_key,
        status="held",
        starts_at=min(p["start"] for p in prepared),
        ends_at=max(p["end"] for p in prepared),
        total_amount=total,
        currency=business.currency,
        hold_expires_at=now + timedelta(minutes=HOLD_MINUTES),
        notes=payload.notes,
    )
    db.add(booking)
    try:
        db.flush()
        for sequence, p in enumerate(prepared, start=1):
            service = p["service"]
            segment = BookingSegment(
                business_id=business.id, booking_id=booking.id, service_id=service.id,
                employee_id=p["employee_id"], sequence_number=sequence,
                starts_at=p["start"], ends_at=p["end"],
                reserved_starts_at=p["reserved_start"], reserved_ends_at=p["reserved_end"],
                status="held", service_name_snapshot=service.name,
                duration_minutes_snapshot=service.duration_minutes,
                price_amount_snapshot=service.price_amount,
            )
            db.add(segment)
            db.flush()
            for resource_id, quantity in p["resource_requirements"]:
                db.add(BookingSegmentResource(
                    business_id=business.id, booking_segment_id=segment.id,
                    resource_id=resource_id, quantity=quantity,
                ))
        db.add(AuditEvent(
            business_id=business.id, actor_user_id=user.id, action="booking.held",
            target_type="booking", target_id=str(booking.id),
            event_metadata={"segment_count": len(prepared), "total_amount": str(total)},
        ))
        db.commit()
        db.refresh(booking)
        set_tenant_context(db, business.id)
    except IntegrityError as exc:
        db.rollback()
        if "ex_booking_segments_employee_no_overlap" in str(exc.orig):
            raise HTTPException(status_code=409, detail="The employee was just booked for that time") from None
        raise HTTPException(status_code=409, detail="The booking conflicts with an existing reservation") from None
    return _response(db, booking)


def _transition_booking(
    business_id: uuid.UUID,
    booking_id: uuid.UUID,
    user: User,
    db: Session,
    target_status: str,
) -> dict:
    business, _membership = require_membership(business_id, user, db)
    set_tenant_context(db, business.id)
    booking = db.scalar(
        select(Booking)
        .where(Booking.business_id == business.id, Booking.id == booking_id)
        .with_for_update()
    )
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    now = datetime.now(UTC)
    if booking.status == "held" and booking.hold_expires_at is not None:
        expiry = booking.hold_expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        if expiry <= now:
            booking.status = "expired"
            db.execute(
                update(BookingSegment)
                .where(
                    BookingSegment.business_id == business.id,
                    BookingSegment.booking_id == booking.id,
                    BookingSegment.status == "held",
                )
                .values(status="cancelled")
            )
            db.add(AuditEvent(
                business_id=business.id, actor_user_id=user.id,
                action="booking.expired", target_type="booking",
                target_id=str(booking.id), event_metadata={"source": "lifecycle_transition"},
            ))
            db.commit()
            raise HTTPException(status_code=409, detail="The booking hold has expired")
    if target_status == "confirmed":
        if booking.status != "held":
            raise HTTPException(status_code=409, detail="Only an active hold can be confirmed")
        booking.status = "confirmed"
        booking.hold_expires_at = None
        db.execute(
            update(BookingSegment)
            .where(
                BookingSegment.business_id == business.id,
                BookingSegment.booking_id == booking.id,
                BookingSegment.status == "held",
            )
            .values(status="confirmed")
        )
    elif target_status == "cancelled":
        if booking.status not in ("held", "confirmed"):
            raise HTTPException(status_code=409, detail="This booking cannot be cancelled in its current state")
        booking.status = "cancelled"
        booking.hold_expires_at = None
        db.execute(
            update(BookingSegment)
            .where(
                BookingSegment.business_id == business.id,
                BookingSegment.booking_id == booking.id,
                BookingSegment.status.in_(("held", "confirmed")),
            )
            .values(status="cancelled")
        )
    else:
        raise HTTPException(status_code=500, detail="Unsupported booking transition")
    db.add(AuditEvent(
        business_id=business.id, actor_user_id=user.id,
        action=f"booking.{target_status}", target_type="booking",
        target_id=str(booking.id), event_metadata={"previous_status": "held" if target_status == "confirmed" else "held_or_confirmed"},
    ))
    db.commit()
    db.refresh(booking)
    set_tenant_context(db, business.id)
    return _response(db, booking)


@router.post("/{booking_id}/confirm", response_model=None)
def confirm_booking(
    business_id: uuid.UUID,
    booking_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return _transition_booking(business_id, booking_id, user, db, "confirmed")


@router.post("/{booking_id}/cancel", response_model=None)
def cancel_booking(
    business_id: uuid.UUID,
    booking_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return _transition_booking(business_id, booking_id, user, db, "cancelled")


@router.get("", response_model=None)
def list_bookings(
    business_id: uuid.UUID,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List a business's bookings for its authenticated team workspace."""
    if limit < 1 or limit > 250:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 250")
    business, _membership = require_membership(business_id, user, db)
    set_tenant_context(db, business.id)
    rows = db.execute(
        select(Booking, Customer.display_name)
        .join(
            Customer,
            (Customer.business_id == Booking.business_id)
            & (Customer.id == Booking.customer_id),
        )
        .where(Booking.business_id == business.id)
        .order_by(Booking.starts_at.desc())
        .limit(limit)
    ).all()
    results: list[dict] = []
    for booking, customer_name in rows:
        item = _response(db, booking)
        item["customer_name"] = customer_name
        results.append(item)
    return results
