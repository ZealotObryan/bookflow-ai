"""Create users, businesses and memberships.

Revision ID: 0001_identity_business
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_identity_business"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("email_normalized", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email_normalized", name="uq_users_email_normalized"),
    )
    op.create_table(
        "businesses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("timezone", sa.String(length=64), server_default="Africa/Blantyre", nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="MWK", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(currency) = 3", name="ck_businesses_currency_length"),
        sa.CheckConstraint(
            "status IN ('active', 'suspended', 'closed')",
            name="ck_businesses_business_status",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_businesses"),
        sa.UniqueConstraint("slug", name="uq_businesses_slug"),
    )
    op.create_table(
        "business_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('owner', 'admin', 'manager', 'staff')", name="ck_business_memberships_membership_role"),
        sa.CheckConstraint("status IN ('invited', 'active', 'suspended')", name="ck_business_memberships_membership_status"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], name="fk_business_memberships_business_id_businesses", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_business_memberships_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_business_memberships"),
        sa.UniqueConstraint("business_id", "user_id", name="uq_business_memberships_business_user"),
    )
    op.create_index("ix_business_memberships_business_id", "business_memberships", ["business_id"])
    op.create_index("ix_business_memberships_user_id", "business_memberships", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_business_memberships_user_id", table_name="business_memberships")
    op.drop_index("ix_business_memberships_business_id", table_name="business_memberships")
    op.drop_table("business_memberships")
    op.drop_table("businesses")
    op.drop_table("users")
