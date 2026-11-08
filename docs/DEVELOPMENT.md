# Development

See the repository README for local setup. Apply database changes from `apps/api` with:

```bash
uv run alembic upgrade head
```

The API CI workflow runs Ruff, pytest and the complete migration chain against PostgreSQL.

## Tenant-owned catalogue records

The initial scheduling catalogue migration adds services, employee profiles, schedulable resources, employee eligibility, and service resource requirements. All operational catalogue rows are business-scoped. API write/read endpoints must call the business membership authorization layer and must not trust a client-supplied business ID as proof of access.

Do not enable production tenant data access until RLS is forced on these tables and the runtime database role is a non-owner, non-superuser role without BYPASSRLS. Migration credentials and application runtime credentials must be separate.


## PostgreSQL tenant isolation

Migration `0008_tenant_rls` enables and forces row-level security on tenant-owned operational tables. Every query against these tables must run inside a transaction after the API has resolved an active business membership and called `set_tenant_context(db, business_id)`. The helper uses PostgreSQL `set_config(..., true)`, so the tenant ID is transaction-local and is cleared automatically when the transaction ends.

The RLS policy denies reads and writes when no tenant context is set. The business membership and business root tables remain outside these policies because they are used to establish access. Business invitations are also excluded because invitation acceptance begins with a high-entropy, single-use token before the target business context is known; the endpoint additionally requires a verified matching email and locks/consumes the invitation transactionally.

**Runtime role requirement:** use a dedicated non-superuser PostgreSQL login without `BYPASSRLS`. It must not own protected tables. Migration credentials must be separate and used only by Alembic. PostgreSQL superusers bypass RLS even when FORCE is enabled, so never use the migration/superuser account for API traffic. Configure least-privilege grants for the runtime role before deploying the API.
