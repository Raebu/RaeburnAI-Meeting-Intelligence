from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from meeting_intelligence.config import Settings
from meeting_intelligence.dispatch_queue import (
    DispatchJobRecord,
    DispatchQueue,
    DispatchStatus,
)
from meeting_intelligence.integrations import DispatchResult
from meeting_intelligence.schemas import ApprovalStatus, IntegrationCommand


def _settings(database_path: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "RAEBURN_ENV": "test",
        "RAEBURN_API_KEY": "test-only-api-key",
        "DATABASE_URL": f"sqlite+pysqlite:///{database_path}",
        "DISPATCH_MAX_ATTEMPTS": 2,
        "DISPATCH_BASE_BACKOFF_SECONDS": 1,
        "DISPATCH_LEASE_SECONDS": 10,
    }
    values.update(overrides)
    return Settings(**values)


def _command(index: int) -> IntegrationCommand:
    return IntegrationCommand(
        id=uuid4(),
        system="github",
        operation="create_task",
        payload={
            "action": {
                "title": f"Load item {index}",
                "description": "Queue resilience verification",
            }
        },
        approval_status=ApprovalStatus.approved,
    )


def test_queue_drains_large_batch_without_loss_or_duplication(tmp_path: Path) -> None:
    queue = DispatchQueue(_settings(tmp_path / "dispatch-load.db"))
    queue.bootstrap_nonproduction_schema()
    commands = [_command(index) for index in range(300)]

    for command in commands:
        assert queue.enqueue("workspace-load", "meeting-load", command) is True
        assert queue.enqueue("workspace-load", "meeting-load", command) is False

    claimed_ids: set[str] = set()
    while (claimed := queue.claim_next()) is not None:
        assert claimed.id not in claimed_ids
        claimed_ids.add(claimed.id)
        queue.succeed(
            claimed.id,
            DispatchResult(
                system="github",
                operation="create_task",
                status="dispatched",
                external_id=f"external-{claimed.id}",
            ),
        )

    assert claimed_ids == {str(command.id) for command in commands}
    jobs = queue.list_jobs("workspace-load", meeting_id="meeting-load")
    assert len(jobs) == 250  # public listing is intentionally bounded
    assert all(job.status is DispatchStatus.succeeded for job in jobs)
    assert queue.claim_next() is None


def test_stale_running_job_is_recovered_after_worker_loss(tmp_path: Path) -> None:
    queue = DispatchQueue(_settings(tmp_path / "dispatch-recovery.db"))
    queue.bootstrap_nonproduction_schema()
    command = _command(1)
    assert queue.enqueue("workspace-a", "meeting-a", command) is True

    claimed = queue.claim_next()
    assert claimed is not None
    assert claimed.status is DispatchStatus.running

    with Session(queue._engine) as session:  # noqa: SLF001 - deliberate fault injection
        record = session.get(DispatchJobRecord, claimed.id)
        assert record is not None
        record.updated_at = datetime.now(UTC) - timedelta(seconds=30)
        session.commit()

    assert queue.recover_stale_running() == 1
    recovered = queue.claim_next()
    assert recovered is not None
    assert recovered.id == claimed.id
    assert recovered.attempts == 2

    queue.succeed(
        recovered.id,
        DispatchResult(
            system="github",
            operation="create_task",
            status="dispatched",
            external_id="recovered-1",
        ),
    )
    final = queue.list_jobs("workspace-a")
    assert len(final) == 1
    assert final[0].status is DispatchStatus.succeeded
    assert final[0].result is not None
    assert final[0].result.external_id == "recovered-1"


def test_failure_storm_dead_letters_every_job_without_cross_workspace_leakage(
    tmp_path: Path,
) -> None:
    queue = DispatchQueue(
        _settings(tmp_path / "dispatch-failure.db", DISPATCH_MAX_ATTEMPTS=1)
    )
    queue.bootstrap_nonproduction_schema()

    workspace_ids = ("workspace-a", "workspace-b")
    commands_by_workspace: dict[str, list[IntegrationCommand]] = {
        workspace_id: [_command(index) for index in range(40)]
        for workspace_id in workspace_ids
    }
    for workspace_id, commands in commands_by_workspace.items():
        for command in commands:
            assert queue.enqueue(workspace_id, "meeting-failure", command) is True

    failed = 0
    while (claimed := queue.claim_next()) is not None:
        assert (
            queue.fail(claimed.id, "simulated provider outage")
            is DispatchStatus.dead_letter
        )
        failed += 1

    assert failed == 80
    for workspace_id in workspace_ids:
        jobs = queue.list_jobs(workspace_id)
        expected_ids = {
            str(command.id) for command in commands_by_workspace[workspace_id]
        }
        assert {job.id for job in jobs} == expected_ids
        assert all(job.status is DispatchStatus.dead_letter for job in jobs)
        assert all(job.last_error == "simulated provider outage" for job in jobs)

    foreign_job_id = str(commands_by_workspace["workspace-a"][0].id)
    assert queue.retry_dead_letter("workspace-b", foreign_job_id) is False
    assert queue.retry_dead_letter("workspace-a", foreign_job_id) is True
