import asyncio

import pytest
from fastapi import HTTPException

from app.core import turnstile


def test_turnstile_fails_closed_when_secret_is_not_configured(monkeypatch):
    class Settings:
        cloudflare_turnstile_secret_key = None

    monkeypatch.setattr(turnstile, "get_settings", lambda: Settings())

    with pytest.raises(HTTPException) as error:
        asyncio.run(turnstile.verify_turnstile_token("valid-looking-token"))

    assert error.value.status_code == 503


def test_turnstile_rejects_empty_token_before_provider_call(monkeypatch):
    class Settings:
        cloudflare_turnstile_secret_key = "test-secret"

    monkeypatch.setattr(turnstile, "get_settings", lambda: Settings())

    with pytest.raises(HTTPException) as error:
        asyncio.run(turnstile.verify_turnstile_token(""))

    assert error.value.status_code == 400


def test_turnstile_rejects_oversized_token(monkeypatch):
    class Settings:
        cloudflare_turnstile_secret_key = "test-secret"

    monkeypatch.setattr(turnstile, "get_settings", lambda: Settings())

    with pytest.raises(HTTPException) as error:
        asyncio.run(turnstile.verify_turnstile_token("x" * 2049))

    assert error.value.status_code == 400
