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
