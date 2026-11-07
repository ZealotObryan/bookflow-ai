from fastapi import Response
from starlette.requests import Request

from app.modules.identity.router import (
    _clear_refresh_cookie,
    _require_same_origin,
    _set_refresh_cookie,
)


def make_request(origin: str, fetch_site: str = "same-origin") -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/refresh",
            "headers": [
                (b"origin", origin.encode()),
                (b"sec-fetch-site", fetch_site.encode()),
            ],
            "client": ("192.0.2.20", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
        }
    )


def test_refresh_cookie_is_http_only_and_endpoint_scoped() -> None:
    response = Response()
    _set_refresh_cookie(response, "sensitive-refresh-value")
    cookie = response.headers["set-cookie"].lower()

    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/api/v1/auth/refresh" in cookie
    assert "sensitive-refresh-value" in response.headers["set-cookie"]


def test_refresh_cookie_can_be_cleared() -> None:
    response = Response()
    _clear_refresh_cookie(response)
    cookie = response.headers["set-cookie"].lower()

    assert "max-age=0" in cookie
    assert "path=/api/v1/auth/refresh" in cookie


def test_refresh_requires_exact_frontend_origin() -> None:
    _require_same_origin(make_request("http://localhost:3000"))


def test_refresh_rejects_cross_site_origin() -> None:
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as error:
        _require_same_origin(make_request("https://attacker.example", "cross-site"))
    assert error.value.status_code == 403


def test_refresh_rejects_missing_origin() -> None:
    import pytest
    from fastapi import HTTPException

    request = make_request("http://localhost:3000")
    request.scope["headers"] = []
    with pytest.raises(HTTPException) as error:
        _require_same_origin(request)
    assert error.value.status_code == 403
