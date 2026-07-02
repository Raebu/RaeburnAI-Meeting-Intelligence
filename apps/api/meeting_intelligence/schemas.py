from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class Priority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ApprovalStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    dispatched = "dispatched"
    failed = "failed"


class Attendee(BaseModel):
    name: str
    email: str | None = None
    role: str | None = None
    crm_contact_id: str | None = None
    github_username: str | None = None
    jira_account_id: str | None = None


class MeetingContext(BaseModel):
    crm_account_id: str | None = None
    crm_deal_id: str | None = None
    project_key: str | None = None
    repository: str | None = Field(default=None, description="owner/repo GitHub repository")
    source_url: HttpUrl | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MeetingAnalyseRequest(BaseModel):
    meeting_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    transcript: str = Field(min_length=1)
    attendees: list[Attendee] = Field(default_factory=list)
    context: MeetingContext = Field(default_factory=MeetingContext)
    require_approval: bool | None = None


class Decision(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    statement: str
    rationale: str | None = None
    owner: str | None = None
    confidence: float = Field(ge=0, le=1, default=0.75)
    evidence: str | None = None


class ActionItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    owner: str | None = None
    owner_email: str | None = None
    due_date: datetime | None = None
    priority: Priority = Priority.medium
    confidence: float = Field(ge=0, le=1, default=0.75)
    evidence: str | None = None
    suggested_systems: list[str] = Field(default_factory=list)


class CrmUpdate(BaseModel):
    summary: str
    account_id: str | None = None
    deal_id: str | None = None
    next_step: str | None = None
    risk: str | None = None
    confidence: float = Field(ge=0, le=1, default=0.75)


class FollowUp(BaseModel):
    subject: str
    body: str
    recipients: list[str] = Field(default_factory=list)


class IntegrationCommand(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    system: str
    operation: str
    payload: dict[str, Any]
    approval_status: ApprovalStatus = ApprovalStatus.pending


class MeetingIntelligenceResult(BaseModel):
    meeting_id: str
    decisions: list[Decision]
    action_items: list[ActionItem]
    crm_update: CrmUpdate | None = None
    follow_up: FollowUp | None = None
    integration_commands: list[IntegrationCommand]
    audit_events: list[str]


class ApprovalRequest(BaseModel):
    command_ids: list[UUID]
    approved_by: str
    reason: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
