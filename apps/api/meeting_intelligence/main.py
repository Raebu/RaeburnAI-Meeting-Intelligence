from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from uuid import UUID

import structlog
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from meeting_intelligence.config import Settings, get_settings
from meeting_intelligence.intelligence import MeetingIntelligenceEngine
from meeting_intelligence.schemas import (
    ApprovalRequest,
    ApprovalStatus,
    HealthResponse,
    MeetingAnalyseRequest,
    MeetingIntelligenceResult,
)

logger = structlog.get_logger(__name__)
settings = get_settings()
app = FastAPI(
    title="RaeburnAI Meeting Intelligence API",
    version="0.1.0",
    description="Meeting intelligence API for decisions, actions, owners and workflow writebacks.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["content-type", "x-api-key"],
)

_engine = MeetingIntelligenceEngine()
_results: dict[str, MeetingIntelligenceResult] = {}
_rate_window: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def rate_limit_and_audit(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = _rate_window[client]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= settings.rate_limit_per_minute:
        logger.warning("rate_limit_exceeded", client=client, path=request.url.path)
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    window.append(now)
    response = await call_next(request)
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def require_api_key(
    x_api_key: str | None = Header(default=None), app_settings: Settings = Depends(get_settings)
) -> None:
    if app_settings.environment == "development" and app_settings.api_key.startswith("change-me"):
        return
    if x_api_key != app_settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok", service="meeting-intelligence-api", version="0.1.0")


@app.get("/readyz", response_model=HealthResponse)
def readyz() -> HealthResponse:
    return HealthResponse(status="ready", service="meeting-intelligence-api", version="0.1.0")


@app.post(
    "/v1/meetings/analyse",
    response_model=MeetingIntelligenceResult,
    dependencies=[Depends(require_api_key)],
)
def analyse_meeting(request: MeetingAnalyseRequest) -> MeetingIntelligenceResult:
    result = _engine.analyse(request)
    require_approval = request.require_approval
    if require_approval is None:
        require_approval = get_settings().approvals_required
    if not require_approval:
        for command in result.integration_commands:
            command.approval_status = ApprovalStatus.approved
    _results[request.meeting_id] = result
    logger.info(
        "meeting_analyzed",
        meeting_id=request.meeting_id,
        decisions=len(result.decisions),
        actions=len(result.action_items),
    )
    return result


@app.get(
    "/v1/meetings/{meeting_id}",
    response_model=MeetingIntelligenceResult,
    dependencies=[Depends(require_api_key)],
)
def get_meeting_result(meeting_id: str) -> MeetingIntelligenceResult:
    result = _results.get(meeting_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting result not found")
    return result


@app.post(
    "/v1/approvals/{meeting_id}/approve",
    response_model=MeetingIntelligenceResult,
    dependencies=[Depends(require_api_key)],
)
def approve_commands(meeting_id: str, approval: ApprovalRequest) -> MeetingIntelligenceResult:
    result = _results.get(meeting_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting result not found")
    requested_ids: set[UUID] = set(approval.command_ids)
    for command in result.integration_commands:
        if command.id in requested_ids:
            command.approval_status = ApprovalStatus.approved
    result.audit_events.append(f"commands.approved_by:{approval.approved_by}")
    logger.info("commands_approved", meeting_id=meeting_id, approved_by=approval.approved_by)
    return result


@app.post(
    "/v1/approvals/{meeting_id}/reject",
    response_model=MeetingIntelligenceResult,
    dependencies=[Depends(require_api_key)],
)
def reject_commands(meeting_id: str, approval: ApprovalRequest) -> MeetingIntelligenceResult:
    result = _results.get(meeting_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting result not found")
    requested_ids: set[UUID] = set(approval.command_ids)
    for command in result.integration_commands:
        if command.id in requested_ids:
            command.approval_status = ApprovalStatus.rejected
    result.audit_events.append(f"commands.rejected_by:{approval.approved_by}")
    logger.info("commands_rejected", meeting_id=meeting_id, rejected_by=approval.approved_by)
    return result
