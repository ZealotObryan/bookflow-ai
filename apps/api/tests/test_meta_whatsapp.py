import hashlib
import hmac

import httpx
import pytest

from app.integrations.meta_whatsapp import (
    MetaWhatsAppClient,
    MetaWhatsAppError,
    verify_meta_signature,
)


def test_send_text_uses_meta_cloud_api(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        captured.update({"url": url, **kwargs})
        return httpx.Response(
            200,
            json={"messages": [{"id": "wamid.test-123"}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    client = MetaWhatsAppClient(
        access_token="test-token",
        phone_number_id="123456789",
        graph_api_version="v22.0",
    )

    result = client.send_text("+265991234567", "Your booking is confirmed.")

    assert result == "wamid.test-123"
    assert captured["url"] == "https://graph.facebook.com/v22.0/123456789/messages"
    assert captured["headers"]["Authorization"] == "Bearer test-token"
    assert captured["json"]["to"] == "265991234567"
    assert captured["json"]["messaging_product"] == "whatsapp"


def test_send_text_fails_closed_without_credentials() -> None:
    client = MetaWhatsAppClient(access_token=None, phone_number_id=None)
    with pytest.raises(MetaWhatsAppError):
        client.send_text("+265991234567", "Hello")


def test_send_text_rejects_invalid_phone() -> None:
    client = MetaWhatsAppClient(access_token="token", phone_number_id="123")
    with pytest.raises(MetaWhatsAppError):
        client.send_text("0991234567", "Hello")


def test_verify_meta_signature() -> None:
    body = b'{"object":"whatsapp_business_account"}'
    secret = "app-secret"
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    assert verify_meta_signature(body, f"sha256={digest}", secret)
    assert not verify_meta_signature(body, "sha256=wrong", secret)
    assert not verify_meta_signature(body, f"sha256={digest}", None)
