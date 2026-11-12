import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.payments.schemas import ManualPaymentCreate


def test_manual_payment_requires_exactly_one_target():
    with pytest.raises(ValidationError):
        ManualPaymentCreate(amount=Decimal("100.00"))

    with pytest.raises(ValidationError):
        ManualPaymentCreate(
            booking_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            amount=Decimal("100.00"),
        )


def test_manual_payment_accepts_booking_target():
    payload = ManualPaymentCreate(
        booking_id=uuid.uuid4(),
        amount=Decimal("250.00"),
        payment_method="mobile_money",
    )
    assert payload.amount == Decimal("250.00")
    assert payload.project_id is None


def test_manual_payment_accepts_project_target():
    payload = ManualPaymentCreate(
        project_id=uuid.uuid4(),
        amount=Decimal("1250.00"),
        payment_method="bank_transfer",
    )
    assert payload.booking_id is None
    assert payload.project_id is not None
