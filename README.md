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

- Web: Next.js, React, TypeScript and Tailwind CSS
- API: Python, FastAPI, SQLAlchemy and Alembic
- Data: PostgreSQL
- Background work: Redis-backed worker when required
- Integrations: Meta WhatsApp Business Platform, Google Calendar and payment-provider adapters
- AI: tool-calling model behind validated backend operations

The first release is a **modular monolith**, not a collection of microservices.

## Repository layout

```text
apps/
  web/       Next.js dashboard
  api/       FastAPI application
  worker/    background jobs (introduced when needed)
packages/
  shared-types/
docs/
infrastructure/
```

## Engineering principles

1. PostgreSQL is authoritative for bookings, customers and payment records.
2. AI may interpret requests and call approved tools; it cannot independently confirm availability, bookings or payments.
3. Tenant isolation and authorization are enforced server-side on every tenant-owned operation.
4. Booking conflicts are prevented by database-backed concurrency controls, not UI checks alone.
5. External integrations are idempotent, observable and recoverable.
6. Secrets and real customer data never belong in source control.

## Project documentation

- [Product specification](docs/PRODUCT_SPEC.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Initial data model](docs/DATA_MODEL.md)
- [Development workflow](docs/DEVELOPMENT.md)

## Status

Project foundation and architecture documentation are being established. No production deployment is active yet.
