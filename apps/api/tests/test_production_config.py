import json

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
        ({"GITHUB_WRITEBACK_ENABLED": True}, "workspace-scoped credentials"),
        ({"JIRA_WRITEBACK_ENABLED": True}, "workspace-scoped credentials"),
        ({"CRM_WRITEBACK_ENABLED": True}, "workspace-scoped credentials"),
        (
            {"EMAIL_FOLLOWUP_ENABLED": True},
            "email follow-up is not implemented",
        ),
        ({"WEBHOOK_WRITEBACK_ENABLED": True}, "workspace-scoped credentials"),
        ({"LLM_PROVIDER": "openai-compatible"}, "OPENAI_COMPATIBLE_API_KEY"),
    ],
)
def test_production_rejects_unsafe_configuration(
    overrides: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        production_settings(**overrides)


def test_production_rejects_unsupported_crm_provider() -> None:
    with pytest.raises(ValidationError, match="CRM provider must be hubspot"):
        production_settings(
            CRM_WRITEBACK_ENABLED=True,
            CRM_PROVIDER="salesforce",
            RAEBURN_WORKSPACE_INTEGRATIONS=json.dumps(
                {"customer-a": {"crm": {"api_key": TEST_CREDENTIAL}}}
            ),
        )


def test_production_rejects_incomplete_workspace_integration_config() -> None:
    with pytest.raises(ValidationError, match="default_repository"):
        production_settings(
            GITHUB_WRITEBACK_ENABLED=True,
            RAEBURN_WORKSPACE_INTEGRATIONS=json.dumps(
                {"customer-a": {"github": {"token": TEST_CREDENTIAL}}}
            ),
        )


def test_production_rejects_insecure_workspace_webhook() -> None:
    with pytest.raises(ValidationError, match="must use HTTPS"):
        production_settings(
            WEBHOOK_WRITEBACK_ENABLED=True,
            RAEBURN_WORKSPACE_INTEGRATIONS=json.dumps(
                {
                    "customer-a": {
                        "webhook": {
                            "url": "http://hooks.example.com/events",
                            "signing_secret": TEST_CREDENTIAL,
                        }
                    }
                }
            ),
        )


def test_production_external_llm_requires_https() -> None:
    with pytest.raises(ValidationError, match="HTTPS OPENAI_COMPATIBLE_BASE_URL"):
        production_settings(
            LLM_PROVIDER="openai-compatible",
            OPENAI_COMPATIBLE_API_KEY=TEST_CREDENTIAL,
            OPENAI_COMPATIBLE_BASE_URL="http://llm.example.com/v1",
        )


def test_production_accepts_workspace_scoped_writeback_configuration() -> None:
    integrations = {
        "customer-a": {
            "github": {
                "token": TEST_CREDENTIAL,
                "default_repository": "Raebu/example",
            },
            "jira": {
                "base_url": "https://jira.example.com",
                "email": "automation@example.com",
                "api_token": TEST_CREDENTIAL,
                "project_key": "RAE",
            },
            "crm": {"api_key": TEST_CREDENTIAL},
            "webhook": {
                "url": "https://hooks.example.com/events",
                "signing_secret": TEST_CREDENTIAL,
            },
        }
    }
    settings = production_settings(
        GITHUB_WRITEBACK_ENABLED=True,
        JIRA_WRITEBACK_ENABLED=True,
        CRM_WRITEBACK_ENABLED=True,
        WEBHOOK_WRITEBACK_ENABLED=True,
        RAEBURN_WORKSPACE_INTEGRATIONS=json.dumps(integrations),
        LLM_PROVIDER="openai-compatible",
        OPENAI_COMPATIBLE_API_KEY=TEST_CREDENTIAL,
    )

    assert settings.environment == "production"
    assert settings.crm_writeback_enabled is True
    assert settings.email_followup_enabled is False
    assert settings.integration_config("customer-a", "crm")["api_key"] == TEST_CREDENTIAL
