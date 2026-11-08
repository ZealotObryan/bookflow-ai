from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, update
from sqlalchemy.orm import Session

from app.models import AuthSession, AuthToken, PhoneOtpChallenge


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
