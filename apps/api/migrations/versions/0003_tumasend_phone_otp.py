"""Add encrypted OTP material and TumaSend delivery references.

Revision ID: 0003_tumasend_phone_otp
Revises: 0002_authentication
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_tumasend_phone_otp"
down_revision: str | None = "0002_authentication"
branch_labels: str | Sequence[str] | None = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "phone_otp_challenges",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "phone_otp_challenges",
        sa.Column("code_ciphertext", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "phone_otp_challenges",
        sa.Column("whatsapp_batch_id", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "phone_otp_challenges",
        sa.Column("sms_batch_id", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "phone_otp_challenges",
        sa.Column("delivery_status", sa.String(length=24), server_default="pending", nullable=False),
    )
    op.create_foreign_key(
        "fk_phone_otp_challenges_user_id_users",
        "phone_otp_challenges",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_phone_otp_challenges_user_id", "phone_otp_challenges", ["user_id"])
    op.create_unique_constraint(
        "uq_phone_otp_challenges_whatsapp_batch_id",
        "phone_otp_challenges",
        ["whatsapp_batch_id"],
    )
    op.create_unique_constraint(
        "uq_phone_otp_challenges_sms_batch_id",
        "phone_otp_challenges",
        ["sms_batch_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_phone_otp_challenges_sms_batch_id", "phone_otp_challenges", type_="unique"
    )
    op.drop_constraint(
        "uq_phone_otp_challenges_whatsapp_batch_id", "phone_otp_challenges", type_="unique"
    )
    op.drop_index("ix_phone_otp_challenges_user_id", table_name="phone_otp_challenges")
    op.drop_constraint(
        "fk_phone_otp_challenges_user_id_users", "phone_otp_challenges", type_="foreignkey"
    )
    op.drop_column("phone_otp_challenges", "delivery_status")
    op.drop_column("phone_otp_challenges", "sms_batch_id")
    op.drop_column("phone_otp_challenges", "whatsapp_batch_id")
    op.drop_column("phone_otp_challenges", "code_ciphertext")
    op.drop_column("phone_otp_challenges", "user_id")
