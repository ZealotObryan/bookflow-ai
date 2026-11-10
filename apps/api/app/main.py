from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.rate_limit import close_redis
from app.modules.bookings.availability import router as availability_router
from app.modules.bookings.router import router as bookings_router
from app.modules.businesses.router import router as businesses_router
from app.modules.identity.router import router as identity_router
from app.modules.projects.router import router as projects_router
from app.modules.records.router import router as records_router
from app.modules.whatsapp.entry_links import router as whatsapp_entry_router
from app.modules.whatsapp.router import router as whatsapp_router


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

frontend = urlsplit(get_settings().frontend_base_url)
frontend_origin = f"{frontend.scheme}://{frontend.netloc}"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Retry-After"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


app.include_router(identity_router, prefix="/api/v1")
app.include_router(businesses_router, prefix="/api/v1")
app.include_router(bookings_router, prefix="/api/v1")
app.include_router(availability_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(records_router, prefix="/api/v1")
app.include_router(whatsapp_router, prefix="/api/v1")
app.include_router(whatsapp_entry_router, prefix="/api/v1")


@app.get("/health", tags=["Operations"])
async def health_check() -> dict[str, str]:
    """Return process health without depending on external services."""
    return {"status": "ok", "service": "bookflow-api"}


@app.get("/api/v1", tags=["API"])
async def api_root() -> dict[str, str]:
    """Identify the initial API namespace."""
    return {"name": "BookFlow AI API", "version": "v1"}
