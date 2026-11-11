import httpx

from app.core.config import get_settings


class EmailDeliveryError(RuntimeError):
    """Raised when transactional email cannot be securely delivered."""


def send_transactional_email(*, recipient: str, subject: str, text_body: str) -> None:
    settings = get_settings()
    if not settings.resend_api_key or not settings.resend_from_email:
        raise EmailDeliveryError("Transactional email is not configured")

    normalized_recipient = recipient.strip().casefold()
    if settings.resend_test_mode:
        allowed_recipient = (settings.resend_test_recipient or "").strip().casefold()
        if not allowed_recipient or normalized_recipient != allowed_recipient:
            raise EmailDeliveryError("Recipient is not permitted in Resend test mode")

    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            json={
                "from": settings.resend_from_email,
                "to": [normalized_recipient],
                "subject": subject,
                "text": text_body,
            },
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise EmailDeliveryError("Transactional email delivery failed") from exc
