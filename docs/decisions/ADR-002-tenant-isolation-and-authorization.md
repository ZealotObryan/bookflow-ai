# ADR-002: Tenant isolation and authorization

- **Status:** Accepted for implementation
- **Date:** 2026-11-07

## Context

BookFlow uses a shared PostgreSQL database. A user may belong to multiple businesses, and membership roles are owner, admin, manager and staff. Client-supplied business identifiers are untrusted input and must never grant access.

The current schema contains identity, business and membership records, but no tenant-owned operational tables such as services, customers, bookings or payments. Membership lookup is therefore required before a request can establish its tenant context.

## Decisions

1. Authenticate the user from the validated access token and active server-side session.
2. Resolve business access by joining the requested business to an active membership for the authenticated user. Never trust a role, user ID or business ID supplied as authorization evidence by the client.
3. Return the same 404 response when a business is absent or the caller has no active membership, avoiding tenant-existence disclosure.
4. Create a business and its initial active owner membership in one database transaction. The owner identity and role are derived exclusively from the authenticated principal.
5. Require verified email before business creation. Future invitation acceptance must use a single-use, expiring invitation token and must not permit self-assigned privileged roles.
6. Use explicit server-side role allowlists for every write operation. A role is not inferred from UI visibility.
7. Add PostgreSQL Row-Level Security when the first tenant-owned operational tables are introduced. The application will set tenant context transaction-locally with SET LOCAL app.current_business_id only after verifying active membership. Policies use current_setting('app.current_business_id', true) and deny access when no context exists.
8. RLS must be forced on tenant-owned tables. The runtime database role must not own protected tables, be a superuser, or have BYPASSRLS. Migration ownership and runtime privileges must be separate.
9. Tenant context must be set inside the same SQL transaction as tenant data access. SET LOCAL resets on commit/rollback and is safe for pooled connections when every tenant operation uses a transaction boundary. No session-level SET is permitted.
10. Membership bootstrap tables will not use a policy that recursively queries the same protected membership table. Membership verification happens before tenant context is set; a later carefully reviewed security-definer helper may be considered if a specific policy requires it.
11. Audit sensitive business and membership actions. Audit metadata must be allowlisted and must never contain passwords, access/refresh tokens, OTP codes, API keys or raw payment credentials.

## Initial implementation boundary

The first business endpoints support create, list and read. Create atomically creates the tenant and owner membership. List/read return only active memberships. Membership management, invitation flows, full role matrix and RLS enforcement remain separate implementation tasks and release gates.

## Consequences

The shared database remains operationally simple, while application authorization and later database RLS provide independent controls. Until RLS is enabled, every tenant-owned query must be explicitly scoped by business_id and membership must be checked server-side. Cross-tenant integration tests are required before tenant-owned data features are released.
