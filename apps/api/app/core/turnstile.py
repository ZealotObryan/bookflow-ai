import httpx
from fastapi import HTTPException

from app.core.config import get_settings

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile_token(token: str, remote_ip: str | None = None) -> None:
    """Verify a Turnstile token with Cloudflare; fail closed when not configured."""
    settings = get_settings()
    secret = settings.cloudflare_turnstile_secret_key
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="Online booking verification is not configured yet.",
        )
    if not token or len(token) > 2048:
        raise HTTPException(status_code=400, detail="A valid security verification is required.")

    payload = {"secret": secret, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=2.0)) as client:
            response = await client.post(SITEVERIFY_URL, data=payload)
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(
            status_code=503,
            detail="Security verification is temporarily unavailable. Please try again.",
        ) from None

    if not isinstance(result, dict) or result.get("success") is not True:
        raise HTTPException(status_code=400, detail="Security verification failed. Please try again.")
