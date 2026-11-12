"""Merge booking engine and business profile migration heads.

Revision ID: 0011_merge_heads
Revises: 0010_booking_resource_allocations, 0009_business_profile
Create Date: 2026-11-09
"""

revision = "0011_merge_heads"
down_revision = ("0010_booking_resources", "0009_business_profile")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Both parent branches contain independent schema changes.
    pass


def downgrade() -> None:
    # The merge itself has no schema changes to reverse.
    pass
