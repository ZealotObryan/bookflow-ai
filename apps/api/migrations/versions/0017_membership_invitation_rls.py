"""Protect tenant membership and invitation rows using authenticated identity context.

Revision ID: 0017_membership_invitation_rls
Revises: 0016_payment_ledger
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0017_membership_invitation_rls"
down_revision: str | None = "0016_payment_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Membership reads are needed before a business context can be selected.
    # The authenticated user may therefore see their own membership rows;
    # once a tenant context is selected, tenant administrators can manage
    # membership rows within that business.
    op.execute("ALTER TABLE business_memberships ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE business_memberships FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY membership_identity_or_tenant ON business_memberships
        USING (
            user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
            OR business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
        )
        WITH CHECK (
            business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
        )
    """)

    # Invitation acceptance is token/email based and happens before the
    # business context is known. Permit the authenticated invitee to see only
    # invitations addressed to their normalized email. Inviter and tenant
    # administrators retain access within their own tenant.
    op.execute("ALTER TABLE business_invitations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE business_invitations FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY invitation_identity_or_tenant ON business_invitations
        USING (
            email_normalized = NULLIF(current_setting('app.current_user_email', true), '')
            OR invited_by_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
            OR business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
        )
        WITH CHECK (
            invited_by_user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
            OR business_id = NULLIF(current_setting('app.current_business_id', true), '')::uuid
        )
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS invitation_identity_or_tenant ON business_invitations")
    op.execute("ALTER TABLE business_invitations NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE business_invitations DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS membership_identity_or_tenant ON business_memberships")
    op.execute("ALTER TABLE business_memberships NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE business_memberships DISABLE ROW LEVEL SECURITY")
