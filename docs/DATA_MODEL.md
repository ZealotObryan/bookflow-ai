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
- `roles/permissions`: initially a small, explicit role model.

### Business setup and scheduling
- `business_hours`: recurring operating windows by weekday.
- `services`: name, description, duration, price, currency, active state, booking policy and resource requirements.
- `employees`: staff profile and business assignment.
- `employee_services`: services an employee can perform.
- `employee_availability`: recurring and date-specific working windows.
- `schedulable_resources`: bookable capacity units, including employee capacity and shared resources such as rooms, chairs, beds and equipment. Resource type, capacity and active state are explicit.
- `employee_resource_links`: links an employee profile to its schedulable capacity unit.
- `resource_availability`: recurring and date-specific availability for shared resources.
- `blocked_times`: breaks, leave, maintenance and other unavailable periods.
- `service_resource_requirements`: resource types or specific resources required by a service, including quantity where applicable.

### Customers and bookings
- `customers`: tenant-scoped customer profile and contact identifiers.
- `bookings`: customer, status, overall start/end, timezone snapshot, source, notes and idempotency reference.
- `booking_items`: one service step per line, with sequence, service, assigned employee where required, start/end and price/duration snapshots.
- `booking_allocations`: time-bounded allocation of schedulable resources to a booking item; supports employees and shared resources under the same conflict model.
- `booking_holds`: temporary allocations with expiry, created before confirmation when required.
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

## 3. Scheduling decisions confirmed

1. **No automatic employee assignment in the initial release.** Where a service requires an employee, the booking flow must collect or select a specific eligible employee. Automatic assignment is a later enhancement.
2. **Multi-service appointments are supported.** A booking is the parent appointment and contains booking items, each representing a service step. Items may be handled by different employees and may run sequentially or simultaneously. Each item has its own start/end interval; the parent booking spans the earliest item start to the latest item end.
3. **Shared resources are first-class schedulable capacity.** Rooms, chairs, beds and equipment can be required and allocated to service items. Employee and shared-resource conflicts use a common allocation model.
4. **Availability is evaluated for every required allocation.** A service is not bookable unless its required employee capacity and shared-resource requirements can all be allocated for the requested interval.

Parallel/overlapping service steps are supported when the business allows them and all required employee and shared-resource allocations are available for each item's interval. The booking flow must make overlapping steps and the total appointment span clear to the customer.

## 4. Important relationships

- A user may have many business memberships; a business has many members.
- A business owns services, employees, schedulable resources, customers, schedules, bookings and payments.
- An employee profile links to a schedulable capacity unit and may be eligible for many services.
- A booking belongs to one business and customer and contains one or more ordered booking items.
- Each booking item references one service and may reference a specific employee.
- Booking allocations connect booking items to all required employee/shared resources for their exact time intervals.
- A payment belongs to a business and is associated with a booking or other explicit payment purpose.
- External calendar events map to internal records; they do not replace them.

## 5. Constraints and indexes to design

- Unique normalized user login identifier.
- Unique membership per (business, user).
- Tenant-aware foreign keys for all tenant-owned relationships.
- Index bookings by (business_id, start_at), status and customer.
- Index allocations by tenant, resource and time range.
- Unique provider event ID within provider/account scope.
- Unique idempotency key within tenant and operation scope.
- Check constraints for positive durations, valid intervals and non-negative money amounts.
- Enforce employee service eligibility and resource requirement compatibility in the booking application service and, where practical, database constraints.

PostgreSQL range/exclusion constraints may be used to prevent overlapping active allocations for a single schedulable resource. The final constraint must correctly model holds, confirmed bookings, buffers, multi-service bookings and cancellation. Do not ship a simplistic overlap constraint that rejects valid sequential services or misses concurrent writes.

## 6. Remaining decisions before migrations

1. How business-level capacity and group bookings are represented.
2. Exact deposit, expiry and cancellation policy semantics.
3. RLS rollout and transaction-scoped tenant context strategy.
4. Whether resource requirements can be satisfied by any resource in a type/pool or must name a specific resource.

Resolve these with concrete booking scenarios and tests before the first production schema migration.
