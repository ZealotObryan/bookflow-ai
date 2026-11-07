# BookFlow AI — Product Specification

**Status:** Initial baseline  
**Product:** BookFlow AI  
**Initial market:** Malawi; designed for wider African markets

## 1. Vision

Make it easy for appointment-based businesses to accept, manage and grow bookings without requiring customers or owners to learn a complicated system. WhatsApp is the conversational front door, the calendar is the operational view, and the web dashboard provides full business control.

## 2. Users and roles

- **Business owner:** configures the business, services, staff, policies, integrations and subscription; views reports and manages operations.
- **Manager:** manages bookings, staff schedules, customers and operational settings within assigned permissions.
- **Employee:** views assigned appointments and availability; performs permitted booking actions.
- **Customer:** enquires, books, reschedules or cancels through supported channels.
- **Platform administrator:** supports tenants, platform configuration, subscriptions and audit processes under tightly controlled access.

A user may belong to more than one business. Membership and role are scoped to a business.

## 3. Core experiences

### 3.1 WhatsApp

Use the official Meta WhatsApp Business Platform. Customer capabilities include service and price enquiries, availability enquiries, booking, rescheduling, cancellation, confirmations and reminders.

Owners should be able to ask natural-language operational questions such as today's schedule, upcoming appointments and outstanding deposits, and perform explicitly authorized actions such as blocking time.

The AI assistant is an interface, not the system of record. Every consequential action must call a validated backend operation. The backend rechecks permissions, business rules and current state before committing.

### 3.2 Calendar

Google Calendar is the first calendar integration. Confirmed bookings should sync to connected calendars; calendar events that represent unavailable time should influence availability according to configured sync rules. Support multiple employees and calendars.

PostgreSQL remains authoritative for BookFlow bookings, customer records and payment state. Calendar synchronization must be retryable and idempotent, with visible sync status and conflict handling.

### 3.3 Web dashboard

Responsive dashboard capabilities:

- Registration, sign-in and business onboarding
- Business profile, location, timezone and operating hours
- Services, durations, prices, buffers and deposit policies
- Employees, roles and individual schedules
- Booking list, booking details and calendar
- Customer records and booking history
- Payment tracking and reconciliation
- Integrations, notifications and automation settings
- Analytics, operational reports and subscription management

## 4. Booking engine — highest priority

The booking engine must support:

- Business operating hours, employee schedules and service-specific durations
- Breaks, blocked time, buffers and lead-time rules
- One or more services in a booking, with explicit sequencing rules
- Availability search and temporary booking holds
- Confirmation, cancellation and rescheduling
- Deposit/full-payment policies and booking expiry
- Double-booking prevention under concurrent requests
- Audit history and clear booking state transitions

Availability displayed to a customer is provisional until a hold or booking is successfully committed. All booking writes must use database transactions and appropriate constraints/locking. The API returns the committed result; the AI must never invent a slot or claim a booking succeeded before the backend confirms it.

## 5. Payments

Support deposits and full payments with explicit states such as pending, paid, failed, expired, refunded and under review. Evaluate PayChangu and Malipo before selecting a provider.

Provider callbacks must be authenticated, verified and idempotent. Reconcile provider transactions against internal payment records. Customer-uploaded screenshots and AI-generated messages are not acceptable proof of payment.

## 6. Notifications and automation

Support booking confirmations, reminders, cancellation/reschedule notices, deposit reminders and owner alerts. Background jobs must tolerate retries without sending duplicate messages or creating duplicate side effects.

## 7. Non-functional requirements

- Tenant isolation and least-privilege access
- Secure authentication, authorization and session management
- Reliable booking writes and recoverable integration sync
- Auditability for sensitive business actions
- Accessible, responsive and understandable user experience
- Timezone-aware scheduling; default new Malawi businesses to Africa/Blantyre
- Maintainable code, automated tests, migrations and operational documentation
- Data minimization, retention controls and secure handling of personal data

## 8. Initial scope and sequencing

The first vertical slice should establish the data model, tenant-aware authentication and a reliable booking lifecycle before adding AI automation. WhatsApp and payments are later integrations, not shortcuts around core domain rules.

## 9. Success measures to define during pilot

- Booking completion rate
- Booking creation and confirmation latency
- Double-booking and booking-correction rate
- Reminder delivery and failure rate
- Calendar synchronization success and lag
- Deposit collection and reconciliation rate
- Active businesses and repeat customer bookings

Targets will be set after baseline data from pilot businesses is available.
