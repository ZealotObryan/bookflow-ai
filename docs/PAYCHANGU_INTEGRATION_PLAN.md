# PayChangu Integration Plan

## Product decision

PayChangu is the primary payment provider for BookFlow Ai. Use **PayChangu Connect** for merchant-owned payment collection wherever the business has a PayChangu account. PayChangu explicitly recommends Connect for SaaS platforms because each business receives its funds directly and BookFlow does not custody customer funds. The merchant can revoke the connection at any time.

Official references:
- Connect guide: https://developer.paychangu.com/docs/paychangu-connect
- Connect authorization link: https://developer.paychangu.com/reference/connect-link
- Standard Checkout: https://developer.paychangu.com/docs/standard-checkout
- Webhooks: https://developer.paychangu.com/docs/webhooks
- Charge verification: https://developer.paychangu.com/docs/charge-verification

## Supported payment use cases

- Booking deposits and remaining balances
- Full booking payments
- Project deposits and milestone/final balances
- Customer payment links and receipts
- Future BookFlow subscription/plan billing (separate platform-owned merchant account and ledger)

Use MWK as the default business currency. Do not assume all businesses use the same currency; store currency on each payment.

## Ownership and money flow

- Each business connects its own PayChangu account through PayChangu Connect.
- Customer funds settle to that business's PayChangu account.
- Do not route merchant funds through a BookFlow-owned PayChangu account by default.
- Any BookFlow commission must be explicit, disclosed, and configured through PayChangu Connect's supported fee/split mechanism; do not invent a commission rate.
- Businesses without a PayChangu account can still use BookFlow's non-payment workflows. Show payments as unavailable until connected.
- A separate platform merchant account may later collect BookFlow subscription fees, not merchant customer payments.

## Security and correctness

- PayChangu credentials and merchant access tokens are backend-only; never expose them to browser code or logs.
- Encrypt merchant access tokens at rest using the existing Fernet-backed secret management pattern; require a dedicated production key.
- Use opaque state values bound to the authenticated business and short-lived connection attempts. Validate callback state before accepting any credential.
- Do not trust redirect query parameters as payment confirmation.
- Verify webhook HMAC SHA-256 signatures against the raw request body using the correct merchant webhook secret.
- Re-query PayChangu's verification endpoint before marking any payment successful or fulfilling a booking/project.
- Validate transaction reference, business, amount, currency, and terminal status; make webhook processing idempotent.
- Record provider events and payment state transitions for audit/reconciliation.
- Never store card numbers, CVVs, mobile money PINs, or other payment credentials.
- Support retries/reconciliation for pending transactions; webhook acknowledgement must be fast and durable.

## Integration sequence

1. Merchant connection: PayChangu Connect authorization link, callback state validation, encrypted token storage, connection status and revoke/disconnect.
2. Payment records: tenant-scoped payment intents and provider transaction references; link to booking or project and enforce amount/currency.
3. Checkout: initiate hosted PayChangu checkout using the connected merchant credential and return a checkout URL.
4. Webhooks: signature verification, durable event receipt, idempotency, provider-side verification, and payment state update.
5. Dashboard: real payment history, deposit/balance status, receipts and reconciliation; remove all illustrative payment totals.
6. Customer flow: booking/project payment links and clear pending/success/failed states.
7. Test mode: complete end-to-end test with PayChangu test credentials before enabling live mode.

## Current status

Planning decision only. No PayChangu account, app credentials, webhook secret, or merchant connection has been configured yet. No payment should be represented as live until the integration is tested against PayChangu and a real merchant account.
