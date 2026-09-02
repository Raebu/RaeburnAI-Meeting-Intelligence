from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: str = Field(default="development", alias="RAEBURN_ENV")
    api_key: str = Field(alias="RAEBURN_API_KEY")
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

    @model_validator(mode="after")
    def validate_production_guardrails(self) -> "Settings":
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

        if self.github_writeback_enabled and (
            not self.github_token or not self.github_default_repository
        ):
            raise ValueError(
                "GitHub writeback requires GITHUB_TOKEN and GITHUB_DEFAULT_REPOSITORY"
            )
        if self.jira_writeback_enabled and not all(
            [
                self.jira_base_url,
                self.jira_email,
                self.jira_api_token,
                self.jira_project_key,
            ]
        ):
            raise ValueError(
                "Jira writeback requires base URL, email, API token and project key"
            )
        if self.crm_writeback_enabled and not self.crm_api_key:
            raise ValueError("CRM writeback requires CRM_API_KEY")
        if self.webhook_writeback_enabled:
            if not self.webhook_url or not self.webhook_url.startswith("https://"):
                raise ValueError(
                    "production webhook writeback requires an HTTPS WEBHOOK_URL"
                )
            if not self.webhook_signing_secret:
                raise ValueError(
                    "production webhook writeback requires WEBHOOK_SIGNING_SECRET"
                )
        if self.llm_provider != "deterministic" and not self.openai_compatible_api_key:
            raise ValueError(
                "external LLM provider requires OPENAI_COMPATIBLE_API_KEY"
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
