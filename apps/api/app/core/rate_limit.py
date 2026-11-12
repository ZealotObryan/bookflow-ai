import hashlib
import hmac
from collections.abc import Callable

from fastapi import HTTPException, Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings

_redis: Redis | None = None

# Increment and set expiry atomically so concurrent requests cannot bypass a fixed window.
_INCREMENT_WITH_TTL = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return {current, redis.call('TTL', KEYS[1])}
"""


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            get_settings().redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            health_check_interval=30,
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def _digest(value: str) -> str:
    secret = get_settings().jwt_secret_key.encode("utf-8")
    return hmac.new(secret, value.encode("utf-8"), hashlib.sha256).hexdigest()


def auth_rate_limit(
    scope: str,
    *,
    ip_limit: int,
    ip_window: int,
    identifier_limit: int | None = None,
    identifier_window: int | None = None,
    identifier_field: str | None = None,
) -> Callable:
    async def dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        buckets = [(f"auth:{scope}:ip:{_digest(client_ip)}", ip_limit, ip_window)]

        if identifier_field and identifier_limit and identifier_window:
            try:
                body = await request.json()
            except (ValueError, UnicodeDecodeError):
                body = {}
            identifier = body.get(identifier_field) if isinstance(body, dict) else None
            if isinstance(identifier, str) and identifier.strip():
                normalized = identifier.strip().casefold()
                buckets.append(
                    (
                        f"auth:{scope}:id:{_digest(normalized)}",
                        identifier_limit,
                        identifier_window,
                    )
                )

        try:
            redis = get_redis()
            for key, limit, window in buckets:
                count, ttl = await redis.eval(_INCREMENT_WITH_TTL, 1, key, window)
                if int(count) > limit:
                    raise HTTPException(
                        status_code=429,
                        detail="Too many attempts. Please wait before trying again.",
                        headers={"Retry-After": str(max(int(ttl), 1))},
                    )
        except HTTPException:
            raise
        except RedisError:
            # Authentication endpoints fail closed if the distributed limiter is unavailable.
            raise HTTPException(
                status_code=503,
                detail="Authentication is temporarily unavailable. Please try again shortly.",
                headers={"Retry-After": "30"},
            ) from None

    return dependency
