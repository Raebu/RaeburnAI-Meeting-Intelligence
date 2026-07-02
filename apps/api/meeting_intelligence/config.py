from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="development", alias="RAEBURN_ENV")
    api_key: str = Field(default="change-me", alias="RAEBURN_API_KEY")
    public_base_url: str = Field(default="http://localhost:3000", alias="RAEBURN_PUBLIC_BASE_URL")
    cors_origins: str = Field(default="http://localhost:3000", alias="RAEBURN_CORS_ORIGINS")
    rate_limit_per_minute: int = Field(default=60, alias="RAEBURN_RATE_LIMIT_PER_MINUTE")
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
    openai_compatible_api_key: str | None = Field(default=None, alias="OPENAI_COMPATIBLE_API_KEY")
    openai_compatible_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_COMPATIBLE_MODEL")

    github_writeback_enabled: bool = Field(default=False, alias="GITHUB_WRITEBACK_ENABLED")
    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")
    github_default_repository: str | None = Field(default=None, alias="GITHUB_DEFAULT_REPOSITORY")

    jira_writeback_enabled: bool = Field(default=False, alias="JIRA_WRITEBACK_ENABLED")
    jira_base_url: str | None = Field(default=None, alias="JIRA_BASE_URL")
    jira_email: str | None = Field(default=None, alias="JIRA_EMAIL")
    jira_api_token: str | None = Field(default=None, alias="JIRA_API_TOKEN")
    jira_project_key: str | None = Field(default=None, alias="JIRA_PROJECT_KEY")

    crm_writeback_enabled: bool = Field(default=False, alias="CRM_WRITEBACK_ENABLED")
    crm_provider: str = Field(default="hubspot", alias="CRM_PROVIDER")
    crm_api_key: str | None = Field(default=None, alias="CRM_API_KEY")

    email_followup_enabled: bool = Field(default=False, alias="EMAIL_FOLLOWUP_ENABLED")
    webhook_writeback_enabled: bool = Field(default=False, alias="WEBHOOK_WRITEBACK_ENABLED")
    webhook_url: str | None = Field(default=None, alias="WEBHOOK_URL")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
