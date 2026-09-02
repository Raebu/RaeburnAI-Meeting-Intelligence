from __future__ import annotations

import hashlib
import time
from collections import deque
from collections.abc import Awaitable, Callable
from threading import Lock
from urllib.parse import quote

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
    IntegrationCommand,
    MeetingAnalyseRequest,
    MeetingIntelligenceResult,
)
from meeting_intelligence.security import apply_security_headers
from meeting_intelligence.storage import MeetingResultStore

logger = structlog.get_logger(__name__)
settings = get_settings()
app = FastAPI(
    title="RaeburnAI Meeting Intelligence API",
    version="0.1.0",
    description=(
        "Meeting intelligence API for decisions, actions, owners and workflow "
        "writebacks."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["content-type", "x-api-key"],
)

_engine = MeetingIntelligenceEngine()
_store = MeetingResultStore(settings)
_store.bootstrap_nonproduction_schema()
_rate_window: dict[str, deque[float]] = {}
_rate_limit_lock = Lock()
_MEETING_LOCK_STRIPE_COUNT = 256
_meeting_lock_stripes = tuple(Lock() for _ in range(_MEETING_LOCK_STRIPE_COUNT))


def _safe_ref(value: str) -> str:
    """Return a stable non-reversible reference suitable for operational logs."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _safe_route_path(request: Request) -> str:
    """Return the route template without logging user-controlled path parameters."""
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    return route_path if isinstance(route_path, str) else "unresolved"


def _meeting_lock(meeting_id: str) -> Lock:
    """Map arbitrary meeting IDs onto a fixed lock pool without retaining the IDs."""
    digest = hashlib.sha256(meeting_id.encode("utf-8")).digest()
    stripe = int.from_bytes(digest[:8], byteorder="big") % _MEETING_LOCK_STRIPE_COUNT
    return _meeting_lock_stripes[stripe]


def _approval_targets(
    result: MeetingIntelligenceResult, approval: ApprovalRequest
) -> list[IntegrationCommand]:
    requested_ids = set(approval.command_ids)
    if not requested_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one command ID is required",
        )

    commands_by_id = {command.id: command for command in result.integration_commands}
    missing_ids = requested_ids - commands_by_id.keys()
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more command IDs do not belong to this meeting",
        )

    targets = [commands_by_id[command_id] for command_id in requested_ids]
    if any(
        command.approval_status is not ApprovalStatus.pending for command in targets
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending commands can be approved or rejected",
        )
    return targets


def _stored_result(meeting_id: str) -> MeetingIntelligenceResult | None:
    """Return a non-expired durable meeting result."""
    return _store.get(meeting_id)


def _consume_rate_limit(client: str, now: float) -> bool:
    """Consume one request slot while keeping per-client state memory-bounded."""
    app_settings = get_settings()
    window_seconds = 60.0

    with _rate_limit_lock:
        window = _rate_window.get(client)
        if window is None:
            if len(_rate_window) >= app_settings.rate_limit_max_clients:
                stale_clients = [
                    key
                    for key, timestamps in _rate_window.items()
                    if not timestamps or now - timestamps[-1] > window_seconds
                ]
                for key in stale_clients:
                    _rate_window.pop(key, None)

            if len(_rate_window) >= app_settings.rate_limit_max_clients:
                return False

            window = deque()
            _rate_window[client] = window

        while window and now - window[0] > window_seconds:
            window.popleft()

        if len(window) >= app_settings.rate_limit_per_minute:
            return False

        window.append(now)
        return True


@app.middleware("http")
async def rate_limit_and_audit(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    app_settings = get_settings()
    client = request.client.host if request.client else "unknown"
    if not _consume_rate_limit(client, time.monotonic()):
        logger.warning(
            "rate_limit_exceeded",
            client_ref=_safe_ref(client),
            route=_safe_route_path(request),
        )
        return apply_security_headers(
            JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"}),
            app_settings,
        )
    response = await call_next(request)
    logger.info(
        "request_completed",
        method=request.method,
        route=_safe_route_path(request),
        status_code=response.status_code,
    )
    return apply_security_headers(response, app_settings)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled_exception",
        route=_safe_route_path(request),
        error_type=type(exc).__name__,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def require_api_key(
    x_api_key: str | None = Header(default=None),
    app_settings: Settings = Depends(get_settings),
) -> None:
    if x_api_key != app_settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(
        status="ok", service="meeting-intelligence-api", version="0.1.0"
    )


@app.get("/readyz", response_model=HealthResponse)
def readyz() -> HealthResponse:
    if not _store.ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence layer is not ready",
        )
    return HealthResponse(
        status="ready", service="meeting-intelligence-api", version="0.1.0"
    )


@app.post(
    "/v1/meetings/analyse",
    response_model=MeetingIntelligenceResult,
    dependencies=[Depends(require_api_key)],
)
def analyse_meeting(request: MeetingAnalyseRequest) -> MeetingIntelligenceResult:
    result = _engine.analyse(request)
    app_settings = get_settings()
    require_approval = app_settings.approvals_required or bool(request.require_approval)
    if not require_approval:
        for command in result.integration_commands:
            command.approval_status = ApprovalStatus.approved
    with _meeting_lock(request.meeting_id):
        _store.put(request.meeting_id, result, reset_retention=True)
    logger.info(
        "meeting_analyzed",
        meeting_ref=_safe_ref(request.meeting_id),
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
    with _meeting_lock(meeting_id):
        result = _stored_result(meeting_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting result not found",
            )
        return result.model_copy(deep=True)


@app.get(
    "/v1/meetings/{meeting_id}/export",
    response_model=MeetingIntelligenceResult,
    dependencies=[Depends(require_api_key)],
)
def export_meeting_result(meeting_id: str) -> JSONResponse:
    with _meeting_lock(meeting_id):
        result = _stored_result(meeting_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting result not found",
            )
        exported = result.model_dump(mode="json")
    logger.info("meeting_exported", meeting_ref=_safe_ref(meeting_id))
    encoded_filename = quote(f"meeting-{meeting_id}.json", safe="")
    return JSONResponse(
        content=exported,
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": (
                'attachment; filename="meeting-export.json"; '
                f"filename*=UTF-8''{encoded_filename}"
            ),
            "Vary": "X-API-Key",
        },
    )


@app.delete(
    "/v1/meetings/{meeting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_api_key)],
)
def delete_meeting_result(meeting_id: str) -> Response:
    with _meeting_lock(meeting_id):
        if _stored_result(meeting_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting result not found",
            )
        _store.delete(meeting_id)
    logger.info("meeting_deleted", meeting_ref=_safe_ref(meeting_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post(
    "/v1/approvals/{meeting_id}/approve",
    response_model=MeetingIntelligenceResult,
    dependencies=[Depends(require_api_key)],
)
def approve_commands(
    meeting_id: str, approval: ApprovalRequest
) -> MeetingIntelligenceResult:
    with _meeting_lock(meeting_id):
        result = _stored_result(meeting_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting result not found",
            )
        targets = _approval_targets(result, approval)
        for command in targets:
            command.approval_status = ApprovalStatus.approved
        result.audit_events.append(f"commands.approved_by:{approval.approved_by}")
        _store.put(meeting_id, result, reset_retention=False)
        response_result = result.model_copy(deep=True)
    logger.info(
        "commands_approved",
        meeting_ref=_safe_ref(meeting_id),
        actor_ref=_safe_ref(approval.approved_by),
    )
    return response_result


@app.post(
    "/v1/approvals/{meeting_id}/reject",
    response_model=MeetingIntelligenceResult,
    dependencies=[Depends(require_api_key)],
)
def reject_commands(
    meeting_id: str, approval: ApprovalRequest
) -> MeetingIntelligenceResult:
    with _meeting_lock(meeting_id):
        result = _stored_result(meeting_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting result not found",
            )
        targets = _approval_targets(result, approval)
        for command in targets:
            command.approval_status = ApprovalStatus.rejected
        result.audit_events.append(f"commands.rejected_by:{approval.approved_by}")
        _store.put(meeting_id, result, reset_retention=False)
        response_result = result.model_copy(deep=True)
    logger.info(
        "commands_rejected",
        meeting_ref=_safe_ref(meeting_id),
        actor_ref=_safe_ref(approval.approved_by),
    )
    return response_result
