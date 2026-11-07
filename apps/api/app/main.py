from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.rate_limit import close_redis
from app.modules.identity.router import router as identity_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await close_redis()


app = FastAPI(
    title="BookFlow AI API",
    description="Backend API for the BookFlow AI appointment platform.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


app.include_router(identity_router, prefix="/api/v1")


@app.get("/health", tags=["Operations"])
async def health_check() -> dict[str, str]:
    """Return process health without depending on external services."""
    return {"status": "ok", "service": "bookflow-api"}


@app.get("/api/v1", tags=["API"])
async def api_root() -> dict[str, str]:
    """Identify the initial API namespace."""
    return {"name": "BookFlow AI API", "version": "v1"}
