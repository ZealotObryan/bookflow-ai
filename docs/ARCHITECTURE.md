# BookFlow AI — Architecture

**Status:** Initial architecture baseline; decisions are revisited through documented ADRs.

## 1. Architecture style

Start with a **modular monolith**: one deployable FastAPI application with clear domain modules, one PostgreSQL database, and background workers for asynchronous tasks when required. This keeps early operations and deployment manageable while preserving module boundaries for future extraction if scale justifies it.

The Next.js web application is a separate frontend deployment. The API and worker are hosted on a Python-capable platform; Vercel is used for the web frontend, not assumed to be the long-running Python worker host.

## 2. System context

```text
Customers / Owners
      | WhatsApp
      v
Meta WhatsApp Cloud API ---- webhook ----+
                                         |
Web Dashboard (Next.js) ---- HTTPS ------+--> FastAPI modular monolith
                                         |       |
Google Calendar <---- sync adapter ------+       +--> PostgreSQL (system of record)
                                                 |
Payment provider <---- adapter/webhooks --------+
                                                 |
                                           Redis / Worker
                                                 |
                                      reminders, retries, sync jobs
                                                 |
                                         AI model provider
                                      (tool calls via backend)
```

All external callbacks enter authenticated/validated API endpoints. External providers are adapters; provider-specific payloads do not leak into domain logic.

## 3. Proposed repository structure

```text
apps/
  web/                 Next.js dashboard
  api/
    app/
      modules/
        identity/
        businesses/
        customers/
        services/
        employees/
        availability/
        bookings/
        payments/
        integrations/
        messaging/
        agent/
        notifications/
        audit/
  worker/              background job entry points
packages/
  shared-types/        generated/shared API contracts where useful
infrastructure/
  docker/
docs/
  decisions/
```

Do not create empty abstractions for every future module. Introduce modules when their domain behavior is implemented.

## 4. Domain ownership

- **Identity and tenancy:** users, business memberships, roles and authorization.
- **Scheduling:** business hours, employee availability, blocked periods, service duration and availability calculation.
- **Bookings:** holds, booking lifecycle, booking-service lines and conflict prevention.
- **Payments:** internal payment ledger, provider references, webhook verification and reconciliation.
- **Integrations:** OAuth credentials, WhatsApp accounts, calendar mappings and sync state.
- **Agent:** intent interpretation and tool orchestration; no direct database writes.
- **Notifications/automation:** durable jobs, retries, idempotency and delivery tracking.
- **Audit:** actor, business, action, target and relevant before/after metadata.

Each module owns its business rules and exposes application services to other modules. Avoid circular dependencies and cross-module table manipulation from route handlers.

## 5. Multi-tenancy and security

Initial approach: shared PostgreSQL database with tenant-owned rows carrying a non-null `business_id`. Every API operation derives business membership from the authenticated principal and checks authorization server-side; clients cannot choose an arbitrary tenant context.

PostgreSQL Row-Level Security (RLS) is a defence-in-depth option. Before enabling it, implement transaction-scoped tenant context and prove safe behavior with pooled connections, rollback paths and cross-tenant tests. Never rely on a client-supplied business ID or RLS alone as the authorization model.

Platform administration uses separate, audited privileges. Secrets are encrypted at rest where stored and never returned to ordinary API clients.

## 6. Booking consistency

PostgreSQL is authoritative. Availability reads are advisory; the booking write path must revalidate inside a transaction. Use explicit holds with expiry, idempotency keys for retried requests, and database-enforced conflict protection for resources that cannot overlap.

The exact constraint strategy depends on the finalized scheduling model (employee/resource allocation, multi-service sequence and buffer semantics). It will be documented and tested before the booking engine is considered complete.

## 7. Integration reliability

- Use provider adapters and normalized internal events.
- Verify webhook signatures and provider event authenticity.
- Store provider event identifiers and enforce idempotent processing.
- Use an outbox/job pattern for side effects that must follow a committed database transaction.
- Retry transient failures with bounded backoff and dead-letter/manual recovery.
- Track sync status, last attempt, next attempt and actionable error details.
- Never treat an external calendar event as a BookFlow booking without explicit reconciliation rules.

## 8. AI safety boundary

The model receives only the context needed for the current business interaction and a defined set of tools. Tools call application services, validate input, enforce tenant/role access and return structured outcomes. The model cannot issue SQL or bypass business rules.

The backend must verify availability, prices, policy, payment status and booking state at execution time. High-impact owner actions may require confirmation. Log tool invocations and outcomes without unnecessarily retaining sensitive message content.

## 9. Deployment boundaries

- Web: Vercel project `bookflow-ai`, repository root `apps/web`.
- API: deploy to a Python ASGI-capable host.
- Worker: deploy as a separate process when asynchronous workload is introduced.
- Database: managed PostgreSQL with automated backups and tested restore procedure.
- Redis: managed Redis when queueing/caching is introduced.

No production environment or deployment is configured by this document.
