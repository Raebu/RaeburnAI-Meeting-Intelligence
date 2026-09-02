import pytest
from pydantic import ValidationError

from meeting_intelligence.config import Settings


def _credential(value: str) -> str:
    return value


BASE_PRODUCTION = {
    "RAEBURN_ENV": "production",
    "RAEBURN_API_KEY": _credential("a" * 32),
    "RAEBURN_PUBLIC_BASE_URL": "https://meeting.example.com",
    "RAEBURN_CORS_ORIGINS": "https://meeting.example.com",
    "DATABASE_URL": "postgresql+psycopg://user:pass@db/meeting_intelligence",
}
TEST_CREDENTIAL = _credential("t" * 32)


def production_settings(**overrides: object) -> Settings:
    values = BASE_PRODUCTION | overrides
    return Settings(**values)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"RAEBURN_API_KEY": _credential("short")}, "RAEBURN_API_KEY"),
        ({"DATABASE_URL": "sqlite:///unsafe.db"}, "DATABASE_URL"),
        ({"RAEBURN_CORS_ORIGINS": "*"}, "CORS origins"),
        ({"APPROVALS_REQUIRED": False}, "APPROVALS_REQUIRED"),
        ({"RAEBURN_PUBLIC_BASE_URL": "http://meeting.example.com"}, "HTTPS"),
        ({"GITHUB_WRITEBACK_ENABLED": True}, "GitHub writeback"),
        ({"JIRA_WRITEBACK_ENABLED": True}, "Jira writeback"),
        ({"CRM_WRITEBACK_ENABLED": True}, "CRM writeback is not implemented"),
        ({"EMAIL_FOLLOWUP_ENABLED": True}, "email follow-up is not implemented"),
        ({"LLM_PROVIDER": "openai-compatible"}, "OPENAI_COMPATIBLE_API_KEY"),
    ],
)
def test_production_rejects_unsafe_configuration(
    overrides: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        production_settings(**overrides)


def test_production_jira_requires_https() -> None:
    with pytest.raises(ValidationError, match="HTTPS JIRA_BASE_URL"):
        production_settings(
            JIRA_WRITEBACK_ENABLED=True,
            JIRA_BASE_URL="http://jira.example.com",
            JIRA_EMAIL="automation@example.com",
            JIRA_API_TOKEN=TEST_CREDENTIAL,
            JIRA_PROJECT_KEY="RAE",
        )


def test_production_webhook_requires_https_and_strong_signing_secret() -> None:
    with pytest.raises(ValidationError, match="HTTPS WEBHOOK_URL"):
        production_settings(
            WEBHOOK_WRITEBACK_ENABLED=True,
            WEBHOOK_URL="http://hooks.example.com/events",
            WEBHOOK_SIGNING_SECRET=TEST_CREDENTIAL,
        )

    with pytest.raises(ValidationError, match="WEBHOOK_SIGNING_SECRET"):
        production_settings(
            WEBHOOK_WRITEBACK_ENABLED=True,
            WEBHOOK_URL="https://hooks.example.com/events",
        )

    with pytest.raises(ValidationError, match="at least 32 characters"):
        production_settings(
            WEBHOOK_WRITEBACK_ENABLED=True,
            WEBHOOK_URL="https://hooks.example.com/events",
            WEBHOOK_SIGNING_SECRET=_credential("short"),
        )


def test_production_external_llm_requires_https() -> None:
    with pytest.raises(ValidationError, match="HTTPS OPENAI_COMPATIBLE_BASE_URL"):
        production_settings(
            LLM_PROVIDER="openai-compatible",
            OPENAI_COMPATIBLE_API_KEY=TEST_CREDENTIAL,
            OPENAI_COMPATIBLE_BASE_URL="http://llm.example.com/v1",
        )


def test_production_accepts_safe_supported_writeback_configuration() -> None:
    settings = production_settings(
        GITHUB_WRITEBACK_ENABLED=True,
        GITHUB_TOKEN=TEST_CREDENTIAL,
        GITHUB_DEFAULT_REPOSITORY="Raebu/example",
        JIRA_WRITEBACK_ENABLED=True,
        JIRA_BASE_URL="https://jira.example.com",
        JIRA_EMAIL="automation@example.com",
        JIRA_API_TOKEN=TEST_CREDENTIAL,
        JIRA_PROJECT_KEY="RAE",
        WEBHOOK_WRITEBACK_ENABLED=True,
        WEBHOOK_URL="https://hooks.example.com/events",
        WEBHOOK_SIGNING_SECRET=TEST_CREDENTIAL,
        LLM_PROVIDER="openai-compatible",
        OPENAI_COMPATIBLE_API_KEY=TEST_CREDENTIAL,
    )

    assert settings.environment == "production"
    assert settings.crm_writeback_enabled is False
    assert settings.email_followup_enabled is False
