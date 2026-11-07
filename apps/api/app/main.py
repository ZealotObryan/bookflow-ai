from fastapi import FastAPI

app = FastAPI(
    title="BookFlow AI API",
    description="Backend API for the BookFlow AI appointment platform.",
    version="0.1.0",
)


@app.get("/health", tags=["Operations"])
async def health_check() -> dict[str, str]:
    """Return process health; dependency health checks will be added separately."""
    return {"status": "ok", "service": "bookflow-api"}


@app.get("/api/v1", tags=["API"])
async def api_root() -> dict[str, str]:
    """Identify the initial API namespace."""
    return {"name": "BookFlow AI API", "version": "v1"}
