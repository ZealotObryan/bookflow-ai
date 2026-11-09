from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.db.session import set_tenant_context
from app.models import (
    AuditEvent,
    AuthSession,
    AuthToken,
    Booking,
    BookingSegment,
    Business,
    PhoneOtpChallenge,
)


def purge_expired_auth_material(db: Session) -> dict[str, int]:
    """Remove expired bearer material while retaining limited audit history."""
    now = datetime.now(UTC)
    otp_result = db.execute(
        update(PhoneOtpChallenge)
        .where(
            PhoneOtpChallenge.expires_at <= now,
            PhoneOtpChallenge.code_ciphertext.is_not(None),
        )
        .values(
            code_ciphertext=None,
            consumed_at=func.coalesce(PhoneOtpChallenge.consumed_at, PhoneOtpChallenge.expires_at),
        )
    )
    token_result = db.execute(
        delete(AuthToken).where(AuthToken.expires_at < now - timedelta(days=7))
    )
    challenge_result = db.execute(
        delete(PhoneOtpChallenge).where(PhoneOtpChallenge.expires_at < now - timedelta(days=7))
    )
    session_result = db.execute(
        delete(AuthSession).where(
            (AuthSession.expires_at < now - timedelta(days=90))
            | (AuthSession.revoked_at < now - timedelta(days=90))
        )
    )
    db.commit()
    return {
        "otp_ciphertexts_cleared": otp_result.rowcount or 0,
        "email_tokens_deleted": token_result.rowcount or 0,
        "otp_challenges_deleted": challenge_result.rowcount or 0,
        "sessions_deleted": session_result.rowcount or 0,
    }



def expire_booking_holds(db: Session) -> dict[str, int]:
    """Expire timed-out holds for every business, respecting tenant RLS."""
    now = datetime.now(UTC)
    expired_count = 0
    businesses = db.scalars(select(Business.id).where(Business.status == "active")).all()
    for business_id in businesses:
        set_tenant_context(db, business_id)
        expired_ids = db.scalars(
            select(Booking.id)
            .where(
                Booking.business_id == business_id,
                Booking.status == "held",
                Booking.hold_expires_at.is_not(None),
                Booking.hold_expires_at <= now,
            )
            .order_by(Booking.id)
            .with_for_update(skip_locked=True)
        ).all()
        if not expired_ids:
            db.rollback()
            continue
        db.execute(
            update(BookingSegment)
            .where(
                BookingSegment.business_id == business_id,
                BookingSegment.booking_id.in_(expired_ids),
                BookingSegment.status == "held",
            )
            .values(status="cancelled")
        )
        db.execute(
            update(Booking)
            .where(
                Booking.business_id == business_id,
                Booking.id.in_(expired_ids),
                Booking.status == "held",
            )
            .values(status="expired")
        )
        db.add(AuditEvent(
            business_id=business_id,
            actor_user_id=None,
            action="booking.holds_expired",
            target_type="booking_batch",
            target_id=None,
            event_metadata={"count": len(expired_ids), "source": "scheduled_maintenance"},
        ))
        db.commit()
        expired_count += len(expired_ids)
    return {"expired_bookings": expired_count}
