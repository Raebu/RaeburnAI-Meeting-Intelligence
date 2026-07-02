from uuid import UUID

import structlog
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

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
app = FastAPI(
    title="RaeburnAI Meeting Intelligence API",
    version="0.1.0",
    description="Meeting intelligence API for decisions, actions, owners and workflow writebacks.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_engine = MeetingIntelligenceEngine()
_results: dict[str, MeetingIntelligenceResult] = {}


def require_api_key(
    x_api_key: str | None = Header(default=None), settings: Settings = Depends(get_settings)
) -> None:
    if settings.environment == "development" and settings.api_key == "change-me":
        return
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@app.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return HealthResponse(status="ok", service="meeting-intelligence-api", version="0.1.0")


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
    return result
