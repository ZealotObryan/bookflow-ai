# BookFlow AI — Development Guide

## 1. Local prerequisites

Install:

- Git
- Node.js LTS and pnpm
- Python 3.12+ and uv
- Docker Engine/Desktop with Compose
- VS Code or another editor
- Postman or Bruno for API testing

Pin exact runtime and dependency versions in the project files when scaffolding begins. Do not assume the Vercel Node runtime setting is the local development version.

## 2. Repository conventions

- Keep the monorepo layout documented in the root README.
- Use feature branches for substantial work and reviewable pull requests.
- Write focused commits with imperative messages.
- Keep secrets in local environment files ignored by Git; commit only safe placeholders in `.env.example`.
- Use migrations for all schema changes.
- Add tests with each domain behavior.
- Update documentation when architecture or API behavior changes.

## 3. Local services

Docker Compose will provide local PostgreSQL and, when needed, Redis. Local development must work without production credentials. External integrations should use clearly labelled test/sandbox configurations; do not silently substitute mocks in production paths.

## 4. Quality gates

Before a change is considered complete:

- Formatting and lint checks pass.
- Static typing checks pass where configured.
- Unit and integration tests pass.
- Database migrations apply cleanly to a fresh database.
- Tenant-isolation and authorization tests cover affected operations.
- No secrets, personal customer data or provider credentials are committed.
- Relevant docs and environment examples are current.

## 5. Environment configuration

Use environment variables validated at application startup. Maintain separate local, test, preview and production configuration. Never commit real API keys, OAuth secrets, database URLs or signing secrets.

## 6. Milestone completion

Each milestone records its objective, implementation, acceptance criteria, tests, documentation, known risks and remaining work. Production deployment requires a separate review and explicit approval.
