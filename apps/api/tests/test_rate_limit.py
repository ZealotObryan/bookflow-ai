import asyncio

import pytest
from fastapi import HTTPException
from redis.exceptions import RedisError
from starlette.requests import Request

from app.core import rate_limit


class FakeRedis:
    def __init__(self, count: int = 1) -> None:
        self.count = count

    async def eval(self, script: str, numkeys: int, key: str, window: int) -> list[int]:
        return [self.count, window]


class BrokenRedis:
    async def eval(self, script: str, numkeys: int, key: str, window: int) -> list[int]:
        raise RedisError("connection unavailable")


def make_request(body: bytes = b'{"email":"owner@example.com"}') -> Request:
    async def receive() -> dict:
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/login",
            "headers": [(b"content-type", b"application/json")],
            "client": ("192.0.2.10", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
        },
        receive,
    )


def test_auth_rate_limit_passes_under_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rate_limit, "get_redis", lambda: FakeRedis(count=1))
    dependency = rate_limit.auth_rate_limit(
        "login",
        ip_limit=30,
        ip_window=900,
        identifier_limit=5,
        identifier_window=900,
        identifier_field="email",
    )
    asyncio.run(dependency(make_request()))


def test_auth_rate_limit_rejects_over_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rate_limit, "get_redis", lambda: FakeRedis(count=6))
    dependency = rate_limit.auth_rate_limit(
        "login",
        ip_limit=30,
        ip_window=900,
        identifier_limit=5,
        identifier_window=900,
        identifier_field="email",
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(dependency(make_request()))
    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"] == "900"


def test_auth_rate_limit_fails_closed_when_redis_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rate_limit, "get_redis", lambda: BrokenRedis())
    dependency = rate_limit.auth_rate_limit("login", ip_limit=30, ip_window=900)
    with pytest.raises(HTTPException) as error:
        asyncio.run(dependency(make_request()))
    assert error.value.status_code == 503
