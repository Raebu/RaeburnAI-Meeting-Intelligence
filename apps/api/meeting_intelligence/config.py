from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: str = Field(default="development", alias="RAEBURN_ENV")
    api_key: str = Field(alias="RAEBURN_API_KEY")
    bootstrap_workspace_id: str = Field(
        default="default", alias="RAEBURN_BOOTSTRAP_WORKSPACE_ID"
    )
    workspace_api_keys_json: str = Field(
        default="{}", alias="RAEBURN_WORKSPACE_API_KEYS"
    )
    workspace_integrations_json: str = Field(
        default="{}", alias="RAEBURN_WORKSPACE_INTEGRATIONS"
    )
    public_base_url: str = Field(
        default="http://localhost:3000", alias="RAEBURN_PUBLIC_BASE_URL"
    )
    cors_origins: str = Field(
        default="http://localhost:3000", alias="RAEBURN_CORS_ORIGINS"
    )
    rate_limit_per_minute: int = Field(
        default=60, alias="RAEBURN_RATE_LIMIT_PER_MINUTE"
    )
    rate_limit_max_clients: int = Field(
        default=10_000, ge=100, alias="RAEBURN_RATE_LIMIT_MAX_CLIENTS"
    )
    meeting_retention_seconds: int = Field(
        default=2_592_000, ge=60, alias="MEETING_RETENTION_SECONDS"
    )
    database_url: str = Field(
        default="postgresql+psycopg://raeburn:raeburn@localhost:5432/meeting_intelligence",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    dispatch_max_attempts: int = Field(
        default=5, ge=1, le=20, alias="DISPATCH_MAX_ATTEMPTS"
    )
    dispatch_base_backoff_seconds: int = Field(
        default=5, ge=1, le=3600, alias="DISPATCH_BASE_BACKOFF_SECONDS"
    )
    dispatch_lease_seconds: int = Field(
        default=120, ge=10, le=3600, alias="DISPATCH_LEASE_SECONDS"
    )
    dispatch_poll_seconds: float = Field(
        default=1.0, ge=0.1, le=60, alias="DISPATCH_POLL_SECONDS"
    )
    approvals_required: bool = Field(default=True, alias="APPROVALS_REQUIRED")
    llm_provider: str = Field(default="deterministic", alias="LLM_PROVIDER")
    openai_compatible_base_url: str = Field(
        default="https://api.openai.com/v1", alias="OPENAI_COMPATIBLE_BASE_URL"
    )
    openai_compatible_api_key: str | None = Field(
        default=None, alias="OPENAI_COMPATIBLE_API_KEY"
    )
    openai_compatible_model: str = Field(
        default="gpt-4.1-mini", alias="OPENAI_COMPATIBLE_MODEL"
    )

    github_writeback_enabled: bool = Field(
        default=False, alias="GITHUB_WRITEBACK_ENABLED"
    )
    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")
    github_default_repository: str | None = Field(
        default=None, alias="GITHUB_DEFAULT_REPOSITORY"
    )

    jira_writeback_enabled: bool = Field(default=False, alias="JIRA_WRITEBACK_ENABLED")
    jira_base_url: str | None = Field(default=None, alias="JIRA_BASE_URL")
    jira_email: str | None = Field(default=None, alias="JIRA_EMAIL")
    jira_api_token: str | None = Field(default=None, alias="JIRA_API_TOKEN")
    jira_project_key: str | None = Field(default=None, alias="JIRA_PROJECT_KEY")

    crm_writeback_enabled: bool = Field(default=False, alias="CRM_WRITEBACK_ENABLED")
    crm_provider: str = Field(default="hubspot", alias="CRM_PROVIDER")
    crm_api_key: str | None = Field(default=None, alias="CRM_API_KEY")

    email_followup_enabled: bool = Field(default=False, alias="EMAIL_FOLLOWUP_ENABLED")
    webhook_writeback_enabled: bool = Field(
        default=False, alias="WEBHOOK_WRITEBACK_ENABLED"
    )
    webhook_url: str | None = Field(default=None, alias="WEBHOOK_URL")
    webhook_signing_secret: str | None = Field(
        default=None, alias="WEBHOOK_SIGNING_SECRET"
    )

    @staticmethod
    def _parse_object(raw: str, setting_name: str) -> dict[str, Any]:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{setting_name} must be valid JSON") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{setting_name} must be a JSON object")
        return value

    @staticmethod
    def _require_strings(
        config: dict[str, Any], system: str, keys: tuple[str, ...]
    ) -> None:
        if not all(
            isinstance(config.get(key), str) and config.get(key) for key in keys
        ):
            joined = ", ".join(keys)
            raise ValueError(f"production {system} workspace config requires {joined}")

    @model_validator(mode="after")
    def validate_settings(self) -> Settings:
        if not self.bootstrap_workspace_id.strip():
            raise ValueError("RAEBURN_BOOTSTRAP_WORKSPACE_ID cannot be empty")

        workspace_keys = self._parse_object(
            self.workspace_api_keys_json, "RAEBURN_WORKSPACE_API_KEYS"
        )
        for key, value in workspace_keys.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                raise ValueError(
                    "workspace API-key entries must map strings to objects"
                )
            if self.environment == "production" and len(key) < 32:
                raise ValueError(
                    "production workspace API keys must be at least 32 characters"
                )
            required = (
                value.get("workspace_id"),
                value.get("role"),
                value.get("subject"),
            )
            if not all(isinstance(item, str) and item for item in required):
                raise ValueError(
                    "workspace API-key entries require workspace_id, role and subject"
                )
            if value.get("role") not in {"viewer", "operator", "approver", "admin"}:
                raise ValueError("unsupported workspace role")

        workspace_integrations = self._parse_object(
            self.workspace_integrations_json, "RAEBURN_WORKSPACE_INTEGRATIONS"
        )
        for workspace_id, integrations in workspace_integrations.items():
            if not isinstance(workspace_id, str) or not workspace_id.strip():
                raise ValueError("workspace integration IDs must be non-empty strings")
            if not isinstance(integrations, dict):
                raise ValueError("workspace integration entries must be JSON objects")
            for system, config in integrations.items():
                if system not in {"github", "jira", "crm", "email", "webhook"}:
                    raise ValueError(f"unsupported workspace integration: {system}")
                if not isinstance(config, dict):
                    raise ValueError(
                        "workspace integration configs must be JSON objects"
                    )

        if self.environment != "production":
            return self

        if len(self.api_key) < 32 or "change-me" in self.api_key.lower():
            raise ValueError(
                "production RAEBURN_API_KEY must be unique and at least 32 characters"
            )
        if not self.database_url.startswith("postgresql"):
            raise ValueError("production DATABASE_URL must use PostgreSQL")
        if "*" in self.cors_origin_list:
            raise ValueError("production CORS origins must be explicit")
        if not self.approvals_required:
            raise ValueError("production APPROVALS_REQUIRED must remain true")
        if not self.public_base_url.startswith("https://"):
            raise ValueError("production RAEBURN_PUBLIC_BASE_URL must use HTTPS")

        enabled_systems = {
            "github": self.github_writeback_enabled,
            "jira": self.jira_writeback_enabled,
            "crm": self.crm_writeback_enabled,
            "email": self.email_followup_enabled,
            "webhook": self.webhook_writeback_enabled,
        }
        for system, enabled in enabled_systems.items():
            if not enabled:
                continue
            configs = [
                value[system]
                for value in workspace_integrations.values()
                if isinstance(value, dict)
                and system in value
                and isinstance(value[system], dict)
            ]
            if not configs:
                raise ValueError(
                    f"production {system} writeback requires workspace-scoped credentials"
                )
            for config in configs:
                if system == "github":
                    self._require_strings(
                        config, system, ("token", "default_repository")
                    )
                elif system == "jira":
                    self._require_strings(
                        config,
                        system,
                        ("base_url", "email", "api_token", "project_key"),
                    )
                    if not str(config["base_url"]).startswith("https://"):
                        raise ValueError(
                            "production jira workspace base_url must use HTTPS"
                        )
                elif system == "crm":
                    self._require_strings(config, system, ("api_key",))
                elif system == "email":
                    self._require_strings(
                        config,
                        system,
                        ("host", "username", "password", "from_address"),
                    )
                    port = config.get("port")
                    if (
                        not isinstance(port, int)
                        or isinstance(port, bool)
                        or port < 1
                        or port > 65535
                    ):
                        raise ValueError(
                            "production email workspace port must be an integer from 1 to 65535"
                        )
                    if config.get("starttls") is not True:
                        raise ValueError(
                            "production email workspace config must require STARTTLS"
                        )
                elif system == "webhook":
                    self._require_strings(config, system, ("url", "signing_secret"))
                    if not str(config["url"]).startswith("https://"):
                        raise ValueError(
                            "production webhook workspace url must use HTTPS"
                        )
                    if len(str(config["signing_secret"])) < 32:
                        raise ValueError(
                            "production webhook signing_secret must be at least 32 characters"
                        )

        if self.crm_writeback_enabled and self.crm_provider != "hubspot":
            raise ValueError("production CRM provider must be hubspot")
        if self.llm_provider != "deterministic":
            if not self.openai_compatible_api_key:
                raise ValueError(
                    "external LLM provider requires OPENAI_COMPATIBLE_API_KEY"
                )
            if not self.openai_compatible_base_url.startswith("https://"):
                raise ValueError(
                    "production external LLM provider requires an HTTPS OPENAI_COMPATIBLE_BASE_URL"
                )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

    def integration_config(self, workspace_id: str, system: str) -> dict[str, Any]:
        workspaces = self._parse_object(
            self.workspace_integrations_json, "RAEBURN_WORKSPACE_INTEGRATIONS"
        )
        workspace = workspaces.get(workspace_id, {})
        if not isinstance(workspace, dict):
            return {}
        config = workspace.get(system, {})
        return dict(config) if isinstance(config, dict) else {}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
