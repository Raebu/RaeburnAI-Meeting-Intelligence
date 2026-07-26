from __future__ import annotations

import secrets
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from meeting_intelligence.config import Settings, get_settings
from meeting_intelligence.database import database_is_ready, initialise_database
from meeting_intelligence.intelligence import MeetingIntelligenceEngine
from meeting_intelligence.repository import MeetingResultRepository
from meeting_intelligence.schemas import (
    ApprovalRequest,
    ApprovalStatus,
    HealthResponse,
    MeetingAnalyseRequest,
    MeetingIntelligenceResult,
)

logger = structlog.get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.auto_create_schema:
        initialise_database()
        logger.info("database_schema_initialised", environment=settings.environment)
    yield


app = FastAPI(
    title="RaeburnAI Meeting Intelligence API",
    version="0.2.0",
    description="Meeting intelligence API for decisions, actions, owners and workflow writebacks.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["content-type", "x-api-key", "x-request-id"],
)

_engine = MeetingIntelligenceEngine()
_repository = MeetingResultRepository()
_rate_window: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def rate_limit_and_audit(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get("x-request-id") or str(uuid4())
    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window = _rate_window[client]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= settings.rate_limit_per_minute:
        logger.warning(
            "rate_limit_exceeded", request_id=request_id, client=client, path=request.url.path
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded", "request_id": request_id},
            headers={"x-request-id": request_id, "retry-after": "60"},
        )
    window.append(now)

    started = time.monotonic()
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request_completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round((time.monotonic() - started) * 1000, 2),
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request.headers.get("x-request-id") or str(uuid4())
    logger.exception(
        "unhandled_exception",
        request_id=request_id,
        path=request.url.path,
        exception_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "request_id": request_id},
        headers={"x-request-id": request_id},
    )


def require_api_key(
    x_api_key: str | None = Header(default=None), app_settings: Settings = Depends(get_settings)
) -> None:
    if app_settings.environment == "development" and app_settings.api_key.startswith("change-me"):
        return
    if x_api_key is None or not secrets.compare_digest(x_api_key, app_settings.api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok", service="meeting-intelligence-api", version="0.2.0")


@app.get("/readyz", response_model=HealthResponse)
def readyz() -> HealthResponse:
    if not database_is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        )
    return HealthResponse(status="ready", service="meeting-intelligence-api", version="0.2.0")


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
    _repository.save_analysis(result)
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
    result = _repository.get(meeting_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting result not found")
    return result


def update_command_approval(
    meeting_id: str,
    approval: ApprovalRequest,
    approval_status: ApprovalStatus,
) -> MeetingIntelligenceResult:
    try:
        result = _repository.update_approval(
            meeting_id=meeting_id,
            command_ids=approval.command_ids,
            approval_status=approval_status,
            actor=approval.approved_by,
            reason=approval.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting result not found")
    logger.info(
        "commands_approval_updated",
        meeting_id=meeting_id,
        actor=approval.approved_by,
        approval_status=approval_status.value,
        command_count=len(approval.command_ids),
    )
    return result


@app.post(
    "/v1/approvals/{meeting_id}/approve",
    response_model=MeetingIntelligenceResult,
    dependencies=[Depends(require_api_key)],
)
def approve_commands(meeting_id: str, approval: ApprovalRequest) -> MeetingIntelligenceResult:
    return update_command_approval(meeting_id, approval, ApprovalStatus.approved)


@app.post(
    "/v1/approvals/{meeting_id}/reject",
    response_model=MeetingIntelligenceResult,
    dependencies=[Depends(require_api_key)],
)
def reject_commands(meeting_id: str, approval: ApprovalRequest) -> MeetingIntelligenceResult:
    return update_command_approval(meeting_id, approval, ApprovalStatus.rejected)
