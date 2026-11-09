from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.projects.schemas import ProjectCreate, ProjectUpdate


def test_project_create_accepts_work_tracking_fields() -> None:
    project = ProjectCreate(
        title="Wedding photography",
        client_name="Amina Banda",
        project_type="wedding",
        status="booked",
        quoted_amount=Decimal("500000"),
        deposit_amount=Decimal("150000"),
        amount_paid=Decimal("150000"),
    )

    assert project.status == "booked"
    assert project.deposit_amount == Decimal("150000")


def test_project_create_rejects_deposit_above_quote() -> None:
    with pytest.raises(ValidationError):
        ProjectCreate(
            title="Portrait session",
            client_name="Ruth Phiri",
            quoted_amount=Decimal("10000"),
            deposit_amount=Decimal("12000"),
        )


def test_project_update_validates_provided_financial_values() -> None:
    with pytest.raises(ValidationError):
        ProjectUpdate(quoted_amount=Decimal("10000"), amount_paid=Decimal("12000"))
