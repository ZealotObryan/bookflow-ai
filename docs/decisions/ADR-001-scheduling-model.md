# ADR-001: Scheduling model for multi-service appointments

- **Status:** Accepted for initial domain design
- **Date:** 2026-11-07

## Context

BookFlow AI must support appointment-based businesses where a customer can book multiple services in one visit. Different service steps may be handled by different employees, and services may also require shared capacity such as a room, salon chair, bed or piece of equipment. Automatic employee assignment is not part of the first release.

A booking-level employee field is insufficient: it cannot represent different employees, different service durations or distinct resource requirements within one appointment.

## Decision

1. Model a customer appointment as a parent `booking`.
2. Model each selected service as an ordered `booking_item` with its own duration, price snapshot, time interval and optional specific employee assignment.
3. Use a common `schedulable_resources` concept for capacity that cannot be double-booked. Employee profiles link to employee capacity units; shared rooms, chairs, beds and equipment are represented as additional resource units.
4. Store time-bounded `booking_allocations` for each booking item and each required capacity unit. Temporary holds use equivalent allocation semantics and expire explicitly.
5. In the first release, require a specific eligible employee when the service needs one. Do not silently auto-assign staff.
6. Support ordered multi-service appointments and different employees across service steps. Parallel/overlapping service steps remain disabled until an explicit policy and tested user experience are agreed.

## Consequences

- Availability is calculated per service item and all its required allocations.
- Booking confirmation must revalidate every allocation in one database transaction.
- Conflict protection is resource-based, so employees and shared resources receive consistent concurrency safeguards.
- The parent booking interval is derived from its child items; it is not treated as a substitute for item-level intervals.
- Calendar synchronization can map the parent appointment and, where useful, its individual service steps.
- The model is more expressive than a single employee field, with additional schema and validation complexity.

## Rejected alternatives

- **One employee on the parent booking:** cannot represent appointments handled by multiple employees.
- **Treat shared resources as notes or labels:** cannot prevent two bookings from consuming the same chair, room or equipment at the same time.
- **Let AI choose staff or claim availability:** unsafe; all assignment and availability decisions must be validated by deterministic backend scheduling logic.
