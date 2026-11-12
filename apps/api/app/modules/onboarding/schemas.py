from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ONBOARDING_STEPS = {
    "business_profile",
    "services",
    "availability",
    "team",
    "payments",
    "whatsapp",
    "first_booking",
    "first_project",
}


class OnboardingProgressUpdate(BaseModel):
    completed_steps: list[str] = Field(max_length=8)
    dismissed: bool = False

    @field_validator("completed_steps")
    @classmethod
    def validate_steps(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Completed steps must not contain duplicates")
        unknown = set(value) - ONBOARDING_STEPS
        if unknown:
            raise ValueError("One or more onboarding steps are not recognised")
        return value


class OnboardingProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    business_id: UUID
    completed_steps: list[str]
    dismissed: bool
    updated_at: datetime
