import hmac
import json

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.core.config import get_settings
from app.integrations.meta_whatsapp import verify_meta_signature

router = APIRouter(tags=["Meta WhatsApp webhooks"])


@router.get("/webhooks/meta/whatsapp", response_class=PlainTextResponse)
async def verify_whatsapp_webhook(
    mode: str | None = Query(default=None, alias="hub.mode"),
    verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> str:
    """Complete Meta's webhook subscription handshake."""
    settings = get_settings()
    expected = settings.meta_whatsapp_verify_token
    if (
        mode != "subscribe"
        or not expected
        or not verify_token
        or not hmac.compare_digest(verify_token, expected)
        or challenge is None
    ):
        raise HTTPException(status_code=403, detail="Webhook verification failed")
    return challenge


@router.post("/webhooks/meta/whatsapp")
async def receive_whatsapp_webhook(
    request: Request,
    signature: str | None = Header(default=None, alias="X-Hub-Signature-256"),
) -> dict[str, str]:
    """Verify Meta's request signature before accepting a WhatsApp event."""
    settings = get_settings()
    if not settings.meta_whatsapp_app_secret:
        raise HTTPException(status_code=503, detail="WhatsApp webhook is not configured")
    raw_body = await request.body()
    if not verify_meta_signature(raw_body, signature, settings.meta_whatsapp_app_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        payload = json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from None
    if not isinstance(payload, dict) or payload.get("object") != "whatsapp_business_account":
        raise HTTPException(status_code=400, detail="Unsupported webhook payload")
    # Event routing and message processing are deliberately handled by a later,
    # tenant-aware layer after an authorised WABA-to-business mapping exists.
    return {"status": "accepted"}
