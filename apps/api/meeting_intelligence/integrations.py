from __future__ import annotations

import asyncio
import hashlib
import hmac
import smtplib
import ssl
import time
from abc import ABC, abstractmethod
from collections.abc import Mapping
from email.message import EmailMessage
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


async def _patch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    **kwargs: Any,
) -> httpx.Response:
    """Retry transient PATCH failures with the same bounded policy as POST."""
    for attempt in range(_MAX_DISPATCH_ATTEMPTS):
        try:
            response = await client.patch(url, **kwargs)
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


def _config_string(config: Mapping[str, Any], key: str) -> str | None:
    value = config.get(key)
    return value if isinstance(value, str) and value else None


def _send_smtp_message(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    message: EmailMessage,
) -> None:
    """Send one message using authenticated STARTTLS SMTP."""
    context = ssl.create_default_context()
    with smtplib.SMTP(host, port, timeout=20) as client:
        client.ehlo()
        client.starttls(context=context)
        client.ehlo()
        client.login(username, password)
        client.send_message(message)


class GitHubIssueAdapter(IntegrationAdapter):
    system = "github"

    def __init__(
        self, settings: Settings, workspace_config: Mapping[str, Any] | None = None
    ) -> None:
        self.settings = settings
        self.workspace_config = workspace_config or {}

    async def dispatch(self, command: IntegrationCommand) -> DispatchResult:
        if not self.settings.github_writeback_enabled:
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="skipped",
                detail="disabled",
            )
        token = _config_string(self.workspace_config, "token")
        repository = command.payload.get("repository") or _config_string(
            self.workspace_config, "default_repository"
        )
        if self.settings.environment != "production":
            token = token or self.settings.github_token
            repository = repository or self.settings.github_default_repository
        if not repository or not token:
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="failed",
                detail="missing workspace config",
            )
        action = command.payload["action"]
        url = f"https://api.github.com/repos/{repository}/issues"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await _post_with_retry(
                client,
                url,
                headers={
                    "Authorization": f"Bearer {token}",
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

    def __init__(
        self, settings: Settings, workspace_config: Mapping[str, Any] | None = None
    ) -> None:
        self.settings = settings
        self.workspace_config = workspace_config or {}

    async def dispatch(self, command: IntegrationCommand) -> DispatchResult:
        if not self.settings.jira_writeback_enabled:
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="skipped",
                detail="disabled",
            )
        jira_base_url = _config_string(self.workspace_config, "base_url")
        jira_email = _config_string(self.workspace_config, "email")
        jira_api_token = _config_string(self.workspace_config, "api_token")
        jira_project_key = _config_string(self.workspace_config, "project_key")
        if self.settings.environment != "production":
            jira_base_url = jira_base_url or self.settings.jira_base_url
            jira_email = jira_email or self.settings.jira_email
            jira_api_token = jira_api_token or self.settings.jira_api_token
            jira_project_key = jira_project_key or self.settings.jira_project_key
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
                detail="missing workspace config",
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


class HubSpotAdapter(IntegrationAdapter):
    """Update a HubSpot deal after human approval using workspace credentials."""

    system = "crm"

    def __init__(
        self, settings: Settings, workspace_config: Mapping[str, Any] | None = None
    ) -> None:
        self.settings = settings
        self.workspace_config = workspace_config or {}

    async def dispatch(self, command: IntegrationCommand) -> DispatchResult:
        if not self.settings.crm_writeback_enabled:
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="skipped",
                detail="disabled",
            )
        token = _config_string(self.workspace_config, "api_key")
        if self.settings.environment != "production":
            token = token or self.settings.crm_api_key
        if not token:
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="failed",
                detail="missing workspace config",
            )
        if self.settings.crm_provider != "hubspot":
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="failed",
                detail="unsupported CRM provider",
            )

        deal_id = command.payload.get("deal_id")
        if not isinstance(deal_id, str) or not deal_id:
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="failed",
                detail="HubSpot deal_id is required for writeback",
            )

        summary = command.payload.get("summary")
        next_step = command.payload.get("next_step")
        properties: dict[str, str] = {}
        if isinstance(summary, str) and summary:
            properties["description"] = summary
        if isinstance(next_step, str) and next_step:
            properties["hs_next_step"] = next_step
        if not properties:
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="failed",
                detail="no supported HubSpot properties supplied",
            )

        url = f"https://api.hubapi.com/crm/v3/objects/deals/{deal_id}"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await _patch_with_retry(
                client,
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"properties": properties},
            )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        external_id = payload.get("id")
        return DispatchResult(
            system=self.system,
            operation=command.operation,
            external_id=str(external_id) if external_id is not None else deal_id,
            url=f"https://app.hubspot.com/contacts/deal/{deal_id}",
            status="dispatched",
        )


class EmailAdapter(IntegrationAdapter):
    """Send an approved meeting follow-up using workspace SMTP credentials."""

    system = "email"

    def __init__(
        self, settings: Settings, workspace_config: Mapping[str, Any] | None = None
    ) -> None:
        self.settings = settings
        self.workspace_config = workspace_config or {}

    async def dispatch(self, command: IntegrationCommand) -> DispatchResult:
        if not self.settings.email_followup_enabled:
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="skipped",
                detail="disabled",
            )

        host = _config_string(self.workspace_config, "host")
        username = _config_string(self.workspace_config, "username")
        password = _config_string(self.workspace_config, "password")
        from_address = _config_string(self.workspace_config, "from_address")
        port = self.workspace_config.get("port")
        if (
            not host
            or not username
            or not password
            or not from_address
            or not isinstance(port, int)
            or isinstance(port, bool)
            or not 1 <= port <= 65535
            or self.workspace_config.get("starttls") is not True
        ):
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="failed",
                detail="missing or unsafe workspace config",
            )

        subject = command.payload.get("subject")
        body = command.payload.get("body")
        recipients = command.payload.get("recipients")
        if not isinstance(subject, str) or not subject.strip():
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="failed",
                detail="email subject is required",
            )
        if not isinstance(body, str) or not body.strip():
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="failed",
                detail="email body is required",
            )
        if (
            not isinstance(recipients, list)
            or not recipients
            or not all(
                isinstance(recipient, str) and recipient.strip()
                for recipient in recipients
            )
        ):
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="failed",
                detail="at least one valid email recipient is required",
            )

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = from_address
        message["To"] = ", ".join(recipients)
        message.set_content(body)

        await asyncio.to_thread(
            _send_smtp_message,
            host=host,
            port=port,
            username=username,
            password=password,
            message=message,
        )
        return DispatchResult(
            system=self.system,
            operation=command.operation,
            external_id=str(command.id),
            status="dispatched",
        )


class WebhookAdapter(IntegrationAdapter):
    system = "webhook"

    def __init__(
        self, settings: Settings, workspace_config: Mapping[str, Any] | None = None
    ) -> None:
        self.settings = settings
        self.workspace_config = workspace_config or {}

    async def dispatch(self, command: IntegrationCommand) -> DispatchResult:
        if not self.settings.webhook_writeback_enabled:
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="skipped",
                detail="disabled",
            )
        webhook_url = _config_string(self.workspace_config, "url")
        signing_secret = _config_string(self.workspace_config, "signing_secret")
        if self.settings.environment != "production":
            webhook_url = webhook_url or self.settings.webhook_url
            signing_secret = signing_secret or self.settings.webhook_signing_secret
        if not webhook_url or not signing_secret:
            return DispatchResult(
                system=self.system,
                operation=command.operation,
                status="failed",
                detail="missing workspace config",
            )

        body = command.model_dump_json()
        headers = _signed_webhook_headers(
            command,
            signing_secret,
            int(time.time()),
        )
        async with httpx.AsyncClient(timeout=20) as client:
            response = await _post_with_retry(
                client,
                webhook_url,
                content=body,
                headers=headers,
            )
        response.raise_for_status()
        return DispatchResult(
            system=self.system,
            operation=command.operation,
            status="dispatched",
        )
