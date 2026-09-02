from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel
from sqlalchemy import DateTime, Float, String, Text, select, text
from sqlalchemy.orm import Mapped, Session, mapped_column

from meeting_intelligence.config import Settings
from meeting_intelligence.schemas import MeetingIntelligenceResult
from meeting_intelligence.storage import Base, _build_engine


class NativeDecisionStatus(StrEnum):
    active = "active"
    superseded = "superseded"
    reversed = "reversed"


class NativeActionStatus(StrEnum):
    open = "open"
    in_progress = "in_progress"
    blocked = "blocked"
    done = "done"
    cancelled = "cancelled"


class NativeDecisionRecord(Base):
    __tablename__ = "native_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    meeting_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NativeActionRecord(Base):
    __tablename__ = "native_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    meeting_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    priority: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NativeDecision(BaseModel):
    id: str
    meeting_id: str
    statement: str
    rationale: str | None = None
    owner: str | None = None
    confidence: float
    evidence: str | None = None
    status: NativeDecisionStatus
    created_at: datetime
    updated_at: datetime


class NativeAction(BaseModel):
    id: str
    meeting_id: str
    title: str
    description: str
    owner: str | None = None
    owner_email: str | None = None
    due_date: datetime | None = None
    priority: str
    confidence: float
    evidence: str | None = None
    status: NativeActionStatus
    outcome: str | None = None
    created_at: datetime
    updated_at: datetime


class NativeDecisionPatch(BaseModel):
    status: NativeDecisionStatus | None = None
    owner: str | None = None


class NativeActionPatch(BaseModel):
    status: NativeActionStatus | None = None
    owner: str | None = None
    due_date: datetime | None = None
    outcome: str | None = None


def _native_id(workspace_id: str, meeting_id: str, kind: str, value: str) -> str:
    canonical = " ".join(value.casefold().split())
    source = f"raeburnai:{workspace_id}:{meeting_id}:{kind}:{canonical}"
    return str(uuid5(NAMESPACE_URL, source))


class NativeWorkStore:
    """RaeburnAI-native source of truth for decisions and accountable actions."""

    def __init__(self, settings: Settings) -> None:
        self._engine = _build_engine(settings.database_url)

    def ready(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1 FROM native_decisions LIMIT 1"))
                connection.execute(text("SELECT 1 FROM native_actions LIMIT 1"))
            return True
        except Exception:
            return False

    def ingest(self, workspace_id: str, result: MeetingIntelligenceResult) -> None:
        """Upsert extracted work without resetting native lifecycle state."""
        now = datetime.now(UTC)
        with Session(self._engine) as session:
            for decision in result.decisions:
                record_id = _native_id(
                    workspace_id, result.meeting_id, "decision", decision.statement
                )
                decision_record = session.get(NativeDecisionRecord, record_id)
                if decision_record is None:
                    session.add(
                        NativeDecisionRecord(
                            id=record_id,
                            workspace_id=workspace_id,
                            meeting_id=result.meeting_id,
                            statement=decision.statement,
                            rationale=decision.rationale,
                            owner=decision.owner,
                            confidence=decision.confidence,
                            evidence=decision.evidence,
                            status=NativeDecisionStatus.active.value,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                else:
                    decision_record.statement = decision.statement
                    decision_record.rationale = decision.rationale
                    decision_record.confidence = decision.confidence
                    decision_record.evidence = decision.evidence
                    if decision_record.owner is None:
                        decision_record.owner = decision.owner
                    decision_record.updated_at = now

            for action in result.action_items:
                identity = f"{action.title}\n{action.description}"
                record_id = _native_id(
                    workspace_id, result.meeting_id, "action", identity
                )
                action_record = session.get(NativeActionRecord, record_id)
                if action_record is None:
                    session.add(
                        NativeActionRecord(
                            id=record_id,
                            workspace_id=workspace_id,
                            meeting_id=result.meeting_id,
                            title=action.title,
                            description=action.description,
                            owner=action.owner,
                            owner_email=action.owner_email,
                            due_date=action.due_date,
                            priority=action.priority.value,
                            confidence=action.confidence,
                            evidence=action.evidence,
                            status=NativeActionStatus.open.value,
                            outcome=None,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                else:
                    action_record.title = action.title
                    action_record.description = action.description
                    action_record.confidence = action.confidence
                    action_record.evidence = action.evidence
                    action_record.priority = action.priority.value
                    if action_record.owner is None:
                        action_record.owner = action.owner
                        action_record.owner_email = action.owner_email
                    if action_record.due_date is None:
                        action_record.due_date = action.due_date
                    action_record.updated_at = now
            session.commit()

    def list_decisions(
        self, workspace_id: str, *, meeting_id: str | None = None
    ) -> list[NativeDecision]:
        with Session(self._engine) as session:
            statement = select(NativeDecisionRecord).where(
                NativeDecisionRecord.workspace_id == workspace_id
            )
            if meeting_id is not None:
                statement = statement.where(NativeDecisionRecord.meeting_id == meeting_id)
            records = session.scalars(
                statement.order_by(NativeDecisionRecord.updated_at.desc()).limit(500)
            ).all()
            return [self._decision(record) for record in records]

    def list_actions(
        self, workspace_id: str, *, meeting_id: str | None = None
    ) -> list[NativeAction]:
        with Session(self._engine) as session:
            statement = select(NativeActionRecord).where(
                NativeActionRecord.workspace_id == workspace_id
            )
            if meeting_id is not None:
                statement = statement.where(NativeActionRecord.meeting_id == meeting_id)
            records = session.scalars(
                statement.order_by(NativeActionRecord.updated_at.desc()).limit(500)
            ).all()
            return [self._action(record) for record in records]

    def update_decision(
        self, workspace_id: str, decision_id: str, patch: NativeDecisionPatch
    ) -> NativeDecision | None:
        with Session(self._engine) as session:
            record = session.scalar(
                select(NativeDecisionRecord).where(
                    NativeDecisionRecord.id == decision_id,
                    NativeDecisionRecord.workspace_id == workspace_id,
                )
            )
            if record is None:
                return None
            if patch.status is not None:
                record.status = patch.status.value
            if patch.owner is not None:
                record.owner = patch.owner
            record.updated_at = datetime.now(UTC)
            session.commit()
            session.refresh(record)
            return self._decision(record)

    def update_action(
        self, workspace_id: str, action_id: str, patch: NativeActionPatch
    ) -> NativeAction | None:
        with Session(self._engine) as session:
            record = session.scalar(
                select(NativeActionRecord).where(
                    NativeActionRecord.id == action_id,
                    NativeActionRecord.workspace_id == workspace_id,
                )
            )
            if record is None:
                return None
            if patch.status is not None:
                record.status = patch.status.value
            if patch.owner is not None:
                record.owner = patch.owner
            if patch.due_date is not None:
                record.due_date = patch.due_date
            if patch.outcome is not None:
                record.outcome = patch.outcome
            record.updated_at = datetime.now(UTC)
            session.commit()
            session.refresh(record)
            return self._action(record)

    def delete_meeting(self, workspace_id: str, meeting_id: str) -> None:
        with Session(self._engine) as session:
            decisions = session.scalars(
                select(NativeDecisionRecord).where(
                    NativeDecisionRecord.workspace_id == workspace_id,
                    NativeDecisionRecord.meeting_id == meeting_id,
                )
            ).all()
            actions = session.scalars(
                select(NativeActionRecord).where(
                    NativeActionRecord.workspace_id == workspace_id,
                    NativeActionRecord.meeting_id == meeting_id,
                )
            ).all()
            for record in [*decisions, *actions]:
                session.delete(record)
            session.commit()

    @staticmethod
    def _decision(record: NativeDecisionRecord) -> NativeDecision:
        return NativeDecision(
            id=record.id,
            meeting_id=record.meeting_id,
            statement=record.statement,
            rationale=record.rationale,
            owner=record.owner,
            confidence=record.confidence,
            evidence=record.evidence,
            status=NativeDecisionStatus(record.status),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _action(record: NativeActionRecord) -> NativeAction:
        return NativeAction(
            id=record.id,
            meeting_id=record.meeting_id,
            title=record.title,
            description=record.description,
            owner=record.owner,
            owner_email=record.owner_email,
            due_date=record.due_date,
            priority=record.priority,
            confidence=record.confidence,
            evidence=record.evidence,
            status=NativeActionStatus(record.status),
            outcome=record.outcome,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
