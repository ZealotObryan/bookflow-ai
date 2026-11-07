# BookFlow AI data model

## Identity and tenancy

Users may belong to multiple businesses through business memberships. Businesses own their operational records. Every tenant-owned operational table carries a `business_id`; APIs must resolve an active membership before querying or mutating those records.

## Service and resource catalogue

- **Services** belong to one business and define display name, optional description, duration in minutes, before/after buffers, price amount, and active/inactive status. Prices use a fixed two-decimal numeric representation; the business currency remains the currency of record.
- **Employees** are business-scoped staff profiles. A profile can optionally link to a BookFlow user account, but an employee does not need a login to be schedulable. Employee profiles have a business-unique optional code and active/inactive status.
- **Schedulable resources** represent rooms, chairs, beds, equipment, or other capacity-constrained assets. Capacity is explicit and must be positive.
- **Service employee eligibility** records which employees may perform each service. It uses composite foreign keys containing `business_id`, preventing an employee from another business being assigned to a service.
- **Service resource requirements** records which resource types/assets a service consumes and the required quantity. Composite foreign keys enforce same-business references.

The schema intentionally does not automatically assign employees. Booking requests will require an eligible employee where a service requires one. A future booking can contain multiple service segments, allowing sequential services with one employee or parallel/sequential segments handled by different employees.

## Scheduling invariants to implement in the booking engine

1. A booking request is checked against business hours, employee schedules, breaks, service duration, buffers, and resource capacity.
2. A booking may contain multiple service segments. Each segment references a service and, where required, an explicitly selected eligible employee.
3. Resource requirements are evaluated for every segment and resource capacity is enforced for overlapping intervals.
4. PostgreSQL transactions, row-level locking and exclusion/constraint strategies must prevent concurrent requests from double-booking employees or resources.
5. Tenant context is transaction-local and database RLS must be forced for operational tenant tables before release.


## Booking and availability foundation

- Customers are scoped to a business and are not global contacts by default.
- Business and employee weekly hours use the business's configured timezone for interpreting local wall-clock hours. Store actual booking and time-off instants as timezone-aware timestamps.
- Employee time off is an explicit UTC interval.
- A booking is the customer-facing appointment container. A booking may contain multiple ordered service segments, each with its own service, employee, start/end time and immutable service/price snapshots.
- Composite foreign keys prevent a booking or segment from referencing a customer, service, employee or booking in another tenant.
- A PostgreSQL GiST exclusion constraint prevents overlapping active segments assigned to the same employee, including concurrent booking attempts.
- Resource capacity greater than one must be checked while holding a row lock on the resource in the booking transaction. A booking is not considered confirmed until all segment, employee and resource checks commit atomically.
- Holds expire through a scheduled cleanup process. Expired holds must be transitioned to expired/cancelled segment states before their employee reservations are released.
