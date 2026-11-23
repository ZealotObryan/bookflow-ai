from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL", "").startswith("postgresql"),
    reason="PostgreSQL RLS integration test",
)
def test_tenant_rls_is_enforced_for_non_bypass_runtime_role() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    role = f"bookflow_rls_test_{uuid.uuid4().hex[:10]}"
    first_business = uuid.uuid4()
    second_business = uuid.uuid4()
    first_service = uuid.uuid4()
    second_service = uuid.uuid4()

    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE ROLE "{role}" NOLOGIN NOBYPASSRLS'))
            connection.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role}"'))
            connection.execute(text(f'GRANT SELECT, INSERT ON services TO "{role}"'))
            connection.execute(
                text(
                    "INSERT INTO businesses (id, name, slug, timezone, currency, status) "
                    "VALUES (:id, :name, :slug, 'Africa/Blantyre', 'MWK', 'active')"
                ),
                [
                    {"id": first_business, "name": "RLS One", "slug": f"rls-one-{first_business.hex[:8]}"},
                    {"id": second_business, "name": "RLS Two", "slug": f"rls-two-{second_business.hex[:8]}"},
                ],
            )
            connection.execute(
                text(
                    "INSERT INTO services "
                    "(id, business_id, name, duration_minutes, buffer_before_minutes, "
                    "buffer_after_minutes, price_amount, status) "
                    "VALUES (:id, :business_id, 'Consultation', 30, 0, 0, 1000, 'active')"
                ),
                [
                    {"id": first_service, "business_id": first_business},
                    {"id": second_service, "business_id": second_business},
                ],
            )

        with engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(text(f'SET ROLE "{role}"'))
            hidden_count = connection.scalar(text("SELECT count(*) FROM services"))
            assert hidden_count == 0

            connection.execute(
                text("SELECT set_config('app.current_business_id', :business_id, true)"),
                {"business_id": str(first_business)},
            )
            visible_ids = set(connection.scalars(text("SELECT id FROM services")).all())
            assert visible_ids == {first_service}
            transaction.rollback()

        with engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(text(f'SET ROLE "{role}"'))
            connection.execute(
                text("SELECT set_config('app.current_business_id', :business_id, true)"),
                {"business_id": str(first_business)},
            )
            with pytest.raises(DBAPIError):
                connection.execute(
                    text(
                        "INSERT INTO services "
                        "(id, business_id, name, duration_minutes, buffer_before_minutes, "
                        "buffer_after_minutes, price_amount, status) "
                        "VALUES (:id, :business_id, 'Cross tenant', 30, 0, 0, 1000, 'active')"
                    ),
                    {"id": uuid.uuid4(), "business_id": second_business},
                )
            transaction.rollback()
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP OWNED BY "{role}"'))
            connection.execute(text(f'DROP ROLE IF EXISTS "{role}"'))
            connection.execute(
                text("DELETE FROM businesses WHERE id IN (:first, :second)"),
                {"first": first_business, "second": second_business},
            )
        engine.dispose()



@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL", "").startswith("postgresql"),
    reason="PostgreSQL RLS integration test",
)
def test_membership_and_invitation_rls_identity_and_tenant_boundaries() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    role = f"bookflow_membership_rls_{uuid.uuid4().hex[:8]}"
    owner_id, invitee_id, outsider_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    first_business, second_business = uuid.uuid4(), uuid.uuid4()
    membership_id, invitation_id = uuid.uuid4(), uuid.uuid4()
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE ROLE "{role}" NOLOGIN NOBYPASSRLS'))
            connection.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role}"'))
            connection.execute(text(f'GRANT SELECT, INSERT, UPDATE, DELETE ON business_memberships TO "{role}"'))
            connection.execute(text(f'GRANT SELECT, INSERT, UPDATE, DELETE ON business_invitations TO "{role}"'))
            connection.execute(text(f'GRANT SELECT ON businesses, users TO "{role}"'))
            connection.execute(
                text("INSERT INTO users (id, email, email_normalized, full_name) VALUES "
                     "(:owner, 'owner@example.com', 'owner@example.com', 'Owner'), "
                     "(:invitee, 'invitee@example.com', 'invitee@example.com', 'Invitee'), "
                     "(:outsider, 'outsider@example.com', 'outsider@example.com', 'Outsider')"),
                {"owner": owner_id, "invitee": invitee_id, "outsider": outsider_id},
            )
            connection.execute(
                text("INSERT INTO businesses (id, name, slug) VALUES "
                     "(:first, 'First Studio', :first_slug), (:second, 'Second Studio', :second_slug)"),
                {"first": first_business, "second": second_business,
                 "first_slug": f"first-{first_business.hex[:8]}",
                 "second_slug": f"second-{second_business.hex[:8]}"},
            )
            connection.execute(
                text("INSERT INTO business_memberships "
                     "(id, business_id, user_id, role, status) "
                     "VALUES (:id, :business, :owner, 'owner', 'active')"),
                {"id": membership_id, "business": first_business, "owner": owner_id},
            )
            connection.execute(
                text("INSERT INTO business_invitations "
                     "(id, business_id, invited_by_user_id, email_normalized, role, token_hash, expires_at) "
                     "VALUES (:id, :business, :owner, 'invitee@example.com', 'staff', :token, now() + interval '1 hour')"),
                {"id": invitation_id, "business": first_business, "owner": owner_id,
                 "token": uuid.uuid4().hex * 2},
            )

        # No identity or tenant context must reveal no tenant-owned rows.
        with engine.connect() as connection:
            tx = connection.begin()
            connection.execute(text(f'SET ROLE "{role}"'))
            assert connection.scalar(text("SELECT count(*) FROM business_memberships")) == 0
            assert connection.scalar(text("SELECT count(*) FROM business_invitations")) == 0
            tx.rollback()

        # A user can discover their own memberships, but cannot self-enrol in
        # an unrelated business merely by supplying their own user_id.
        with engine.connect() as connection:
            tx = connection.begin()
            connection.execute(text(f'SET ROLE "{role}"'))
            connection.execute(
                text("SELECT set_config('app.current_user_id', :user_id, true)"),
                {"user_id": str(owner_id)},
            )
            assert connection.scalar(text("SELECT count(*) FROM business_memberships")) == 1
            with pytest.raises(DBAPIError):
                connection.execute(
                    text("INSERT INTO business_memberships "
                         "(id, business_id, user_id, role, status) "
                         "VALUES (:id, :business, :user, 'staff', 'active')"),
                    {"id": uuid.uuid4(), "business": second_business, "user": owner_id},
                )
            tx.rollback()

        # Tenant context reveals only rows belonging to that tenant.
        with engine.connect() as connection:
            tx = connection.begin()
            connection.execute(text(f'SET ROLE "{role}"'))
            connection.execute(
                text("SELECT set_config('app.current_business_id', :business_id, true)"),
                {"business_id": str(first_business)},
            )
            assert connection.scalar(text("SELECT count(*) FROM business_memberships")) == 1
            assert connection.scalar(text("SELECT count(*) FROM business_invitations")) == 1
            tx.rollback()

        # An invitee can resolve only invitations addressed to their verified
        # identity before the tenant context is selected.
        with engine.connect() as connection:
            tx = connection.begin()
            connection.execute(text(f'SET ROLE "{role}"'))
            connection.execute(
                text("SELECT set_config('app.current_user_email', :email, true)"),
                {"email": "invitee@example.com"},
            )
            visible = connection.scalars(text("SELECT id FROM business_invitations")).all()
            assert visible == [invitation_id]
            tx.rollback()

        # Transaction-local identity and tenant settings must not leak when
        # the pooled connection is reused by a new transaction.
        with engine.connect() as connection:
            tx = connection.begin()
            connection.execute(text(f'SET ROLE "{role}"'))
            connection.execute(
                text("SELECT set_config('app.current_business_id', :business_id, true)"),
                {"business_id": str(first_business)},
            )
            tx.commit()
            next_tx = connection.begin()
            assert connection.scalar(text("SELECT count(*) FROM business_memberships")) == 0
            next_tx.rollback()
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP OWNED BY "{role}"'))
            connection.execute(text(f'DROP ROLE IF EXISTS "{role}"'))
            connection.execute(
                text("DELETE FROM businesses WHERE id IN (:first, :second)"),
                {"first": first_business, "second": second_business},
            )
            connection.execute(
                text("DELETE FROM users WHERE id IN (:owner, :invitee, :outsider)"),
                {"owner": owner_id, "invitee": invitee_id, "outsider": outsider_id},
            )
        engine.dispose()
