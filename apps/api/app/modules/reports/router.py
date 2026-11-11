from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db, set_tenant_context
from app.models import Booking, Project, User
from app.modules.businesses.authorization import require_membership
from app.modules.identity.router import get_current_user
from app.modules.reports.schemas import BusinessReportResponse, DailyActivity

router = APIRouter(prefix="/businesses/{business_id}/reports", tags=["Reports"])


@router.get("/overview", response_model=BusinessReportResponse)
def get_business_report(
    business_id: UUID,
    period: str = Query(default="7d", pattern="^(7d|30d|month)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BusinessReportResponse:
    business, _ = require_membership(business_id, user, db)
    set_tenant_context(db, business.id)

    try:
        today = datetime.now(ZoneInfo(business.timezone)).date()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Business timezone is invalid") from exc

    if period == "7d":
        start_date = today - timedelta(days=6)
    elif period == "30d":
        start_date = today - timedelta(days=29)
    else:
        start_date = today.replace(day=1)

    start_at = datetime.combine(start_date, time.min, tzinfo=ZoneInfo(business.timezone)).astimezone(UTC)
    end_at = datetime.combine(today + timedelta(days=1), time.min, tzinfo=ZoneInfo(business.timezone)).astimezone(UTC)

    booking_rows = db.execute(
        select(Booking.status, func.count(Booking.id), func.coalesce(func.sum(Booking.total_amount), 0))
        .where(
            Booking.business_id == business.id,
            Booking.starts_at >= start_at,
            Booking.starts_at < end_at,
        )
        .group_by(Booking.status)
    ).all()
    counts = {status: int(count) for status, count, _ in booking_rows}
    values = {status: Decimal(amount) for status, _, amount in booking_rows}

    project_rows = db.execute(
        select(
            func.count(Project.id),
            func.coalesce(func.sum(Project.quoted_amount), 0),
            func.coalesce(func.sum(Project.amount_paid), 0),
        ).where(
            Project.business_id == business.id,
            Project.created_at >= start_at,
            Project.created_at < end_at,
        )
    ).one()
    project_count, quoted_value, recorded_paid = project_rows

    daily_rows = db.execute(
        select(Booking.starts_at, Booking.status).where(
            Booking.business_id == business.id,
            Booking.starts_at >= start_at,
            Booking.starts_at < end_at,
        )
    ).all()
    daily_counts: dict[datetime.date, list[int]] = {}
    business_zone = ZoneInfo(business.timezone)
    for starts_at, booking_status in daily_rows:
        local_day = starts_at.astimezone(business_zone).date()
        counts_for_day = daily_counts.setdefault(local_day, [0, 0])
        counts_for_day[0] += 1
        if booking_status == "confirmed":
            counts_for_day[1] += 1

    daily_activity = [
        DailyActivity(
            date=start_date + timedelta(days=offset),
            bookings=daily_counts.get(start_date + timedelta(days=offset), [0, 0])[0],
            confirmed_bookings=daily_counts.get(start_date + timedelta(days=offset), [0, 0])[1],
        )
        for offset in range((today - start_date).days + 1)
    ]

    return BusinessReportResponse(
        business_id=business.id,
        currency=business.currency,
        period=period,
        bookings_total=sum(counts.values()),
        bookings_confirmed=counts.get("confirmed", 0),
        bookings_held=counts.get("held", 0),
        bookings_cancelled=counts.get("cancelled", 0),
        confirmed_booking_value=values.get("confirmed", Decimal("0")),
        project_count=int(project_count),
        project_quoted_value=Decimal(quoted_value),
        project_amount_recorded_paid=Decimal(recorded_paid),
        project_outstanding_value=max(Decimal(quoted_value) - Decimal(recorded_paid), Decimal("0")),
        daily_activity=daily_activity,
    )
