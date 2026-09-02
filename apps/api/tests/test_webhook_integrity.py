import hashlib
import hmac
from uuid import UUID

from meeting_intelligence.config import Settings
from meeting_intelligence.integrations import WebhookAdapter, _signed_webhook_headers
from meeting_intelligence.schemas import IntegrationCommand


def _command() -> IntegrationCommand:
    return IntegrationCommand(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        system="webhook",
        operation="notify",
        payload={"message": "approved"},
    )


def test_signed_webhook_headers_are_stable_and_verifiable() -> None:
    command = _command()
    timestamp = 1_725_000_000
    headers = _signed_webhook_headers(command, "test-secret", timestamp)

    body = command.model_dump_json()
    expected = hmac.new(
        b"test-secret",
        f"{timestamp}.{body}".encode(),
        hashlib.sha256,
    ).hexdigest()

    assert headers["Idempotency-Key"] == str(command.id)
    assert headers["X-Raeburn-Webhook-Timestamp"] == str(timestamp)
    assert headers["X-Raeburn-Webhook-Signature"] == f"sha256={expected}"
    assert headers["Content-Type"] == "application/json"


def test_signature_changes_with_timestamp() -> None:
    command = _command()
    first = _signed_webhook_headers(command, "test-secret", 1_725_000_000)
    second = _signed_webhook_headers(command, "test-secret", 1_725_000_001)

    assert first["X-Raeburn-Webhook-Signature"] != second["X-Raeburn-Webhook-Signature"]


async def test_enabled_webhook_fails_closed_without_signing_secret() -> None:
    settings = Settings(
        RAEBURN_API_KEY="test-key",
        WEBHOOK_WRITEBACK_ENABLED=True,
        WEBHOOK_URL="https://example.invalid/webhook",
    )
    result = await WebhookAdapter(settings).dispatch(_command())

    assert result.status == "failed"
    assert result.detail == "missing workspace config"
