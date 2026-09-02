from __future__ import annotations

from uuid import uuid4

from meeting_intelligence.config import Settings
from meeting_intelligence.dispatch_queue import DispatchQueue, DispatchStatus
from meeting_intelligence.integrations import DispatchResult
from meeting_intelligence.schemas import ApprovalStatus, IntegrationCommand


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "RAEBURN_ENV": "test",
        "RAEBURN_API_KEY": "test-only-api-key",
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
        "DISPATCH_MAX_ATTEMPTS": 1,
        "DISPATCH_BASE_BACKOFF_SECONDS": 1,
        "DISPATCH_LEASE_SECONDS": 10,
    }
    values.update(overrides)
    return Settings(**values)


def _command() -> IntegrationCommand:
    return IntegrationCommand(
        id=uuid4(),
        system="github",
        operation="create_task",
        payload={"action": {"title": "Ship", "description": "Ship safely"}},
        approval_status=ApprovalStatus.approved,
    )


def test_queue_is_idempotent_and_persists_terminal_success() -> None:
    queue = DispatchQueue(_settings())
    queue.bootstrap_nonproduction_schema()
    command = _command()

    assert queue.enqueue("workspace-a", "meeting-a", command) is True
    assert queue.enqueue("workspace-a", "meeting-a", command) is False

    claimed = queue.claim_next()
    assert claimed is not None
    assert claimed.id == str(command.id)
    assert claimed.status is DispatchStatus.running
    assert claimed.attempts == 1

    queue.succeed(
        claimed.id,
        DispatchResult(
            system="github",
            operation="create_task",
            status="dispatched",
            external_id="123",
        ),
    )
    jobs = queue.list_jobs("workspace-a")
    assert len(jobs) == 1
    assert jobs[0].status is DispatchStatus.succeeded
    assert jobs[0].result is not None
    assert jobs[0].result.external_id == "123"


def test_queue_dead_letters_and_supports_scoped_retry_and_cancel() -> None:
    queue = DispatchQueue(_settings())
    queue.bootstrap_nonproduction_schema()
    command = _command()
    queue.enqueue("workspace-a", "meeting-a", command)

    claimed = queue.claim_next()
    assert claimed is not None
    assert queue.fail(claimed.id, "provider unavailable") is DispatchStatus.dead_letter

    assert queue.retry_dead_letter("workspace-b", claimed.id) is False
    assert queue.retry_dead_letter("workspace-a", claimed.id) is True
    assert queue.cancel("workspace-b", claimed.id) is False
    assert queue.cancel("workspace-a", claimed.id) is True
    assert queue.list_jobs("workspace-a")[0].status is DispatchStatus.cancelled


def test_queue_rejects_unapproved_commands() -> None:
    queue = DispatchQueue(_settings())
    queue.bootstrap_nonproduction_schema()
    command = _command()
    command.approval_status = ApprovalStatus.pending

    try:
        queue.enqueue("workspace-a", "meeting-a", command)
    except ValueError as exc:
        assert "approved" in str(exc)
    else:
        raise AssertionError("unapproved command must not be queued")
