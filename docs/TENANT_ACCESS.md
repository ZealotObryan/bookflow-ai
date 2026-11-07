# Tenant access and membership operations

## Roles and permissions

| Action | Owner | Admin | Manager | Staff |
|---|---:|---:|---:|---:|
| View business and member list | Yes | Yes | Yes | Yes |
| Invite administrator | Yes | No | No | No |
| Invite manager or staff | Yes | Yes | No | No |
| Assign administrator role | Yes | No | No | No |
| Assign manager or staff role | Yes | Yes | No | No |
| Suspend/reactivate non-owner member | Yes | Yes, except admins | No | No |
| Change owner membership | No, separate transfer workflow | No | No | No |

Owners cannot be suspended or demoted through the ordinary member endpoint. Ownership transfer must be a separate, explicit, audited operation. Administrators cannot manage another administrator or assign the administrator role.

## Invitation lifecycle

- Only owners and administrators may issue invitations.
- Invitations are limited to admin, manager or staff; administrator invitations are owner-only.
- The token is generated from cryptographic randomness. Only its SHA-256 hash is stored.
- Invitations expire after 72 hours and are single-use.
- Issuing a replacement revokes earlier outstanding invitations for the same business and email.
- The invitee must authenticate, verify their email, and accept using the exact invited email address.
- The raw token is delivered in the email URL fragment so it is not sent in the initial HTTP request.
- Email delivery failure rolls back the invitation transaction.
- Acceptance and membership creation/reactivation occur in one transaction.
- Audit events record invitation creation, acceptance and membership changes without storing the invitation token.

## API endpoints

- POST /api/v1/businesses/{business_id}/invitations
- POST /api/v1/businesses/invitations/accept
- GET /api/v1/businesses/{business_id}/members
- PATCH /api/v1/businesses/{business_id}/members/{membership_id}

## Remaining security gates

RLS is intentionally not activated until tenant-owned operational tables are introduced and the runtime database role can be separated from migration ownership. Every new tenant-owned query must use membership authorization and business scoping, with PostgreSQL integration tests that attempt cross-tenant reads and writes. Proxy IP trust configuration, live SMTP delivery, and invitation-link frontend handling must be verified in the deployment environment before launch.
