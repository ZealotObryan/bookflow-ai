import uuid
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db, set_tenant_context
from app.models import (
    Booking,
    BookingSegment,
    BusinessWeeklyHours,
    Employee,
    EmployeeTimeOff,
    EmployeeWeeklyHours,
    Service,
    ServiceEmployeeEligibility,
    ServiceResourceRequirement,
    User,
)
from app.modules.businesses.authorization import require_membership
from app.modules.identity.router import get_current_user

router = APIRouter(prefix="/businesses/{business_id}/availability", tags=["Availability"])
ACTIVE_SEGMENTS = ("held", "confirmed", "in_progress")


def _local_interval(day: date, start: time, duration: int, timezone: ZoneInfo) -> tuple[datetime, datetime]:
    local_start = datetime.combine(day, start, tzinfo=timezone)
    local_end = local_start + timedelta(minutes=duration)
    return local_start.astimezone(UTC), local_end.astimezone(UTC)


@router.get("")
def get_availability(
    business_id: uuid.UUID,
    service_id: uuid.UUID,
    target_date: date = Query(alias="date"),
    employee_id: uuid.UUID | None = None,
    slot_interval_minutes: int = Query(default=15, ge=5, le=60),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    business, _membership = require_membership(business_id, user, db)
    set_tenant_context(db, business.id)

    try:
        timezone = ZoneInfo(business.timezone)
    except ZoneInfoNotFoundError:
        raise HTTPException(status_code=500, detail="Business timezone is invalid") from None

    service = db.scalar(
        select(Service).where(
            Service.id == service_id,
            Service.business_id == business.id,
            Service.status == "active",
        )
    )
    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")

    resource_needed = db.scalar(
        select(ServiceResourceRequirement.resource_id)
        .where(
            ServiceResourceRequirement.business_id == business.id,
            ServiceResourceRequirement.service_id == service.id,
        )
        .limit(1)
    )
    if resource_needed is not None:
        return {"date": target_date, "timezone": business.timezone, "slots": [],
                "unavailable_reason": "Resource allocation is not enabled for this service yet"}

    business_hours = db.get(BusinessWeeklyHours, (business.id, target_date.weekday()))
    if (
        business_hours is None
        or business_hours.is_closed
        or business_hours.opens_at is None
        or business_hours.closes_at is None
    ):
        return {"date": target_date, "timezone": business.timezone, "slots": []}

    if employee_id is not None:
        employees = db.scalars(
            select(Employee).where(
                Employee.business_id == business.id,
                Employee.id == employee_id,
                Employee.status == "active",
            )
        ).all()
        if not employees:
            raise HTTPException(status_code=404, detail="Active employee not found")
    elif service.requires_employee:
        employees = db.scalars(
            select(Employee).where(
                Employee.business_id == business.id,
                Employee.status == "active",
            ).order_by(Employee.display_name)
        ).all()
    else:
        employees = []

    eligibility_rows = db.scalars(
        select(ServiceEmployeeEligibility.employee_id).where(
            ServiceEmployeeEligibility.business_id == business.id,
            ServiceEmployeeEligibility.service_id == service.id,
        )
    ).all()
    eligible_ids = set(eligibility_rows)
    if eligible_ids:
        employees = [employee for employee in employees if employee.id in eligible_ids]

    if service.requires_employee and not employees:
        return {"date": target_date, "timezone": business.timezone, "slots": []}

    now = datetime.now(UTC)
    day_start, day_end = _local_interval(target_date, time.min, 24 * 60, timezone)
    segments = db.scalars(
        select(BookingSegment)
        .join(Booking, (Booking.id == BookingSegment.booking_id) & (Booking.business_id == BookingSegment.business_id))
        .where(
            BookingSegment.business_id == business.id,
            BookingSegment.status.in_(ACTIVE_SEGMENTS),
            BookingSegment.reserved_starts_at < day_end,
            BookingSegment.reserved_ends_at > day_start,
            Booking.status.in_(("held", "confirmed")),
            (Booking.status != "held") | (Booking.hold_expires_at.is_(None)) | (Booking.hold_expires_at > now),
        )
    ).all()

    slots: list[dict] = []
    cursor = datetime.combine(target_date, business_hours.opens_at)
    closing = datetime.combine(target_date, business_hours.closes_at)
    while cursor < closing:
        local_end = cursor + timedelta(minutes=service.duration_minutes)
        if local_end > closing:
            break
        local_reserved_start = cursor - timedelta(minutes=service.buffer_before_minutes)
        local_reserved_end = local_end + timedelta(minutes=service.buffer_after_minutes)
        start_utc = cursor.replace(tzinfo=timezone).astimezone(UTC)
        end_utc = local_end.replace(tzinfo=timezone).astimezone(UTC)
        reserved_start_utc = local_reserved_start.replace(tzinfo=timezone).astimezone(UTC)
        reserved_end_utc = local_reserved_end.replace(tzinfo=timezone).astimezone(UTC)

        if start_utc > now:
            candidate_employees: list[Employee | None] = employees if employees else [None]
            for employee in candidate_employees:
                if employee is not None:
                    employee_hours = db.get(
                        EmployeeWeeklyHours, (business.id, employee.id, target_date.weekday())
                    )
                    if (
                        employee_hours is None
                        or employee_hours.is_unavailable
                        or employee_hours.starts_at is None
                        or employee_hours.ends_at is None
                        or local_reserved_start.date() != target_date
                        or local_reserved_start.time() < employee_hours.starts_at
                        or local_reserved_end.date() != target_date
                        or local_reserved_end.time() > employee_hours.ends_at
                    ):
                        continue
                    time_off = db.scalar(
                        select(EmployeeTimeOff.id).where(
                            EmployeeTimeOff.business_id == business.id,
                            EmployeeTimeOff.employee_id == employee.id,
                            EmployeeTimeOff.starts_at < reserved_end_utc,
                            EmployeeTimeOff.ends_at > reserved_start_utc,
                        ).limit(1)
                    )
                    if time_off is not None:
                        continue
                    conflict = any(
                        segment.employee_id == employee.id
                        and segment.reserved_starts_at.replace(tzinfo=UTC) < reserved_end_utc
                        and segment.reserved_ends_at.replace(tzinfo=UTC) > reserved_start_utc
                        for segment in segments
                    )
                    if conflict:
                        continue
                slots.append({
                    "starts_at": start_utc,
                    "ends_at": end_utc,
                    "employee_id": employee.id if employee else None,
                    "employee_name": employee.display_name if employee else None,
                })
        cursor += timedelta(minutes=slot_interval_minutes)

    return {"date": target_date, "timezone": business.timezone, "slots": slots}
