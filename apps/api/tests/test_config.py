import pytest
from pydantic import ValidationError

from meeting_intelligence.config import Settings


def test_production_rejects_default_api_key() -> None:
    with pytest.raises(ValidationError):
        Settings(
            RAEBURN_ENV="production",
            RAEBURN_API_KEY="change-me",
            RAEBURN_PUBLIC_BASE_URL="https://meeting.example.com",
            DATABASE_URL="postgresql+psycopg://user:pass@db/meeting",
            APPROVALS_REQUIRED=True,
        )


def test_production_requires_human_approvals() -> None:
    with pytest.raises(ValidationError):
        Settings(
            RAEBURN_ENV="production",
            RAEBURN_API_KEY="x" * 40,
            RAEBURN_PUBLIC_BASE_URL="https://meeting.example.com",
            DATABASE_URL="postgresql+psycopg://user:pass@db/meeting",
            APPROVALS_REQUIRED=False,
        )


def test_safe_production_baseline_is_accepted() -> None:
    settings = Settings(
        RAEBURN_ENV="production",
        RAEBURN_API_KEY="x" * 40,
        RAEBURN_PUBLIC_BASE_URL="https://meeting.example.com",
        RAEBURN_CORS_ORIGINS="https://consulting.theraeburngroup.com",
        DATABASE_URL="postgresql+psycopg://user:pass@db/meeting",
        APPROVALS_REQUIRED=True,
    )
    assert settings.environment == "production"
