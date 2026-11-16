import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.session import get_db, set_tenant_context
from app.models import Booking, BookingSegment, Business, Service, User
from app.models.calendar_feed import BusinessCalendarFeed
from app.modules.businesses.authorization import require_roles
from app.modules.identity.router import get_current_user

router = APIRouter(tags=["Calendar"])


def _escape_ics(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r", "").replace("\n", "\\n")


def _utc_stamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Calendar event timestamps must be timezone-aware")
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def render_calendar(business: Business, rows: list[tuple[Booking, object, list[str]]]) -> str:
    now = _utc_stamp(datetime.now(UTC))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//BookFlow AI//Business Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:" + _escape_ics(business.name + " appointments"),
    ]
    for booking, _customer, service_names in rows:
        summary = "Appointment" if not service_names else "Appointment · " + ", ".join(service_names)
        lines.extend([
            "BEGIN:VEVENT",
            "UID:" + str(booking.id) + "@bookflow.ai",
            "DTSTAMP:" + now,
            "DTSTART:" + _utc_stamp(booking.starts_at),
            "DTEND:" + _utc_stamp(booking.ends_at),
            "SUMMARY:" + _escape_ics(summary),
            "STATUS:CONFIRMED",
            "TRANSP:OPAQUE",
            "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


@router.get("/businesses/{business_id}/calendar/feed")
def calendar_feed_status(business_id: uuid.UUID, user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)) -> dict[str, bool]:
    require_roles(business_id, {"owner", "admin", "manager"}, user, db)
    set_tenant_context(db, business_id)
    feed = db.scalar(select(BusinessCalendarFeed).where(
        BusinessCalendarFeed.business_id == business_id
    ))
    return {"enabled": feed is not None and feed.revoked_at is None}


@router.post("/businesses/{business_id}/calendar/feed")
def create_calendar_feed(business_id: uuid.UUID, user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)) -> dict[str, str]:
    business, _ = require_roles(business_id, {"owner", "admin", "manager"}, user, db)
    set_tenant_context(db, business.id)
    token = secrets.token_urlsafe(40)
    feed = db.scalar(select(BusinessCalendarFeed).where(
        BusinessCalendarFeed.business_id == business.id
    ).with_for_update())
    if feed is None:
        feed = BusinessCalendarFeed(
            business_id=business.id,
            token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        )
        db.add(feed)
    else:
        feed.token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        feed.revoked_at = None
    db.commit()
    return {"feed_token": token, "feed_path": f"/api/v1/calendar/feed/{token}"}


@router.delete("/businesses/{business_id}/calendar/feed", status_code=204)
def revoke_calendar_feed(business_id: uuid.UUID, user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)) -> Response:
    business, _ = require_roles(business_id, {"owner", "admin", "manager"}, user, db)
    set_tenant_context(db, business.id)
    feed = db.scalar(select(BusinessCalendarFeed).where(
        BusinessCalendarFeed.business_id == business.id
    ).with_for_update())
    if feed is not None and feed.revoked_at is None:
        feed.revoked_at = datetime.now(UTC)
        db.commit()
    return Response(status_code=204)


@router.get("/calendar/feed/{token}")
def read_calendar_feed(token: str, db: Session = Depends(get_db)) -> Response:
    if len(token) < 40 or len(token) > 128:
        raise HTTPException(status_code=404, detail="Calendar feed not found")
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    business_id = db.scalar(
        text("SELECT resolve_business_calendar_feed(:token_hash)"),
        {"token_hash": token_hash},
    )
    if business_id is None:
        raise HTTPException(status_code=404, detail="Calendar feed not found")
    set_tenant_context(db, business_id)
    business = db.get(Business, business_id)
    if business is None or business.status != "active":
        raise HTTPException(status_code=404, detail="Calendar feed not found")
    rows = db.scalars(
        select(Booking).where(
            Booking.business_id == business_id,
            Booking.status == "confirmed",
            Booking.ends_at >= datetime.now(UTC),
        ).order_by(Booking.starts_at.asc())
    ).all()
    result: list[tuple[Booking, object, list[str]]] = []
    for booking in rows:
        names = db.scalars(
            select(Service.name)
            .join(
                BookingSegment,
                (BookingSegment.service_id == Service.id)
                & (BookingSegment.business_id == Service.business_id),
            )
            .where(
                BookingSegment.business_id == business_id,
                BookingSegment.booking_id == booking.id,
            )
            .order_by(BookingSegment.sequence_number.asc())
        ).all()
        result.append((booking, None, list(names)))
    calendar = render_calendar(business, result)
    return Response(
        content=calendar,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'inline; filename="bookflow-calendar.ics"',
            "Cache-Control": "private, no-store, max-age=0",
            "X-Content-Type-Options": "nosniff",
        },
    )
