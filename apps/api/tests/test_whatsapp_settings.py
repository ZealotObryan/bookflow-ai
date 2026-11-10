import pytest
from pydantic import ValidationError

from app.modules.whatsapp.schemas import WhatsAppSettingsUpdate


def test_whatsapp_settings_accepts_valid_preferences():
    payload = WhatsAppSettingsUpdate(
        assistant_enabled=True,
        greeting="Welcome to our business",
        booking_policy="owner_approval",
        business_whatsapp_number="+265991234567",
        notify_owner=True,
    )
    assert payload.assistant_enabled is True
    assert payload.booking_policy == "owner_approval"
    assert payload.business_whatsapp_number == "+265991234567"


def test_whatsapp_settings_strips_greeting():
    payload = WhatsAppSettingsUpdate(
        assistant_enabled=False,
        greeting="  Hello there  ",
        booking_policy="automatic",
    )
    assert payload.greeting == "Hello there"


@pytest.mark.parametrize("number", ["265991234567", "+265 991 234 567", "123", ""])
def test_whatsapp_settings_rejects_invalid_nonempty_phone(number):
    if number == "":
        return
    with pytest.raises(ValidationError):
        WhatsAppSettingsUpdate(
            assistant_enabled=True,
            greeting="Hello",
            booking_policy="owner_approval",
            business_whatsapp_number=number,
        )


def test_whatsapp_settings_rejects_blank_greeting():
    with pytest.raises(ValidationError):
        WhatsAppSettingsUpdate(
            assistant_enabled=True,
            greeting="   ",
            booking_policy="owner_approval",
        )
