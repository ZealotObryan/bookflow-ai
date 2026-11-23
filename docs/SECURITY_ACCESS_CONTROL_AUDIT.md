# BookFlow AI — Security and Tenant Access Audit

**Status:** Initial audit in progress  
**Branch:** `security/tenant-access-hardening`  
**Production impact:** None; this branch is not deployed.

## Scope and architecture

BookFlow uses PostgreSQL, SQLAlchemy/Alembic and a FastAPI backend. This audit applies least-privilege and row-level isolation principles to that architecture; it does not introduce Supabase dependencies.

The application currently combines:
- PostgreSQL RLS for tenant-boundary enforcement;
- FastAPI membership and role checks for business authorization;
- transaction-local `app.current_business_id` context for PostgreSQL policies.

These are complementary controls. RLS tenant isolation alone does not distinguish owner, admin, manager and staff capabilities.

## Initial access matrix (target policy; endpoint-specific exceptions must be documented)

| Resource | Anonymous visitor | Customer | Staff | Manager | Admin | Owner | Platform operator |
|---|---|---|---|---|---|---|---|
| Public business profile and active services | Read published fields | Read published fields | Read own tenant | Read own tenant | Read own tenant | Read own tenant | Support-only, audited |
| Customer records and contact details | None | Own record via verified flow | Read/create/update within assigned tenant | Read/create/update within tenant | Read/create/update within tenant | Full tenant management | Break-glass only, audited |
| Bookings and booking segments | Create request only through validated public flow; no arbitrary reads | Read/cancel own booking through verified flow | Read/create/update permitted operational fields | Read/create/update | Read/create/update/delete only where safe | Full tenant management | Break-glass only, audited |
| Services, employees, resources and schedules | Read published availability only | Read published availability only | Read operational data; no role/admin changes | Manage operational configuration | Manage tenant configuration | Full tenant management | Break-glass only, audited |
| Payments and payment ledger | None | Read own payment status/receipt only | Read; record only if explicitly permitted | Read/record; no provider reconciliation override | Read/record/reconcile with audit | Full tenant financial oversight | Break-glass only, audited |
| Projects and client work | None unless explicitly published | Own project status only through verified flow | Read/update assigned work | Manage tenant projects | Manage tenant projects | Full tenant management | Break-glass only, audited |
| Invitations and memberships | Accept own valid invitation only | None | None | Invite staff only if policy allows; cannot grant owner/admin | Manage non-owner memberships | Manage all tenant memberships; ownership transfer guarded | No routine access |
| Communication/WhatsApp settings and entry links | Resolve valid signed/token link only | No settings access | No integration credentials | Read limited status; no secrets | Configure if explicitly authorized | Configure and disconnect | Break-glass only, audited |
| Authentication sessions, OTPs and reset tokens | Own challenge flow only | Own sessions only | Own sessions only | Own sessions only | Own sessions only | Own sessions only | No routine access |
| Audit events | None | None | Read only if operational need and scoped | Read tenant events | Read tenant events | Read tenant events | Security audit access, audited |

**Important:** This is the intended baseline, not a claim that every permission is already implemented. In particular, customer self-service access must be verified against the actual public booking and identity flows before granting it.

## Existing protections confirmed in source

- Migration `0008_tenant_rls` enables and forces RLS on audit events, services, employees, schedulable resources, service eligibility/requirements, customers, business/employee hours, time off, bookings and booking segments.
- Later migrations add tenant RLS for projects, business communication settings, WhatsApp settings, WhatsApp entry links and payments.
- Policies compare each row's `business_id` to transaction-local `app.current_business_id`.
- FastAPI business authorization checks active membership and role in `app/modules/businesses/authorization.py`.
- The database session helper sets `app.current_business_id` with transaction-local `set_config(..., true)`.
- Existing PostgreSQL RLS integration coverage checks cross-tenant service reads and inserts using a non-bypass role.

## Findings requiring remediation or verification

### SEC-01 — Role permissions are not represented by the RLS policy
**Risk:** High. The current RLS policy enforces tenant boundaries but does not distinguish staff, manager, admin and owner actions. Fine-grained authorization currently depends on route-level checks. Every endpoint and non-HTTP execution path must be reviewed for consistent enforcement.

### SEC-02 — Privileged WhatsApp resolver is executable by PUBLIC
**Risk:** High / needs design validation. Migration `0014_whatsapp_entry_links` creates `resolve_whatsapp_entry_business(text)` as `SECURITY DEFINER`, revokes then re-grants execution to `PUBLIC`. The function has a fixed search path and accepts a token hash, but its effective exposure and output must be explicitly justified and tested. Avoid granting public database execution when only the backend needs it.

### SEC-03 — New tenant tables require a central RLS inventory
**Risk:** High. Tenant RLS is currently added incrementally in separate migrations. The audit must ensure every tenant-owned table introduced later (including payment and integration settings) is covered, and that global identity tables are deliberately handled rather than accidentally exposed.

### SEC-04 — RLS integration tests cover too few operations/resources
**Risk:** High. The current PostgreSQL test validates service SELECT isolation and cross-tenant INSERT rejection. It does not yet exercise UPDATE, DELETE, tenant reassignment, other tenant tables, missing context, connection reuse/context reset, or role-specific endpoint access.

### SEC-05 — Production database role and RLS bypass characteristics need confirmation
**Risk:** High. RLS is not a meaningful backstop if the application connects as a superuser, table owner without FORCE RLS, or a role with BYPASSRLS. Confirm the actual Render database login role and grants before claiming production enforcement.

### SEC-06 — Indirect access paths need inventory
**Risk:** Medium/High. Review database functions, views, triggers, background scripts, reporting queries, webhook handlers and external integration endpoints for access outside the normal tenant-aware request path.

## Implementation progress — 2026-11-23

- Added transaction-local authenticated user ID and normalized email context for membership discovery and invitation acceptance.
- Added forced RLS policies for `business_memberships` and `business_invitations`.
- Membership and invitation writes now require the selected tenant context; identity context is read-only for discovering the user's own memberships or invitations addressed to their verified email. This prevents self-enrolment or invitation creation in an unrelated tenant using only an identity setting.
- Restored user/tenant context after commits in business creation and invitation workflows where a subsequent refresh/read is required.
- Added PostgreSQL integration coverage for missing context, own-membership visibility, cross-tenant membership/invitation write rejection, tenant-scoped visibility, invitee email visibility, and transaction-local context reset.
- Replaced stale fixed booking-test dates with the next Monday so scheduling tests remain valid as time advances.

**Validation status:** PostgreSQL migrations and Ruff lint passed in the first CI run. The full suite reported 87 passed and 15 failures, all in pre-existing booking tests that used dates which had become past appointments. The fixture dates have now been made relative; a fresh CI run is pending. The newly added membership/invitation integration tests have not yet been confirmed green. Production DB-role verification, SECURITY DEFINER review, and route/worker access inventory remain open.

## Verification plan

Before merge:
1. Enumerate every table and classify it as global identity, tenant-owned, public-read projection or internal-only.
2. Record CRUD permissions by application role and map each route/service/worker to those permissions.
3. Confirm RLS is enabled and forced on all tenant-owned tables, with safe deny-by-default behavior when context is absent.
4. Confirm application DB role is non-superuser and NOBYPASSRLS, and is not relying on table-owner bypass.
5. Review every view and function for security-invoker/definer behavior, fixed search paths and EXECUTE grants.
6. Test allowed and denied SELECT/INSERT/UPDATE/DELETE, including cross-tenant reassignment attempts and transaction-pool context isolation.
7. Run the full API test suite and PostgreSQL integration suite against an isolated test database.
8. Review findings and migration SQL before merge. Do not run unverified security migrations against production.

## Release gate

No production migration, deployment or merge until:
- the access matrix is mapped to actual routes and database operations;
- positive and negative tests pass using non-bypass roles;
- no unresolved critical/high cross-tenant access issue remains;
- deployment/runtime database role and migration execution behavior are confirmed.
