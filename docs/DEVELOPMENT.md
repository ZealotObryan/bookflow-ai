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

## Authentication

The API provides email/password registration and login, short-lived JWT access tokens, opaque rotating refresh tokens, session revocation, and an authenticated `/auth/me` endpoint.

- Passwords use Argon2 hashing; plaintext passwords are never stored.
- Refresh tokens are stored only as SHA-256 hashes and rotate on use.
- Access tokens are checked against server-side sessions so logout/revocation takes effect immediately.
- Phone login is available only after a user has linked and verified their phone number from an authenticated account.
- OTP codes expire after five minutes and are limited to five verification attempts.
- OTP hashes use an HMAC pepper. The temporary code is encrypted at rest so it can be re-sent through SMS if WhatsApp delivery fails.
- TumaSend is the initial messaging adapter. It sends WhatsApp first, falls back to SMS if the WhatsApp send request fails, and also falls back to SMS when a signed `message.failed` webhook is received for a queued WhatsApp message.
- A successful send API response means queued, not delivered. Delivery status is updated from signed TumaSend webhooks.
- TumaSend credentials and sender IDs are not included in the repository. Configure `TUMASEND_API_KEY`, `TUMASEND_SMS_SENDER_ID`, and `TUMASEND_WEBHOOK_SECRET` in the local environment or secret manager.
- TumaSend requires an approved business account and a sender ID for SMS. Validate WhatsApp template/policy requirements, account KYC, pricing, and real +265 delivery in sandbox/pilot testing before production.
- Email verification delivery, distributed rate limiting, and broader audit logging remain pending.

Generate a unique Fernet key for each environment:

```bash
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Set the result as `OTP_ENCRYPTION_KEY`. Also generate independent, high-entropy `JWT_SECRET_KEY` and `OTP_PEPPER` values. Never reuse the sample development values in a deployed environment.

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
