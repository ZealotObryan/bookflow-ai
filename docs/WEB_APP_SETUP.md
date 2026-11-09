# BookFlow AI web application setup

## Local development
From the repository root:

\`\`\`sh
cd apps/web
cp .env.example .env.local
npm install
npm run dev
\`\`\`

Open http://localhost:3000.

## API connection
Set \`NEXT_PUBLIC_API_BASE_URL\` to the HTTPS base URL of the deployed FastAPI service. The web client appends \`/api/v1\` to this base URL.

The API must set \`FRONTEND_BASE_URL\` to the exact browser origin used by the web app. This matters for the authentication refresh endpoint, which checks the Origin header. Configure CORS to allow that exact origin and credentials.

The auth implementation keeps short-lived access tokens in React memory and relies on the API's HttpOnly refresh cookie. It does not write tokens to localStorage or sessionStorage.

## Preview and live-data boundary
The dashboard is currently an interactive preview. Sample bookings, customers and services are stored in the current browser only. The preview banner is intentional and must remain visible until the corresponding business-scoped read/write APIs are connected.

Authentication, registration, email verification, password recovery, and business creation are wired to the existing API contract, but they require a reachable API and correctly configured SMTP, database, Redis, and production secrets.

## Vercel
- Project: \`bookflow-ai\`
- Root directory: \`apps/web\`
- Node.js: \`22.x\`
- Build: \`npm run build\`
- Environment variable: \`NEXT_PUBLIC_API_BASE_URL\` (set only after the API host is provisioned)
- Current deployment strategy: build the \`development\` branch only; do not promote to production until the live data flows and security review are complete.
