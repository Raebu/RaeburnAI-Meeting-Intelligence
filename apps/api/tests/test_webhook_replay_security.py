from __future__ import annotations

import hashlib
import hmac

from meeting_intelligence.config import Settings
from meeting_intelligence.webhook_security import (
    WebhookReplayStore,
    verify_inbound_signature,
)


def _test_secret(value: str) -> str:
    return value


def _signature(secret: str, timestamp: int, body: bytes) -> str:
    digest = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256
    ).hexdigest()
    return f"sha256={digest}"


def test_inbound_signature_accepts_valid_recent_payload() -> None:
    secret = _test_secret("test-signing-secret")
    timestamp = 1_800_000_000
    body = b'{"event":"meeting.updated"}'

    assert verify_inbound_signature(
        body=body,
        signing_secret=secret,
        timestamp=str(timestamp),
        signature=_signature(secret, timestamp, body),
        now=timestamp + 30,
    )


def test_inbound_signature_rejects_stale_tampered_and_malformed_payloads() -> None:
    secret = _test_secret("test-signing-secret")
    timestamp = 1_800_000_000
    body = b'{"event":"meeting.updated"}'
    signature = _signature(secret, timestamp, body)

    assert not verify_inbound_signature(
        body=body,
        signing_secret=secret,
        timestamp=str(timestamp),
        signature=signature,
        now=timestamp + 301,
    )
    assert not verify_inbound_signature(
        body=b'{"event":"tampered"}',
        signing_secret=secret,
        timestamp=str(timestamp),
        signature=signature,
        now=timestamp,
    )
    assert not verify_inbound_signature(
        body=body,
        signing_secret=secret,
        timestamp="not-a-timestamp",
        signature=signature,
        now=timestamp,
    )
    assert not verify_inbound_signature(
        body=body,
        signing_secret=secret,
        timestamp=str(timestamp),
        signature="invalid",
        now=timestamp,
    )


def test_replay_store_records_event_only_once_per_workspace() -> None:
    settings = Settings(
        RAEBURN_ENV="test",
        RAEBURN_API_KEY="test-key",
        DATABASE_URL="sqlite+pysqlite:///:memory:",
    )
    store = WebhookReplayStore(settings)
    store.bootstrap_nonproduction_schema()
    body = b'{"event":"meeting.updated"}'

    assert store.record_once("workspace-a", "event-1", body) is True
    assert store.record_once("workspace-a", "event-1", body) is False
    assert store.record_once("workspace-b", "event-1", body) is True
    assert store.ready() is True
