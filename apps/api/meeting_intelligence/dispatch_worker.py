from __future__ import annotations

import asyncio

import structlog

from meeting_intelligence.config import Settings, get_settings
from meeting_intelligence.dispatch_queue import DispatchQueue
from meeting_intelligence.integrations import (
    EmailAdapter,
    GitHubIssueAdapter,
    HubSpotAdapter,
    IntegrationAdapter,
    JiraAdapter,
    WebhookAdapter,
)
from meeting_intelligence.observability import increment, safe_ref, trace_span

logger = structlog.get_logger(__name__)


def _adapter_for(settings: Settings, workspace_id: str, system: str) -> IntegrationAdapter:
    workspace_config = settings.integration_config(workspace_id, system)
    if system == "github":
        return GitHubIssueAdapter(settings, workspace_config)
    if system == "jira":
        return JiraAdapter(settings, workspace_config)
    if system == "crm":
        return HubSpotAdapter(settings, workspace_config)
    if system == "email":
        return EmailAdapter(settings, workspace_config)
    if system == "webhook":
        return WebhookAdapter(settings, workspace_config)
    raise ValueError(f"unsupported integration system: {system}")


async def run_once(queue: DispatchQueue, settings: Settings) -> bool:
    """Dispatch at most one due job and persist its terminal/retry state."""
    recovered = queue.recover_stale_running()
    if recovered:
        increment("dispatch_stale_recovered_total", outcome="recovered")
    job = queue.claim_next()
    if job is None:
        return False
    system = job.command.system
    increment("dispatch_claimed_total", system=system)
    try:
        with trace_span("dispatch", system=system):
            adapter = _adapter_for(settings, job.workspace_id, system)
            result = await adapter.dispatch(job.command)
        if result.status == "dispatched":
            queue.succeed(job.id, result)
            increment("dispatch_completed_total", system=system, outcome="succeeded")
            logger.info(
                "dispatch_succeeded",
                job_ref=safe_ref(job.id),
                workspace_ref=safe_ref(job.workspace_id),
                system=system,
            )
        else:
            state = queue.fail(job.id, result.detail or result.status)
            increment("dispatch_completed_total", system=system, outcome=state.value)
            logger.warning(
                "dispatch_not_completed",
                job_ref=safe_ref(job.id),
                workspace_ref=safe_ref(job.workspace_id),
                system=system,
                state=state.value,
            )
    except Exception as exc:
        state = queue.fail(job.id, type(exc).__name__)
        increment("dispatch_completed_total", system=system, outcome=state.value)
        logger.warning(
            "dispatch_failed",
            job_ref=safe_ref(job.id),
            workspace_ref=safe_ref(job.workspace_id),
            system=system,
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
