# BookFlow AI — Product Specification

**Status:** Initial baseline  
**Product:** BookFlow AI  
**Initial market:** Malawi; designed for wider African markets

## 1. Vision

Make it easy for service businesses to manage customer relationships, bookings and everyday operations without forcing every business into the same workflow. The platform serves appointment-led businesses (salons, nail technicians, barbers, designers and tailors, event planners, photographers, fitness and wellness providers, consultants) as well as businesses that mainly need customer and work tracking. WhatsApp is a first-class conversational channel, the calendar is the operational view, and the web dashboard provides full business control.

## 2. Business types and onboarding

On first setup, a business chooses a category (salon, nail technician, barber, designer/tailor, event planner, photographer/creative, fitness/wellness, consultant/professional or other), its primary workflow (bookings, business tracking or both), and its WhatsApp priority (essential, important or not a priority yet). These are configuration hints, not hard product restrictions; a business can change its workflow as it grows.

- **Bookings:** customer-facing availability, appointments, reminders and rescheduling.
- **Business tracking:** customer directory, projects/work items, schedules, payment tracking, notes and follow-ups without requiring customer self-booking.
- **Both:** combines appointment management with the broader business workspace.

WhatsApp should be a first-class interaction channel, especially for booking-led businesses. Customers can enquire, check availability, book, reschedule and cancel through WhatsApp. Owners can use it for permitted operational questions and actions. Selecting WhatsApp priority during onboarding records preference only; it does not imply the integration is connected.

### 2.1 Photography business workflow

Photography is a first-class business category, not a generic creative-services fallback. A photography workspace should support both customer bookings and project tracking, while allowing the owner to select bookings, tracking or both.

- **Shoot types:** weddings, birthdays, portraits, graduations, family sessions, corporate events, conferences, products, commercial campaigns and other custom shoots.
- **Enquiry and quotation:** capture the client brief, shoot type, date/location, package, deliverables and quotation status.
- **Booking and payment:** confirm shoot dates, record deposits, track outstanding balances and retain agreed package/pricing details.
- **Production pipeline:** enquiry received → quotation sent → booking confirmed → deposit paid → shoot completed → editing → client review → delivered/closed.
- **Client and delivery management:** keep contact details, notes, shot/deliverable expectations, review feedback, delivery links and completion history together.
- **WhatsApp:** support enquiries, quotation follow-ups, booking confirmations, reminders, balance reminders and delivery notifications through the official integration when connected.

The pipeline is a project workflow as well as a booking workflow: a photographer who does not need public self-booking must still be able to manage shoots and client projects. WhatsApp preference remains separate from provider connection status.

## 3. Users and roles

- **Business owner:** configures the business, services, staff, policies, integrations and subscription; views reports and manages operations.
- **Manager:** manages bookings, staff schedules, customers and operational settings within assigned permissions.
- **Employee:** views assigned appointments and availability; performs permitted booking actions.
- **Customer:** enquires, books, reschedules or cancels through supported channels.
- **Platform administrator:** supports tenants, platform configuration, subscriptions and audit processes under tightly controlled access.

A user may belong to more than one business. Membership and role are scoped to a business.

## 4. Core experiences

### 4.1 WhatsApp

Use the official Meta WhatsApp Business Platform. Customer capabilities include service and price enquiries, availability enquiries, booking, rescheduling, cancellation, confirmations and reminders.

Owners should be able to ask natural-language operational questions such as today's schedule, upcoming appointments and outstanding deposits, and perform explicitly authorized actions such as blocking time.

The AI assistant is an interface, not the system of record. Every consequential action must call a validated backend operation. The backend rechecks permissions, business rules and current state before committing.

### 4.1.1 WhatsApp integration implementation

The customer messaging provider is the official Meta WhatsApp Cloud API. The existing TumaSend integration remains available for phone OTP delivery and is not treated as the business messaging integration.

The first integration foundation includes a server-side Cloud API client for text messages, strict E.164 recipient validation, bounded message length, request timeouts, provider message-ID handling and HMAC-SHA256 signature verification for future webhook delivery. Access tokens, phone-number IDs, app secrets and webhook verification tokens are server-side secrets only; they must never be exposed to the browser or committed to source control.

Next integration steps are business-level WhatsApp account connection, webhook subscription and tenant routing, durable inbound/outbound message records, approved template messaging outside the customer-service window, consent/opt-out handling, delivery status updates, retries and message audit history. Do not enable customer messaging until a Meta app, WhatsApp Business Account, phone number and production credentials have been configured and verified.

### 4.2 Calendar

Google Calendar is the first calendar integration. Confirmed bookings should sync to connected calendars; calendar events that represent unavailable time should influence availability according to configured sync rules. Support multiple employees and calendars.

PostgreSQL remains authoritative for BookFlow bookings, customer records and payment state. Calendar synchronization must be retryable and idempotent, with visible sync status and conflict handling.

### 4.3 Web dashboard

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

### 4.4 Projects and work management

Projects are a first-class workflow for businesses whose work spans multiple days or deliverables. A project belongs to one business and records a title, client contact, project type, description, due date, workflow stage, quoted amount, deposit and amount paid. The initial API supports tenant-scoped creation, listing and updates, with audit events and PostgreSQL row-level security.

Standard stages are enquiry, quoted, booked, in progress, editing, client review, delivered and cancelled. Businesses may use these stages for photography shoots, event plans, tailoring/design orders and other client work. Booking records remain separate from projects until a deliberate linking model is introduced; the project module must not silently create bookings or payment transactions.

The first dashboard release provides project creation, client/job overview, due dates, payment visibility and stage updates. Subsequent increments should add project tasks, files/delivery links, activity history, reusable templates and explicit links to bookings and verified payment records.

## 5. Booking engine — highest priority

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

## 6. Payments

Support deposits and full payments with explicit states such as pending, paid, failed, expired, refunded and under review. Evaluate PayChangu and Malipo before selecting a provider.

Provider callbacks must be authenticated, verified and idempotent. Reconcile provider transactions against internal payment records. Customer-uploaded screenshots and AI-generated messages are not acceptable proof of payment.

## 7. Notifications and automation

Support booking confirmations, reminders, cancellation/reschedule notices, deposit reminders and owner alerts. Background jobs must tolerate retries without sending duplicate messages or creating duplicate side effects.

## 8. Non-functional requirements

- Tenant isolation and least-privilege access
- Secure authentication, authorization and session management
- Reliable booking writes and recoverable integration sync
- Auditability for sensitive business actions
- Accessible, responsive and understandable user experience
- Timezone-aware scheduling; default new Malawi businesses to Africa/Blantyre
- Maintainable code, automated tests, migrations and operational documentation
- Data minimization, retention controls and secure handling of personal data

## 9. Initial scope and sequencing

The first vertical slice should establish the data model, tenant-aware authentication and a reliable booking lifecycle before adding AI automation. WhatsApp and payments are later integrations, not shortcuts around core domain rules.

## 10. Success measures to define during pilot

- Booking completion rate
- Booking creation and confirmation latency
- Double-booking and booking-correction rate
- Reminder delivery and failure rate
- Calendar synchronization success and lag
- Deposit collection and reconciliation rate
- Active businesses and repeat customer bookings

Targets will be set after baseline data from pilot businesses is available.
