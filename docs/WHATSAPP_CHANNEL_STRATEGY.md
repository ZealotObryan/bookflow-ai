# BookFlow AI — WhatsApp Channel Strategy

**Status:** Approved product direction; implementation pending  
**Decision:** Support both the shared BookFlow assistant and each business's own WhatsApp channel.

## Product principle

BookFlow's database and booking API remain the system of record. WhatsApp is a communication channel, not the source of truth. Businesses must be able to use BookFlow without connecting a personal or WhatsApp Business number.

## Channel A — Shared BookFlow assistant

BookFlow operates a centrally managed WhatsApp Business Platform number. Customers enter through a business-specific link or QR code. The link carries an opaque, signed, expiring business-routing token; it must not expose internal database IDs or allow a customer to choose another tenant by editing a URL parameter.

The assistant:
1. Resolves the signed business context.
2. Identifies the customer or creates a minimal customer record after appropriate notice.
3. Explains the business's services, published prices and configured hours.
4. Collects an enquiry or booking request.
5. Checks live availability through the booking API before offering slots.
6. Creates a booking only after explicit customer confirmation and a successful backend response.
7. Notifies the business through its configured notification channel.
8. Records conversation events and the resulting booking reference in the correct tenant.

The central channel is a platform-level integration. It is not a way to read or mirror businesses' private WhatsApp conversations. It only processes messages addressed to BookFlow's own provisioned number.

## Channel B — Business-owned WhatsApp

Businesses may continue to use their own WhatsApp or WhatsApp Business app without connecting it to BookFlow.

BookFlow provides business-specific click-to-chat links and QR codes, pre-filled enquiry messages, booking and service links, manual conversation notes and follow-up tasks, and customer/booking records created through BookFlow forms or by authorised staff.

A click-to-chat link opens WhatsApp for the customer and business to converse directly. It does not grant BookFlow access to that conversation. Automatic inbox sync or message ingestion is available only after the business explicitly connects an eligible account through Meta's approved APIs and grants the required permissions.

## Optional Channel C — Connected business account

After Meta prerequisites are met, an owner/admin may connect a business-owned WhatsApp Business Account using the approved Embedded Signup flow. This is optional and independent of Channel A.

Connection states: not_connected, setup_required, pending_approval, connecting, connected, attention_required, disconnected. Never infer connection from onboarding preference or the existence of a phone number.

For existing WhatsApp Business App numbers, use the documented coexistence path only when Meta confirms eligibility. Never silently migrate a number or imply that app history and all message types will synchronise.

## Tenant isolation and routing

- Every business conversation and resulting customer/booking record is tenant-scoped.
- Shared assistant routing uses a signed opaque token with expiry and integrity protection.
- Never trust a tenant ID supplied in free-form message text or an unsigned query parameter.
- Resolve optional connected-account webhooks by verified WABA/phone-number mapping.
- A business must not see conversations, customers, contacts or metrics belonging to another business.
- Staff permissions are checked for every owner-side action.

## Consent, privacy and messaging controls

- Display a clear notice that the customer is interacting with BookFlow on behalf of the named business.
- Collect only data required for the requested enquiry or booking.
- Record the purpose, timestamp and source of consent where consent is required.
- Provide a clear opt-out route and honour it across the relevant messaging channel.
- Apply Meta's customer-service-window and approved-template rules to outbound WhatsApp messages.
- Do not use WhatsApp data for unrelated advertising, profiling or cross-business enrichment.
- Provide business-level retention and deletion processes consistent with applicable law and provider requirements.
- Keep access tokens and app secrets server-side; encrypt retained business tokens at rest.

## Business configuration

Each workspace will eventually configure whether the shared assistant accepts enquiries, its greeting and description, services and public prices, operating hours and timezone, whether bookings can be confirmed automatically or require owner approval, notification recipients, its own click-to-chat number/link, and optional official account connection.

Default for new workspaces: assistant enquiries are enabled only after the platform channel is operational; booking creation requires live availability and customer confirmation. Owner approval can be enabled per business.

## Delivery phases

1. Communication foundation: tenant-scoped preferences, channel status, settings UI and API.
2. Shared assistant: signed business entry links, conversation state, enquiry capture and owner alerts.
3. Booking actions: availability lookup, booking creation, cancellation and rescheduling through existing validated endpoints.
4. Business-owned channel tools: click-to-chat links, QR codes, prefilled messages and manual follow-up tracking.
5. Notifications and audit: delivery state, consent, opt-out, retries and message history.
6. Optional Meta account connection: Embedded Signup, webhook subscription, encrypted tokens, tenant routing and app review/Tech Provider approval.

## Non-goals and safeguards

- Do not scrape WhatsApp Web, automate a personal WhatsApp account, use unofficial clients or ask customers to forward private chats.
- Do not claim that BookFlow can read a business's direct WhatsApp inbox unless an authorised official integration is connected.
- Do not mark a booking confirmed until the booking API confirms it.
- Do not enable production messaging until a real platform-owned WhatsApp Business Platform number, approved configuration, credentials, consent controls and operational monitoring are in place.