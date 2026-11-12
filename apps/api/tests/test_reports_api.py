from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Business, Project
from app.modules.reports import router as reports_module


def test_business_report_returns_scoped_project_payment_totals(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        business = Business(name="Report Studio", slug=f"report-{uuid4().hex[:8]}")
        db.add(business)
        db.flush()
        db.add(
            Project(
                business_id=business.id,
                title="Wedding photography",
                client_name="Alex Customer",
                project_type="photography",
                status="in_progress",
                quoted_amount=Decimal("100000.00"),
                deposit_amount=Decimal("30000.00"),
                amount_paid=Decimal("40000.00"),
                currency="MWK",
            )
        )
        db.commit()

        monkeypatch.setattr(
            reports_module,
            "require_membership",
            lambda business_id, user, session: (business, None),
        )
        monkeypatch.setattr(
            reports_module,
            "set_tenant_context",
            lambda session, tenant_id: None,
        )

        result = reports_module.get_business_report(
            business_id=business.id,
            period="7d",
            user=object(),
            db=db,
        )

        assert result.business_id == business.id
        assert result.currency == "MWK"
        assert result.bookings_total == 0
        assert result.project_count == 1
        assert result.project_quoted_value == Decimal("100000.00")
        assert result.project_amount_recorded_paid == Decimal("40000.00")
        assert result.project_outstanding_value == Decimal("60000.00")
        assert len(result.daily_activity) == 7
    engine.dispose()
