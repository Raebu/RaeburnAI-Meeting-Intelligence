from __future__ import annotations

import asyncio
import hashlib
import hmac
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel

from meeting_intelligence.config import Settings
from meeting_intelligence.schemas import IntegrationCommand

_RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}
_MAX_DISPATCH_ATTEMPTS = 3


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


async def _post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    **kwargs: Any,
) -> httpx.Response:
    """Retry transient outbound failures without retrying permanent client errors."""
    for attempt in range(_MAX_DISPATCH_ATTEMPTS):
        try:
            response = await client.post(url, **kwargs)
        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt == _MAX_DISPATCH_ATTEMPTS - 1:
                raise
        else:
            if (
                response.status_code not in _RETRYABLE_STATUS_CODES
                or attempt == _MAX_DISPATCH_ATTEMPTS - 1
            ):
                return response

        await asyncio.sleep(0.25 * (2**attempt))

    raise RuntimeError("integration dispatch retry loop exhausted unexpectedly")


def _signed_webhook_headers(
    command: IntegrationCommand, signing_secret: str, timestamp: int
) -> dict[str, str]:
    body = command.model_dump_json()
    message = f"{timestamp}.{body}".encode()
    signature = hmac.new(signing_secret.encode(), message, hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "Idempotency-Key": str(command.id),
        "X-Raeburn-Webhook-Timestamp": str(timestamp),
        "X-Raeburn-Webhook-Signature": f"sha256={signature}",
    }


class GitHubIssueAdapter(IntegrationAdapter):
    system = "github"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def dispatch(self, command: IntegrationCommand) -> DispatchResult:
        if not self.settings.github_writeback_enabled:
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="skipped",
                detail="disabled",
            )
        repository = (
            command.payload.get("repository") or self.settings.github_default_repository
        )
        if not repository or not self.settings.github_token:
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="failed",
                detail="missing config",
            )
        action = command.payload["action"]
        url = f"https://api.github.com/repos/{repository}/issues"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await _post_with_retry(
                client,
                url,
                headers={
                    "Authorization": f"Bearer {self.settings.github_token}",
                    "Accept": "application/vnd.github+json",
                },
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
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="skipped",
                detail="disabled",
            )
        jira_base_url = self.settings.jira_base_url
        jira_email = self.settings.jira_email
        jira_api_token = self.settings.jira_api_token
        jira_project_key = self.settings.jira_project_key
        if (
            not jira_base_url
            or not jira_email
            or not jira_api_token
            or not jira_project_key
        ):
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="failed",
                detail="missing config",
            )
        action = command.payload["action"]
        async with httpx.AsyncClient(timeout=20) as client:
            response = await _post_with_retry(
                client,
                f"{jira_base_url}/rest/api/3/issue",
                auth=(jira_email, jira_api_token),
                json={
                    "fields": {
                        "project": {"key": jira_project_key},
                        "summary": action["title"],
                        "description": {
                            "type": "doc",
                            "version": 1,
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": action["description"],
                                        }
                                    ],
                                }
                            ],
                        },
                        "issuetype": {"name": "Task"},
                    }
                },
            )
        response.raise_for_status()
        payload = response.json()
        return DispatchResult(
            system=self.system,
            operation=command.operation,
            external_id=payload.get("key"),
            status="dispatched",
        )


class WebhookAdapter(IntegrationAdapter):
    system = "webhook"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def dispatch(self, command: IntegrationCommand) -> DispatchResult:
        if not self.settings.webhook_writeback_enabled:
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="skipped",
                detail="disabled",
            )
        if not self.settings.webhook_url or not self.settings.webhook_signing_secret:
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="failed",
                detail="missing config",
            )

        body = command.model_dump_json()
        headers = _signed_webhook_headers(
            command,
            self.settings.webhook_signing_secret,
            int(time.time()),
        )
        async with httpx.AsyncClient(timeout=20) as client:
            response = await _post_with_retry(
                client,
                self.settings.webhook_url,
                content=body,
                headers=headers,
            )
        response.raise_for_status()
        return DispatchResult(
            system=self.system,
            operation=command.operation,
            status="dispatched",
        )
