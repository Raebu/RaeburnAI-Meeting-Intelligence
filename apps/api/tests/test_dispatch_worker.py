from __future__ import annotations

from uuid import uuid4

import pytest

from meeting_intelligence import dispatch_worker
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


class FailingAdapter:
    async def dispatch(self, command: IntegrationCommand) -> DispatchResult:
        del command
        raise TimeoutError("provider unavailable")


class SuccessfulAdapter:
    async def dispatch(self, command: IntegrationCommand) -> DispatchResult:
        return DispatchResult(
            system=command.system,
            operation=command.operation,
            status="dispatched",
            external_id="provider-123",
        )


@pytest.mark.asyncio
async def test_run_once_dead_letters_provider_outage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings()
    queue = DispatchQueue(settings)
    queue.bootstrap_nonproduction_schema()
    command = _command()
    queue.enqueue("workspace-a", "meeting-a", command)
    monkeypatch.setattr(
        dispatch_worker,
        "_adapter_for",
        lambda settings, workspace_id, system: FailingAdapter(),
    )

    processed = await dispatch_worker.run_once(queue, settings)

    assert processed is True
    jobs = queue.list_jobs("workspace-a")
    assert len(jobs) == 1
    assert jobs[0].status is DispatchStatus.dead_letter
    assert jobs[0].last_error == "TimeoutError"


@pytest.mark.asyncio
async def test_run_once_persists_provider_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings()
    queue = DispatchQueue(settings)
    queue.bootstrap_nonproduction_schema()
    command = _command()
    queue.enqueue("workspace-a", "meeting-a", command)
    monkeypatch.setattr(
        dispatch_worker,
        "_adapter_for",
        lambda settings, workspace_id, system: SuccessfulAdapter(),
    )

    processed = await dispatch_worker.run_once(queue, settings)

    assert processed is True
    jobs = queue.list_jobs("workspace-a")
    assert len(jobs) == 1
    assert jobs[0].status is DispatchStatus.succeeded
    assert jobs[0].result is not None
    assert jobs[0].result.external_id == "provider-123"


@pytest.mark.asyncio
async def test_run_once_returns_false_when_queue_is_empty() -> None:
    settings = _settings()
    queue = DispatchQueue(settings)
    queue.bootstrap_nonproduction_schema()

    assert await dispatch_worker.run_once(queue, settings) is False
