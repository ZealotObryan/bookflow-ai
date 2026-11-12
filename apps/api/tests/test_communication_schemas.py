import pytest
from pydantic import ValidationError

from app.modules.businesses.communication_schemas import CommunicationSettingsUpdate


def test_communication_settings_accepts_supported_modes_and_e164_numbers() -> None:
    payload = CommunicationSettingsUpdate(
        assistant_enabled=True,
        assistant_booking_policy="owner_approval",
        notification_phone="+265991234567",
        business_whatsapp_number="+265888123456",
    )
    assert payload.assistant_enabled is True
    assert payload.notification_phone == "+265991234567"


@pytest.mark.parametrize("phone", ["0991234567", "265991234567", "+123", "not-a-number"])
def test_communication_settings_rejects_non_e164_numbers(phone: str) -> None:
    with pytest.raises(ValidationError):
        CommunicationSettingsUpdate(notification_phone=phone)


def test_communication_settings_rejects_unsupported_booking_policy() -> None:
    with pytest.raises(ValidationError):
        CommunicationSettingsUpdate(assistant_booking_policy="always_confirm")
