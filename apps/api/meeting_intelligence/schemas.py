from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


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


class Attendee(StrictModel):
    name: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=320)
    role: str | None = Field(default=None, max_length=255)
    crm_contact_id: str | None = Field(default=None, max_length=255)
    github_username: str | None = Field(default=None, max_length=100)
    jira_account_id: str | None = Field(default=None, max_length=255)


class MeetingContext(StrictModel):
    crm_account_id: str | None = Field(default=None, max_length=255)
    crm_deal_id: str | None = Field(default=None, max_length=255)
    project_key: str | None = Field(default=None, max_length=100)
    repository: str | None = Field(
        default=None,
        max_length=255,
        pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$",
        description="owner/repo GitHub repository",
    )
    source_url: HttpUrl | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MeetingAnalyseRequest(StrictModel):
    meeting_id: str = Field(
        default_factory=lambda: str(uuid4()),
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    title: str = Field(min_length=1, max_length=500)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    transcript: str = Field(min_length=1, max_length=250_000)
    attendees: list[Attendee] = Field(default_factory=list, max_length=500)
    context: MeetingContext = Field(default_factory=MeetingContext)
    require_approval: bool | None = None


class Decision(StrictModel):
    id: UUID = Field(default_factory=uuid4)
    statement: str = Field(min_length=1, max_length=10_000)
    rationale: str | None = Field(default=None, max_length=10_000)
    owner: str | None = Field(default=None, max_length=255)
    confidence: float = Field(ge=0, le=1, default=0.75)
    evidence: str | None = Field(default=None, max_length=25_000)


class ActionItem(StrictModel):
    id: UUID = Field(default_factory=uuid4)
    title: str = Field(min_length=1, max_length=1_000)
    description: str = Field(min_length=1, max_length=25_000)
    owner: str | None = Field(default=None, max_length=255)
    owner_email: str | None = Field(default=None, max_length=320)
    due_date: datetime | None = None
    priority: Priority = Priority.medium
    confidence: float = Field(ge=0, le=1, default=0.75)
    evidence: str | None = Field(default=None, max_length=25_000)
    suggested_systems: list[str] = Field(default_factory=list, max_length=25)


class CrmUpdate(StrictModel):
    summary: str = Field(min_length=1, max_length=25_000)
    account_id: str | None = Field(default=None, max_length=255)
    deal_id: str | None = Field(default=None, max_length=255)
    next_step: str | None = Field(default=None, max_length=5_000)
    risk: str | None = Field(default=None, max_length=5_000)
    confidence: float = Field(ge=0, le=1, default=0.75)


class FollowUp(StrictModel):
    subject: str = Field(min_length=1, max_length=998)
    body: str = Field(min_length=1, max_length=100_000)
    recipients: list[str] = Field(default_factory=list, max_length=500)


class IntegrationCommand(StrictModel):
    id: UUID = Field(default_factory=uuid4)
    system: str = Field(min_length=1, max_length=100)
    operation: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any]
    approval_status: ApprovalStatus = ApprovalStatus.pending


class MeetingIntelligenceResult(StrictModel):
    meeting_id: str
    decisions: list[Decision]
    action_items: list[ActionItem]
    crm_update: CrmUpdate | None = None
    follow_up: FollowUp | None = None
    integration_commands: list[IntegrationCommand]
    audit_events: list[str]


class ApprovalRequest(StrictModel):
    command_ids: list[UUID] = Field(min_length=1, max_length=100)
    approved_by: str = Field(min_length=2, max_length=255)
    reason: str | None = Field(default=None, max_length=2_000)


class HealthResponse(StrictModel):
    status: str
    service: str
    version: str
