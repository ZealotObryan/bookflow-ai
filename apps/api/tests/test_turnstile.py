import asyncio

import httpx
import pytest
from fastapi import HTTPException

from app.core import turnstile


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeAsyncClient:
    def __init__(self, *, response=None, error=None, **_kwargs):
        self.response = response
        self.error = error
        self.request = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, url, *, data):
        self.request = (url, data)
        if self.error:
            raise self.error
        return self.response


def configured_settings(monkeypatch):
    class Settings:
        cloudflare_turnstile_secret_key = "test-secret"

    monkeypatch.setattr(turnstile, "get_settings", lambda: Settings())


def test_turnstile_fails_closed_when_secret_is_not_configured(monkeypatch):
    class Settings:
        cloudflare_turnstile_secret_key = None

    monkeypatch.setattr(turnstile, "get_settings", lambda: Settings())

    with pytest.raises(HTTPException) as error:
        asyncio.run(turnstile.verify_turnstile_token("valid-looking-token"))

    assert error.value.status_code == 503


def test_turnstile_rejects_empty_token_before_provider_call(monkeypatch):
    configured_settings(monkeypatch)

    with pytest.raises(HTTPException) as error:
        asyncio.run(turnstile.verify_turnstile_token(""))

    assert error.value.status_code == 400


def test_turnstile_rejects_oversized_token(monkeypatch):
    configured_settings(monkeypatch)

    with pytest.raises(HTTPException) as error:
        asyncio.run(turnstile.verify_turnstile_token("x" * 2049))

    assert error.value.status_code == 400


def test_turnstile_accepts_valid_provider_response_and_passes_remote_ip(monkeypatch):
    configured_settings(monkeypatch)
    client = FakeAsyncClient(response=FakeResponse({"success": True}))
    monkeypatch.setattr(turnstile.httpx, "AsyncClient", lambda **kwargs: client)

    asyncio.run(turnstile.verify_turnstile_token("valid-token", "203.0.113.10"))

    url, data = client.request
    assert url == turnstile.SITEVERIFY_URL
    assert data == {
        "secret": "test-secret",
        "response": "valid-token",
        "remoteip": "203.0.113.10",
    }


def test_turnstile_rejects_unsuccessful_provider_response(monkeypatch):
    configured_settings(monkeypatch)
    monkeypatch.setattr(
        turnstile.httpx,
        "AsyncClient",
        lambda **kwargs: FakeAsyncClient(response=FakeResponse({"success": False})),
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(turnstile.verify_turnstile_token("invalid-token"))

    assert error.value.status_code == 400


def test_turnstile_fails_closed_when_provider_is_unavailable(monkeypatch):
    configured_settings(monkeypatch)
    monkeypatch.setattr(
        turnstile.httpx,
        "AsyncClient",
        lambda **kwargs: FakeAsyncClient(error=httpx.ConnectError("provider unavailable")),
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(turnstile.verify_turnstile_token("valid-token"))

    assert error.value.status_code == 503
