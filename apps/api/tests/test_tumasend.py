import httpx
import pytest

from app.integrations.tumasend import TumaSendClient, TumaSendError


def test_whatsapp_uses_whatsapp_scoped_key(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        captured.update({"url": url, **kwargs})
        return httpx.Response(
            201,
            json={"success": True, "batch_id": "wa_batch_123"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    client = TumaSendClient(
        whatsapp_api_key="wa_test_key",
        sms_api_key="sms_test_key",
        sms_sender_id="BookFlow",
    )

    batch_id = client.send_whatsapp("+265991234567", "Your code is 123456")

    assert batch_id == "wa_batch_123"
    assert captured["url"] == "https://gateway.tumasend.com/api/v1/send/whatsapp"
    assert captured["headers"]["x-api-key"] == "wa_test_key"
    assert captured["json"]["recipients"] == ["+265991234567"]


def test_sms_uses_sms_scoped_key_and_sender_id(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        captured.update({"url": url, **kwargs})
        return httpx.Response(
            201,
            json={"success": True, "batch_id": "sms_batch_123"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    client = TumaSendClient(
        whatsapp_api_key="wa_test_key",
        sms_api_key="sms_test_key",
        sms_sender_id="BookFlow",
    )

    batch_id = client.send_sms("+265991234567", "Your code is 123456")

    assert batch_id == "sms_batch_123"
    assert captured["url"] == "https://gateway.tumasend.com/api/v1/send/sms"
    assert captured["headers"]["x-api-key"] == "sms_test_key"
    assert captured["json"]["from"] == "BookFlow"


def test_missing_channel_key_fails_closed() -> None:
    client = TumaSendClient(
        whatsapp_api_key=None,
        sms_api_key="sms_test_key",
        sms_sender_id="BookFlow",
    )

    with pytest.raises(TumaSendError):
        client.send_whatsapp("+265991234567", "Your code is 123456")


def test_sms_requires_approved_sender_id() -> None:
    client = TumaSendClient(
        whatsapp_api_key="wa_test_key",
        sms_api_key="sms_test_key",
        sms_sender_id=None,
    )

    with pytest.raises(TumaSendError):
        client.send_sms("+265991234567", "Your code is 123456")
