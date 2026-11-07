# BookFlow AI — Initial Data Model

**Status:** Conceptual model, not a migration or final schema.

## 1. Design rules

- PostgreSQL is the source of truth for BookFlow business data.
- Use UUID primary keys for application entities.
- Tenant-owned records carry `business_id`; enforce tenant-aware foreign keys and authorization.
- Store timestamps in UTC (`timestamptz`) and retain an IANA timezone on each business (default `Africa/Blantyre`).
- Store money as integer minor units with an ISO 4217 currency code; do not use floating-point types.
- Use explicit status enums/check constraints and record lifecycle timestamps.
- Add created/updated timestamps and audit sensitive state transitions.
- Design idempotency for booking writes and external webhook processing.

## 2. Core entities

### Identity and tenancy

- `users`: login identity and profile.
- `businesses`: tenant, display name, timezone, locale, currency and status.
- `business_memberships`: user-to-business relationship, role and membership status.
- `roles/permissions`: initially a small, explicit role model; expand only when real permission needs emerge.

### Business setup

- `business_hours`: recurring operating windows by weekday.
- `services`: name, description, duration, price, currency, active state and booking policy.
- `employees`: staff profile and business membership/assignment.
- `employee_services`: services an employee can perform.
- `employee_availability`: recurring and date-specific working windows.
- `blocked_times`: breaks, leave, maintenance and other unavailable periods.

### Customers and bookings

- `customers`: tenant-scoped customer profile and contact identifiers.
- `booking_holds`: temporary resource reservations with expiry.
- `bookings`: customer, status, start/end, timezone snapshot, source, notes and idempotency reference.
- `booking_items`: services, assigned employee/resource, sequence, duration and price snapshot.
- `booking_status_history`: actor, transition, timestamp and reason.

### Payments and external systems

- `payments`: internal amount, currency, status, purpose and provider reference.
- `payment_events`: verified provider events and processing status.
- `calendar_connections`: OAuth connection metadata and encrypted token references.
- `calendar_event_mappings`: internal booking/resource to external event identifiers and sync state.
- `whatsapp_accounts` and `conversations`: business channel configuration and minimal conversation metadata.
- `webhook_inbox`: provider event identity, payload reference, verification and processing status.
- `notification_jobs`: scheduled message intent, delivery state and idempotency key.
- `audit_logs`: actor, tenant, action, target and safe metadata.

Subscription and platform billing entities will be added before paid self-service launch.

## 3. Important relationships

- A user may have many business memberships; a business has many members.
- A business owns services, employees, customers, schedules, bookings and payments.
- A booking belongs to one business and customer and contains one or more booking items.
- Each booking item references a service and, where applicable, an assigned employee/resource.
- A payment belongs to a business and is associated with a booking or other explicit payment purpose.
- External calendar events map to internal records; they do not replace them.

## 4. Constraints and indexes to design

- Unique normalized user login identifier.
- Unique membership per (business, user).
- Tenant-aware foreign keys for all tenant-owned relationships.
- Index bookings by (business_id, start_at), status and customer.
- Index employee schedule/resource allocations by tenant, resource and time range.
- Unique provider event ID within provider/account scope.
- Unique idempotency key within tenant and operation scope.
- Check constraints for positive durations and non-negative money amounts.

PostgreSQL range/exclusion constraints may be used to prevent overlapping active allocations for a single employee/resource. The final constraint must correctly model holds, confirmed bookings, buffers, multi-service bookings and cancellation. Do not ship a simplistic overlap constraint that rejects valid sequential services or misses concurrent writes.

## 5. Decisions still required before migrations

1. Whether employee assignment is mandatory for every service or whether shared resources (rooms, chairs, equipment) are first-class schedulable resources.
2. Whether multi-service bookings are sequential under one employee, parallel across employees, or both.
3. How business-level capacity and group bookings are represented.
4. Exact deposit, expiry and cancellation policy semantics.
5. RLS rollout and transaction-scoped tenant context strategy.

These decisions will be resolved with concrete booking scenarios and tests before the first production schema migration.
