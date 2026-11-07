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
docker compose up -d db redis
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

## Authentication security controls

- Passwords are hashed with Argon2id; raw passwords are never persisted.
- Login uses a dummy Argon2 verification for unknown email addresses and returns the same error for unknown, disabled and incorrect-password accounts.
- Authentication endpoints use Redis-backed, atomic, distributed IP and identifier rate limits. If Redis is unavailable, authentication requests fail closed with HTTP 503 rather than silently disabling throttling.
- Access JWTs are limited to ten minutes and validate the configured algorithm, issuer and audience.
- Refresh tokens are opaque, high-entropy, SHA-256 hashed in storage, rotated at use and revoked server-side.
- Reuse of a previously rotated refresh token revokes the user's remaining active sessions as a suspected token replay.
- Server-side sessions enforce a 12-hour idle timeout and a 30-day absolute lifetime.
- Password changes require the current password and revoke every active session.
- Users can revoke all sessions with `POST /api/v1/auth/logout-all`.
- Security headers prevent framing, MIME sniffing, referrer leakage and caching of API responses.
- Phone OTPs expire after five minutes, allow at most five attempts, and are protected by Redis rate limits. OTP hashes use an HMAC pepper; temporary encrypted values are cleared when a challenge is consumed or expires through the cleanup process.
- TumaSend uses separate asset-scoped WhatsApp and SMS credentials. WhatsApp is attempted first; SMS fallback uses the same code.
- TumaSend webhooks must pass HMAC signature verification before affecting delivery state.

## Local Redis

Redis is required for authentication throttling. The API deliberately fails closed if it cannot connect to Redis. Do not change this to an in-memory production fallback: it would allow limits to be bypassed across workers and restarts.

## Secrets

Generate a unique Fernet key for each environment:

```bash
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Generate independent high-entropy values for `JWT_SECRET_KEY` and `OTP_PEPPER`. Never reuse development placeholders in any shared environment. Store provider keys and secrets in a secret manager, not in Git.

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

## Security release gate

Before any production launch, complete email verification and password recovery delivery, test Redis and PostgreSQL under concurrency, verify provider webhooks against captured real payloads, configure HTTPS and trusted proxy handling, run dependency and static analysis scans, and perform an independent security review. Do not describe the system as production-ready until these checks pass.

## General security

- Never commit real `.env` files, API keys, OAuth tokens, passwords or customer data.
- Validate tenant membership and authorization in backend application services; never trust tenant IDs supplied by the browser.
- Record security-sensitive actions in audit logs.
