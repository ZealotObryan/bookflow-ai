import pytest
from pydantic import ValidationError

from app.modules.onboarding.schemas import (
    ONBOARDING_STEPS,
    OnboardingProgressUpdate,
)


def test_onboarding_accepts_supported_unique_steps():
    payload = OnboardingProgressUpdate(
        completed_steps=["business_profile", "services", "first_booking"],
        dismissed=False,
    )

    assert payload.completed_steps == ["business_profile", "services", "first_booking"]


def test_onboarding_rejects_unknown_steps():
    with pytest.raises(ValidationError):
        OnboardingProgressUpdate(completed_steps=["made_up_step"])


def test_onboarding_rejects_duplicate_steps():
    with pytest.raises(ValidationError):
        OnboardingProgressUpdate(completed_steps=["services", "services"])


def test_onboarding_step_allowlist_is_bounded():
    assert len(ONBOARDING_STEPS) == 8
