# Development Workflow

## Branching and deployment safety

- `main` is the protected release branch.
- Feature work is committed to `development` or short-lived feature branches.
- Do not merge into `main`, enable production deployment, or change production resources without explicit approval.
- Vercel automatic builds are currently paused while the application foundation is being established.
- Use pull requests for review before release.

## Local prerequisites

- Node.js 22 or newer and npm 10 or newer
- Python 3.12 or newer
- uv
- Docker Engine/Desktop with Compose

## Start local dependencies

From the repository root:

```bash
cp .env.example .env
docker compose up -d db
```

## Start the web app

```bash
cd apps/web
npm install
npm run dev
```

## Start the API

```bash
cd apps/api
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

## Quality checks

From `apps/api`:

```bash
uv run pytest
uv run ruff check .
```

From `apps/web`:

```bash
npm run lint
npm run typecheck
npm run build
```

## Database changes

- Update SQLAlchemy models first.
- Generate or author an Alembic migration and review it before applying.
- Test upgrade and downgrade behavior against PostgreSQL.
- Never edit an already-applied migration; add a new migration instead.
- Keep tenant-aware foreign keys, uniqueness and conflict constraints in the database wherever appropriate.

## Security

- Never commit real `.env` files, API keys, OAuth tokens, passwords or customer data.
- Keep secrets in local environment variables or a managed secret store.
- Validate tenant membership and authorization in backend application services; never trust tenant IDs supplied by the browser.
- Record security-sensitive actions in audit logs.
