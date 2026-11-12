# Booking lifecycle operations

## Booking state transitions

- `held` → `confirmed`: confirms a live hold and clears its expiry timestamp.
- `held` → `expired`: a hold reaches its deadline before confirmation.
- `held` or `confirmed` → `cancelled`: cancellation releases employee and resource reservations.
- Expired and cancelled segments are no longer active reservations.
- Every application transition records an audit event.

Confirmation currently does not enforce a deposit or payment requirement. Payment gating must be added when the payment module is implemented; do not interpret confirmation as proof of payment.

## Scheduled hold expiry

Run the cleanup command hourly using the API runtime environment and its restricted, non-superuser database role:

```sh
cd apps/api
uv run python -m scripts.expire_booking_holds
```

The command scans businesses, establishes transaction-local tenant context for each business, locks eligible held bookings with `SKIP LOCKED`, expires the booking and its held segments, writes an audit event, and commits per business. It is safe to run from more than one scheduler worker.

Example cron entry (adjust the absolute path and environment loading to the deployment):

```cron
0 * * * * cd /srv/bookflow-ai/apps/api && uv run python -m scripts.expire_booking_holds
```

The command is not automatically scheduled by the application. Configure it in the deployment scheduler and monitor its exit status and output before relying on expiry in production.

## Current limitations

- Rescheduling is not implemented yet.
- Cancellation policy, refund handling, and customer-initiated cancellation authorization are not implemented.
- Confirmation is a business-side state transition only; payment verification/deposit gating is pending.
- A PostgreSQL simultaneous resource-capacity test remains required before production readiness.
