# BookFlow Ai Development Roadmap

This roadmap is the working implementation sequence for the development branch. Features are not considered production-ready until they are implemented, tested, documented, and verified in the deployed environment. Production deployment requires explicit owner approval.

## Product foundations
- [x] Establish tenant-scoped business, identity, booking, project and WhatsApp foundations.
- [x] Add customer and service management API endpoints using existing database models.
- [ ] Verify customer/service API changes through CI and add focused endpoint tests for permissions, validation, tenant isolation and audit events.
- [ ] Connect dashboard customer and service views/forms to the API; remove browser-local demo persistence and seeded records from these views.
- [ ] Replace demo booking/calendar state with real booking API reads and validated booking actions.
- [ ] Replace illustrative dashboard metrics with real aggregates or honest empty states.
- [ ] Complete team/resource management and business operating-hours workflows.

## Security and abuse prevention
- [ ] Add Cloudflare Turnstile to public registration, password reset and public booking/enquiry entry points where risk warrants it.
- [ ] Verify Turnstile tokens server-side with Cloudflare Siteverify; reject missing, invalid, expired or replayed tokens.
- [ ] Keep secrets server-side; configure separate site and secret keys per environment. Never commit credentials.
- [ ] Combine bot protection with existing rate limiting, email verification, session security, audit logging and abuse monitoring.
- [ ] Apply risk-based protection to login rather than forcing CAPTCHA on every normal sign-in.
- [ ] Add tests for token verification failures, provider timeouts and protected endpoint behavior.
- [ ] Review public forms and API endpoints against OWASP guidance before production.

## First-time onboarding and product education
- [ ] Build a first-run welcome and setup flow that captures business category, workflow mode, currency, timezone and essential profile details.
- [ ] Create a business-specific interactive product tour for the dashboard navigation and core workflows.
- [ ] Tailor tour steps for bookings-led, tracking-led and combined businesses, including photography workflows.
- [ ] Add a persistent getting-started checklist with practical first tasks (e.g. add a service, customer, team member, project or availability).
- [ ] Save onboarding completion and tour progress to the authenticated user's/business profile on the backend, not only browser storage.
- [ ] Allow users to skip, resume and restart the tour from Help or Settings.
- [ ] Add contextual tips on first visit to complex features and a searchable Help/Guides area.
- [ ] Respect accessibility: keyboard navigation, screen readers, focus management, reduced motion and mobile layouts.
- [ ] Measure onboarding completion and task activation without collecting unnecessary personal data.

## Payments — PayChangu
- [ ] Implement PayChangu Connect merchant authorization with short-lived state, secure callback validation and encrypted token storage.
- [ ] Build tenant-scoped payment records, hosted checkout, webhook signature validation, provider verification and idempotent reconciliation.
- [ ] Support booking and project deposits, balances and full payments; keep BookFlow subscription billing separate.
- [ ] Complete test-mode end-to-end verification before any live-mode enablement.

## WhatsApp
- [ ] Complete official Meta Cloud API configuration, webhook subscription and tenant-safe message routing.
- [ ] Implement durable inbound/outbound message records, delivery status, retries, consent and opt-out controls.
- [ ] Add business-owned account connection only after Meta approvals and verified Embedded Signup.

## AI capabilities
- [ ] Introduce AI features only where they solve a clear workflow problem, with explicit tool permissions and validated backend actions.
- [ ] Use OpenAI structured outputs/tool calling where appropriate; evaluate LangGraph, MCP, RAG or other orchestration only when justified.
- [ ] Keep the API/database as source of truth; require authorization, validation and audit records for consequential actions.
- [ ] Add evaluations, safety boundaries, observability, cost controls and human handoff for AI-assisted workflows.

## Quality, performance and release readiness
- [ ] Add Playwright end-to-end coverage for onboarding, authentication, customers, services, bookings and payment journeys.
- [ ] Verify responsive layouts, accessibility, performance, error states and reduced-motion behavior.
- [ ] Run migrations and security checks against production-like PostgreSQL with a least-privilege runtime role.
- [ ] Complete operational monitoring, backup/restore and incident procedures.
- [ ] Release to production only after explicit approval.
