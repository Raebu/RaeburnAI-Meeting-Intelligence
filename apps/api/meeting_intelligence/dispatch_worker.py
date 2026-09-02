from __future__ import annotations

import asyncio

import structlog

from meeting_intelligence.config import Settings, get_settings
from meeting_intelligence.dispatch_queue import DispatchQueue
from meeting_intelligence.integrations import (
    GitHubIssueAdapter,
    IntegrationAdapter,
    JiraAdapter,
    WebhookAdapter,
)

logger = structlog.get_logger(__name__)


def _adapter_for(settings: Settings, system: str) -> IntegrationAdapter:
    if system == "github":
        return GitHubIssueAdapter(settings)
    if system == "jira":
        return JiraAdapter(settings)
    if system == "webhook":
        return WebhookAdapter(settings)
    raise ValueError(f"unsupported integration system: {system}")


async def run_once(queue: DispatchQueue, settings: Settings) -> bool:
    """Dispatch at most one due job and persist its terminal/retry state."""
    queue.recover_stale_running()
    job = queue.claim_next()
    if job is None:
        return False
    try:
        adapter = _adapter_for(settings, job.command.system)
        result = await adapter.dispatch(job.command)
        if result.status == "dispatched":
            queue.succeed(job.id, result)
            logger.info(
                "dispatch_succeeded",
                job_id=job.id,
                workspace_id=job.workspace_id,
                system=job.command.system,
            )
        else:
            state = queue.fail(job.id, result.detail or result.status)
            logger.warning(
                "dispatch_not_completed",
                job_id=job.id,
                workspace_id=job.workspace_id,
                system=job.command.system,
                state=state.value,
            )
    except Exception as exc:
        state = queue.fail(job.id, type(exc).__name__)
        logger.warning(
            "dispatch_failed",
            job_id=job.id,
            workspace_id=job.workspace_id,
            system=job.command.system,
            error_type=type(exc).__name__,
            state=state.value,
        )
    return True


async def run_forever() -> None:
    settings = get_settings()
    queue = DispatchQueue(settings)
    queue.bootstrap_nonproduction_schema()
    while True:
        processed = await run_once(queue, settings)
        if not processed:
            await asyncio.sleep(settings.dispatch_poll_seconds)


def main() -> None:
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
