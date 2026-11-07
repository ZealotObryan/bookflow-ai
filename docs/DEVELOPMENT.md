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
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

## Authentication security controls

- Passwords use Argon2id. Raw passwords are never persisted.
- Registration requires email verification before password login is permitted.
- Email verification and password-reset tokens are random, single-use, time-limited, and stored only as SHA-256 hashes.
- Password reset responses do not disclose whether an email exists; successful resets revoke all active sessions and outstanding reset tokens.
- Login performs a dummy Argon2 verification for unknown accounts and uses the same failure response for unknown, disabled, unverified and incorrect-password accounts.
- Authentication endpoints use Redis-backed, atomic, distributed IP and identifier rate limits. If Redis is unavailable, authentication requests fail closed with HTTP 503.
- Access JWTs expire after ten minutes and validate the configured algorithm, issuer and audience.
- Refresh tokens are opaque, high-entropy, SHA-256 hashed in storage, rotated at use and revoked server-side. Reuse of a rotated token revokes all active sessions for that account.
- Server-side sessions enforce a 12-hour idle timeout and a 30-day absolute lifetime.
- Password changes require the current password and revoke all sessions. Users can also revoke all sessions explicitly.
- Security headers prevent framing, MIME sniffing, referrer leakage and caching of API responses.
- Phone OTPs expire after five minutes, allow at most five attempts, and are protected by distributed rate limits. OTP hashes use an HMAC pepper; encrypted fallback values are cleared after delivery/consumption or by scheduled cleanup.

## Transactional email

The API uses a provider-neutral SMTP adapter with STARTTLS or implicit TLS. Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, and `FRONTEND_BASE_URL`. Production configuration rejects missing email credentials, insecure Redis/PostgreSQL transport, HTTP frontend URLs, and placeholder secrets.

Email verification and reset links place their token in the URL fragment so the token is not sent in the initial HTTP request to the frontend. The frontend must read the fragment, submit the token to the API, immediately clear the fragment from browser history, and avoid third-party scripts/analytics on verification and reset pages. Apply a strict Referrer-Policy of `no-referrer` to those pages.

## Local Redis

Redis is required for authentication throttling. The API deliberately fails closed if it cannot connect. Do not change this to an in-memory production fallback.

## Scheduled cleanup

Run the authentication cleanup command hourly using the hosting platform's scheduler:

```bash
cd apps/api && uv run python -m scripts.cleanup_auth
```

It clears expired encrypted OTP fallback values, removes old expired verification/reset tokens and OTP challenges, and removes revoked/expired sessions after the retention period. The scheduler itself must be configured and monitored before production.

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
uv run alembic upgrade head
```

GitHub Actions runs lint, unit tests and PostgreSQL migration checks for API changes on the development branch and pull requests.

## Security release gate

Before production launch, complete frontend verification/reset pages, test Redis and PostgreSQL under concurrency, verify provider webhooks against captured real payloads, configure HTTPS and trusted proxy handling, run dependency/static analysis scans, and perform an independent security review. Do not describe the system as production-ready until these checks pass.

## General security

- Never commit real `.env` files, API keys, OAuth tokens, passwords or customer data.
- Validate tenant membership and authorization in backend application services; never trust tenant IDs supplied by the browser.
- Record security-sensitive actions in audit logs.
