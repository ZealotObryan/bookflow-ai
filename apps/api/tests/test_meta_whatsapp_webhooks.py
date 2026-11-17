import hashlib
import hmac
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.whatsapp import webhooks


def build_client(monkeypatch, *, app_secret="test-secret", verify_token="verify-me"):
    monkeypatch.setattr(
        webhooks,
        "get_settings",
        lambda: SimpleNamespace(
            meta_whatsapp_app_secret=app_secret,
            meta_whatsapp_verify_token=verify_token,
        ),
    )
    app = FastAPI()
    app.include_router(webhooks.router)
    return TestClient(app)


def test_meta_webhook_get_verification(monkeypatch):
    client = build_client(monkeypatch)

    response = client.get(
        "/webhooks/meta/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "verify-me",
            "hub.challenge": "challenge-123",
        },
    )

    assert response.status_code == 200
    assert response.text == "challenge-123"


def test_meta_webhook_rejects_wrong_verify_token(monkeypatch):
    client = build_client(monkeypatch)

    response = client.get(
        "/webhooks/meta/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong",
            "hub.challenge": "challenge-123",
        },
    )

    assert response.status_code == 403


def test_meta_webhook_accepts_valid_signed_event(monkeypatch):
    client = build_client(monkeypatch)
    body = b'{"object":"whatsapp_business_account","entry":[]}'
    digest = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()

    response = client.post(
        "/webhooks/meta/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": f"sha256={digest}"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "accepted"}


def test_meta_webhook_rejects_invalid_signature(monkeypatch):
    client = build_client(monkeypatch)

    response = client.post(
        "/webhooks/meta/whatsapp",
        content=b'{"object":"whatsapp_business_account","entry":[]}',
        headers={"X-Hub-Signature-256": "sha256=invalid"},
    )

    assert response.status_code == 401


def test_meta_webhook_requires_app_secret(monkeypatch):
    client = build_client(monkeypatch, app_secret=None)

    response = client.post(
        "/webhooks/meta/whatsapp",
        content=b'{"object":"whatsapp_business_account","entry":[]}',
    )

    assert response.status_code == 503
