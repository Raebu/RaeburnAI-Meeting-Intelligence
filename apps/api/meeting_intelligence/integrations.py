from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel

from meeting_intelligence.config import Settings
from meeting_intelligence.schemas import IntegrationCommand


class DispatchResult(BaseModel):
    system: str
    operation: str
    external_id: str | None = None
    url: str | None = None
    status: str
    detail: str | None = None


class IntegrationAdapter(ABC):
    system: str

    @abstractmethod
    async def dispatch(self, command: IntegrationCommand) -> DispatchResult:
        raise NotImplementedError


class GitHubIssueAdapter(IntegrationAdapter):
    system = "github"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def dispatch(self, command: IntegrationCommand) -> DispatchResult:
        if not self.settings.github_writeback_enabled:
            return DispatchResult(system=self.system, operation=command.operation, status="skipped", detail="disabled")
        repository = command.payload.get("repository") or self.settings.github_default_repository
        if not repository or not self.settings.github_token:
            return DispatchResult(system=self.system, operation=command.operation, status="failed", detail="missing config")
        action = command.payload["action"]
        url = f"https://api.github.com/repos/{repository}/issues"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {self.settings.github_token}", "Accept": "application/vnd.github+json"},
                json={"title": action["title"], "body": action["description"]},
            )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return DispatchResult(
            system=self.system,
            operation=command.operation,
            external_id=str(payload.get("number")),
            url=payload.get("html_url"),
            status="dispatched",
        )


class JiraAdapter(IntegrationAdapter):
    system = "jira"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def dispatch(self, command: IntegrationCommand) -> DispatchResult:
        if not self.settings.jira_writeback_enabled:
            return DispatchResult(system=self.system, operation=command.operation, status="skipped", detail="disabled")
        if not all([self.settings.jira_base_url, self.settings.jira_email, self.settings.jira_api_token, self.settings.jira_project_key]):
            return DispatchResult(system=self.system, operation=command.operation, status="failed", detail="missing config")
        action = command.payload["action"]
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.settings.jira_base_url}/rest/api/3/issue",
                auth=(self.settings.jira_email, self.settings.jira_api_token),
                json={
                    "fields": {
                        "project": {"key": self.settings.jira_project_key},
                        "summary": action["title"],
                        "description": {
                            "type": "doc",
                            "version": 1,
                            "content": [{"type": "paragraph", "content": [{"type": "text", "text": action["description"]}]}],
                        },
                        "issuetype": {"name": "Task"},
                    }
                },
            )
        response.raise_for_status()
        payload = response.json()
        return DispatchResult(system=self.system, operation=command.operation, external_id=payload.get("key"), status="dispatched")


class WebhookAdapter(IntegrationAdapter):
    system = "webhook"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def dispatch(self, command: IntegrationCommand) -> DispatchResult:
        if not self.settings.webhook_writeback_enabled or not self.settings.webhook_url:
            return DispatchResult(system=self.system, operation=command.operation, status="skipped", detail="disabled")
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(self.settings.webhook_url, json=command.model_dump(mode="json"))
        response.raise_for_status()
        return DispatchResult(system=self.system, operation=command.operation, status="dispatched")
