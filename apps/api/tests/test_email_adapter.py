from __future__ import annotations

from email.message import EmailMessage
from typing import Any

import pytest

from meeting_intelligence.config import Settings
from meeting_intelligence.integrations import EmailAdapter
from meeting_intelligence.schemas import ApprovalStatus, IntegrationCommand


@pytest.mark.asyncio
async def test_email_adapter_builds_message_with_workspace_smtp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_send_smtp_message(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(
        "meeting_intelligence.integrations._send_smtp_message", fake_send_smtp_message
    )
    settings = Settings(
        RAEBURN_ENV="test",
        RAEBURN_API_KEY="test-key",
        DATABASE_URL="sqlite+pysqlite:///:memory:",
        EMAIL_FOLLOWUP_ENABLED=True,
    )
    adapter = EmailAdapter(
        settings,
        {
            "host": "smtp.example.com",
            "port": 587,
            "username": "workspace-user",
            "password": "workspace-password",
            "from_address": "meeting@example.com",
            "starttls": True,
        },
    )
    command = IntegrationCommand(
        system="email",
        operation="draft_follow_up",
        payload={
            "subject": "Meeting follow-up",
            "body": "Approved summary",
            "recipients": ["alice@example.com", "bob@example.com"],
        },
        approval_status=ApprovalStatus.approved,
    )

    result = await adapter.dispatch(command)

    assert result.status == "dispatched"
    assert captured["host"] == "smtp.example.com"
    assert captured["port"] == 587
    assert captured["username"] == "workspace-user"
    assert captured["password"] == "workspace-password"
    message = captured["message"]
    assert isinstance(message, EmailMessage)
    assert message["Subject"] == "Meeting follow-up"
    assert message["From"] == "meeting@example.com"
    assert message["To"] == "alice@example.com, bob@example.com"
    assert "Approved summary" in message.get_content()


@pytest.mark.asyncio
async def test_email_adapter_fails_closed_without_safe_workspace_config() -> None:
    settings = Settings(
        RAEBURN_ENV="test",
        RAEBURN_API_KEY="test-key",
        DATABASE_URL="sqlite+pysqlite:///:memory:",
        EMAIL_FOLLOWUP_ENABLED=True,
    )
    adapter = EmailAdapter(
        settings,
        {
            "host": "smtp.example.com",
            "port": 587,
            "username": "workspace-user",
            "password": "workspace-password",
            "from_address": "meeting@example.com",
            "starttls": False,
        },
    )
    command = IntegrationCommand(
        system="email",
        operation="draft_follow_up",
        payload={
            "subject": "Meeting follow-up",
            "body": "Approved summary",
            "recipients": ["alice@example.com"],
        },
        approval_status=ApprovalStatus.approved,
    )

    result = await adapter.dispatch(command)

    assert result.status == "failed"
    assert result.detail == "missing or unsafe workspace config"


@pytest.mark.asyncio
async def test_email_adapter_rejects_empty_recipient_list() -> None:
    settings = Settings(
        RAEBURN_ENV="test",
        RAEBURN_API_KEY="test-key",
        DATABASE_URL="sqlite+pysqlite:///:memory:",
        EMAIL_FOLLOWUP_ENABLED=True,
    )
    adapter = EmailAdapter(
        settings,
        {
            "host": "smtp.example.com",
            "port": 587,
            "username": "workspace-user",
            "password": "workspace-password",
            "from_address": "meeting@example.com",
            "starttls": True,
        },
    )
    command = IntegrationCommand(
        system="email",
        operation="draft_follow_up",
        payload={"subject": "Follow-up", "body": "Body", "recipients": []},
        approval_status=ApprovalStatus.approved,
    )

    result = await adapter.dispatch(command)

    assert result.status == "failed"
    assert result.detail == "at least one valid email recipient is required"
