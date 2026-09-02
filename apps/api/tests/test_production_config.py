import pytest
from pydantic import ValidationError

from meeting_intelligence.config import Settings


BASE_PRODUCTION = {
    "RAEBURN_ENV": "production",
    "RAEBURN_API_KEY": "a" * 32,
    "RAEBURN_PUBLIC_BASE_URL": "https://meeting.example.com",
    "RAEBURN_CORS_ORIGINS": "https://meeting.example.com",
    "DATABASE_URL": "postgresql+psycopg://user:pass@db/meeting_intelligence",
}


def production_settings(**overrides: object) -> Settings:
    values = BASE_PRODUCTION | overrides
    return Settings(**values)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"RAEBURN_API_KEY": "short"}, "RAEBURN_API_KEY"),
        ({"DATABASE_URL": "sqlite:///unsafe.db"}, "DATABASE_URL"),
        ({"RAEBURN_CORS_ORIGINS": "*"}, "CORS origins"),
        ({"APPROVALS_REQUIRED": False}, "APPROVALS_REQUIRED"),
        ({"RAEBURN_PUBLIC_BASE_URL": "http://meeting.example.com"}, "HTTPS"),
        ({"GITHUB_WRITEBACK_ENABLED": True}, "GitHub writeback"),
        ({"JIRA_WRITEBACK_ENABLED": True}, "Jira writeback"),
        ({"CRM_WRITEBACK_ENABLED": True}, "CRM_API_KEY"),
        ({"LLM_PROVIDER": "openai-compatible"}, "OPENAI_COMPATIBLE_API_KEY"),
    ],
)
def test_production_rejects_unsafe_configuration(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        production_settings(**overrides)


def test_production_webhook_requires_https_and_signing_secret() -> None:
    with pytest.raises(ValidationError, match="HTTPS WEBHOOK_URL"):
        production_settings(
            WEBHOOK_WRITEBACK_ENABLED=True,
            WEBHOOK_URL="http://hooks.example.com/events",
            WEBHOOK_SIGNING_SECRET="secret",
        )

    with pytest.raises(ValidationError, match="WEBHOOK_SIGNING_SECRET"):
        production_settings(
            WEBHOOK_WRITEBACK_ENABLED=True,
            WEBHOOK_URL="https://hooks.example.com/events",
        )


def test_production_accepts_safe_writeback_configuration() -> None:
    settings = production_settings(
        GITHUB_WRITEBACK_ENABLED=True,
        GITHUB_TOKEN="github-token",
        GITHUB_DEFAULT_REPOSITORY="Raebu/example",
        JIRA_WRITEBACK_ENABLED=True,
        JIRA_BASE_URL="https://jira.example.com",
        JIRA_EMAIL="automation@example.com",
        JIRA_API_TOKEN="jira-token",
        JIRA_PROJECT_KEY="RAE",
        CRM_WRITEBACK_ENABLED=True,
        CRM_API_KEY="crm-token",
        WEBHOOK_WRITEBACK_ENABLED=True,
        WEBHOOK_URL="https://hooks.example.com/events",
        WEBHOOK_SIGNING_SECRET="webhook-secret",
        LLM_PROVIDER="openai-compatible",
        OPENAI_COMPATIBLE_API_KEY="llm-token",
    )

    assert settings.environment == "production"
