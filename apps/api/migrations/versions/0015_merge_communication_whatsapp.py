"""Merge business communication and WhatsApp migration heads.

Revision ID: 0015_merge_comm_whatsapp
Revises: 0013_business_communication, 0014_whatsapp_entry_links
"""

from collections.abc import Sequence

revision: str = "0015_merge_comm_whatsapp"
down_revision: tuple[str, str] = (
    "0013_business_communication",
    "0014_whatsapp_entry_links",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
