# Development

See the repository README for local setup. Apply database changes from `apps/api` with:

```bash
uv run alembic upgrade head
```

The API CI workflow runs Ruff, pytest and the complete migration chain against PostgreSQL.

## Tenant-owned catalogue records

The initial scheduling catalogue migration adds services, employee profiles, schedulable resources, employee eligibility, and service resource requirements. All operational catalogue rows are business-scoped. API write/read endpoints must call the business membership authorization layer and must not trust a client-supplied business ID as proof of access.

Do not enable production tenant data access until RLS is forced on these tables and the runtime database role is a non-owner, non-superuser role without BYPASSRLS. Migration credentials and application runtime credentials must be separate.
