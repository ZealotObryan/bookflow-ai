"""Persist flexible business onboarding profile.

Revision ID: 0009_business_profile
Revises: 0008_tenant_rls
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_business_profile"
down_revision: str | None = "0008_tenant_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column("business_type", sa.String(40), server_default="other", nullable=False),
    )
    op.add_column(
        "businesses",
        sa.Column("workflow_mode", sa.String(20), server_default="both", nullable=False),
    )
    op.add_column(
        "businesses",
        sa.Column("whatsapp_priority", sa.String(20), server_default="important", nullable=False),
    )
    op.create_check_constraint(
        "ck_businesses_business_type",
        "businesses",
        "business_type IN ('salon', 'nail_tech', 'barber', 'designer_tailor', "
        "'event_planner', 'photographer', 'fitness_wellness', 'consultant', 'other')",
    )
    op.create_check_constraint(
        "ck_businesses_workflow_mode",
        "businesses",
        "workflow_mode IN ('bookings', 'tracking', 'both')",
    )
    op.create_check_constraint(
        "ck_businesses_whatsapp_priority",
        "businesses",
        "whatsapp_priority IN ('essential', 'important', 'not_now')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_businesses_whatsapp_priority", "businesses", type_="check")
    op.drop_constraint("ck_businesses_workflow_mode", "businesses", type_="check")
    op.drop_constraint("ck_businesses_business_type", "businesses", type_="check")
    op.drop_column("businesses", "whatsapp_priority")
    op.drop_column("businesses", "workflow_mode")
    op.drop_column("businesses", "business_type")
