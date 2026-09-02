from __future__ import annotations

from email.message import EmailMessage
from typing import Any
from uuid import uuid4

import pytest

from meeting_intelligence import integrations
from meeting_intelligence.config import Settings
from meeting_intelligence.integrations import EmailAdapter
from meeting_intelligence.schemas import ApprovalStatus, IntegrationCommand


class FakeSMTP:
    instances: list["FakeSMTP"] = []

    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in: tuple[str, str] | None = None
        self.message: EmailMessage | None = None
        self.__class__.instances.append(self)

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def ehlo(self) -> None:
        return None

    def starttls(self, *, context: Any) -> None:
        assert context is not None
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.logged_in = (username, password)

    def send_message(self, message: EmailMessage) -> None:
        self.message = message


def _settings(*, enabled: bool = True) -> Settings:
    return Settings(
        RAEBURN_ENV="test",
        RAEBURN_API_KEY="test-only-api-key",
        DATABASE_URL="sqlite+pysqlite:///:memory:",
        EMAIL_FOLLOWUP_ENABLED=enabled,
    )


def _command(*, recipients: list[str] | None = None) -> IntegrationCommand:
    return IntegrationCommand(
        id=uuid4(),
        system="email",
        operation="draft_follow_up",
        approval_status=ApprovalStatus.approved,
        payload={
            "subject": "Approved follow-up",
            "body": "This message was approved before dispatch.",
            "recipients": recipients or ["recipient@example.com"],
        },
    )


@pytest.mark.asyncio
async def test_email_adapter_uses_authenticated_starttls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    FakeSMTP.instances.clear()
    monkeypatch.setattr(integrations.smtplib, "SMTP", FakeSMTP)
    adapter = EmailAdapter(
        _settings(),
        {
            "host": "smtp.example.com",
            "port": 587,
            "username": "mailer@example.com",
            "password": "test-password",
            "from_address": "mailer@example.com",
            "starttls": True,
        },
    )
    command = _command()

    result = await adapter.dispatch(command)

    assert result.status == "dispatched"
    assert result.external_id
    assert len(FakeSMTP.instances) == 1
    client = FakeSMTP.instances[0]
    assert (client.host, client.port, client.timeout) == ("smtp.example.com", 587, 20)
    assert client.started_tls is True
    assert client.logged_in == ("mailer@example.com", "test-password")
    assert client.message is not None
    assert client.message["To"] == "recipient@example.com"
    assert client.message["From"] == "mailer@example.com"
    assert client.message["X-Raeburn-Command-ID"] == str(command.id)


@pytest.mark.asyncio
async def test_email_adapter_rejects_header_injection_before_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_smtp(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("SMTP must not be opened for invalid recipients")

    monkeypatch.setattr(integrations.smtplib, "SMTP", unexpected_smtp)
    adapter = EmailAdapter(
        _settings(),
        {
            "host": "smtp.example.com",
            "port": 587,
            "username": "mailer@example.com",
            "password": "test-password",
            "from_address": "mailer@example.com",
            "starttls": True,
        },
    )

    result = await adapter.dispatch(_command(recipients=["victim@example.com\nBcc:x@example.com"]))

    assert result.status == "failed"
    assert result.detail == "valid recipients are required"


@pytest.mark.asyncio
async def test_email_adapter_fails_closed_without_workspace_credentials() -> None:
    result = await EmailAdapter(_settings(), {}).dispatch(_command())

    assert result.status == "failed"
    assert result.detail == "missing workspace config"


@pytest.mark.asyncio
async def test_email_adapter_respects_global_disable() -> None:
    result = await EmailAdapter(_settings(enabled=False), {}).dispatch(_command())

    assert result.status == "skipped"
    assert result.detail == "disabled"
