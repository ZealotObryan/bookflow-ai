FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

# Render and Railway build this image from the repository root.
COPY apps/api/pyproject.toml ./pyproject.toml
COPY apps/api/alembic.ini ./alembic.ini
COPY apps/api/migrations ./migrations

RUN uv sync --no-dev

COPY apps/api/app ./app

EXPOSE 8000

# Run database migrations before starting the API. Render supplies PORT at runtime.
CMD ["sh", "-c", "uv run --no-sync alembic -c alembic.ini upgrade head && exec uv run --no-sync uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
