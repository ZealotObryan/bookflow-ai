import hashlib
import hmac
import re

import httpx


class MetaWhatsAppError(RuntimeError):
    """Raised when Meta WhatsApp Cloud API rejects a request or is unavailable."""


class MetaWhatsAppClient:
    def __init__(
        self,
        *,
        access_token: str | None,
        phone_number_id: str | None,
        graph_api_version: str = "v22.0",
        base_url: str = "https://graph.facebook.com",
    ) -> None:
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.graph_api_version = graph_api_version
        self.base_url = base_url.rstrip("/")

    def send_text(self, recipient_e164: str, message: str) -> str:
        if not self.access_token or not self.phone_number_id:
            raise MetaWhatsAppError("Meta WhatsApp Cloud API credentials are not configured")
        if not re.fullmatch(r"\+[1-9][0-9]{7,14}", recipient_e164):
            raise MetaWhatsAppError("Recipient must be a valid E.164 phone number")
        if not message.strip() or len(message) > 4096:
            raise MetaWhatsAppError("WhatsApp text must contain 1 to 4096 characters")
        url = (
            f"{self.base_url}/{self.graph_api_version}/"
            f"{self.phone_number_id}/messages"
        )
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_e164.lstrip("+"),
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }
        try:
            response = httpx.post(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                json=payload,
                timeout=httpx.Timeout(15.0, connect=4.0),
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MetaWhatsAppError("Meta WhatsApp message request failed") from exc
        messages = data.get("messages") if isinstance(data, dict) else None
        message_id = messages[0].get("id") if isinstance(messages, list) and messages else None
        if not isinstance(message_id, str) or not message_id:
            raise MetaWhatsAppError("Meta WhatsApp response did not contain a message identifier")
        return message_id


def verify_meta_signature(raw_body: bytes, signature_header: str | None, app_secret: str | None) -> bool:
    if not app_secret or not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        app_secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)
