# BookFlow AI

**AI-powered appointment management for service businesses.**

BookFlow AI is a multi-tenant SaaS platform that helps appointment-based businesses manage bookings, customers, staff, payments and communications through WhatsApp, a calendar and a responsive web dashboard.

## Product direction

- **WhatsApp:** customer booking conversations and owner operations, powered by an AI assistant.
- **Calendar:** reliable scheduling with Google Calendar integration.
- **Web dashboard:** business setup, services, staff, bookings, customers, payments and reporting.
- **Booking engine:** the authoritative source for availability, holds and confirmed appointments.
- **Payments:** provider-backed payment status and reconciliation; screenshots are never treated as proof of payment.

The initial market is Malawi, with a design that supports expansion across Africa and multiple time zones.

## Technology direction

- Web: Next.js, React and TypeScript
- API: Python and FastAPI
- Data: PostgreSQL, SQLAlchemy and Alembic
- Background work: a durable worker/queue when asynchronous workflows are introduced
- Integrations: Meta WhatsApp Business Platform, Google Calendar and payment-provider adapters
- AI: tool-calling model behind validated backend operations

The first release is a **modular monolith**, not a collection of microservices.

## Repository layout

```text
apps/
  web/       Next.js dashboard (Vercel root directory)
  api/       FastAPI application and migrations
docs/
  decisions/ architecture decision records
docker-compose.yml
```

## Local development

### Requirements

- Node.js 22+
- npm 10+
- Python 3.12+
- uv
- Docker Engine/Desktop with Compose

### Configure environment and PostgreSQL

From the repository root:

```bash
cp .env.example .env
docker compose up -d db
```

The local PostgreSQL instance is exposed on port 5432 by default. Change the example password before using this setup beyond a disposable local environment.

### Web application

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000.

### API and database migrations

```bash
cd apps/api
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs

Run backend checks:

```bash
uv run pytest
uv run ruff check .
```

The first migration creates users, businesses and business memberships. It does not yet create booking or payment tables.

## Engineering principles

1. PostgreSQL is authoritative for bookings, customers and payment records.
2. AI may interpret requests and call approved tools; it cannot independently confirm availability, bookings or payments.
3. Tenant isolation and authorization are enforced server-side on every tenant-owned operation.
4. Booking conflicts are prevented by database-backed concurrency controls, not UI checks alone.
5. Service items can run sequentially or simultaneously; each item reserves its own employee and required shared resources for its exact time interval.
6. External integrations are idempotent, observable and recoverable.
7. Secrets and real customer data never belong in source control.

## Project documentation

- [Product specification](docs/PRODUCT_SPEC.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Initial data model](docs/DATA_MODEL.md)
- [Development workflow](docs/DEVELOPMENT.md)
- [Scheduling model decision](docs/decisions/ADR-001-scheduling-model.md)

## Status

Application scaffolding and the first identity/tenancy database migration are in progress. No production deployment is active.
