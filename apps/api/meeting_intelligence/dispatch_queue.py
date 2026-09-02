from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel
from sqlalchemy import DateTime, Integer, String, Text, select, text
from sqlalchemy.orm import Mapped, Session, mapped_column

from meeting_intelligence.config import Settings
from meeting_intelligence.integrations import DispatchResult
from meeting_intelligence.schemas import ApprovalStatus, IntegrationCommand
from meeting_intelligence.storage import Base, _build_engine


class DispatchStatus(StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    dead_letter = "dead_letter"
    cancelled = "cancelled"


class DispatchJobRecord(Base):
    __tablename__ = "dispatch_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    meeting_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    command_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class DispatchJob(BaseModel):
    id: str
    workspace_id: str
    meeting_id: str
    status: DispatchStatus
    attempts: int
    next_attempt_at: datetime
    last_error: str | None = None
    command: IntegrationCommand
    result: DispatchResult | None = None


class DispatchQueue:
    """Durable, idempotent database-backed integration dispatch queue."""

    def __init__(self, settings: Settings) -> None:
        self._engine = _build_engine(settings.database_url)
        self._environment = settings.environment
        self._max_attempts = settings.dispatch_max_attempts
        self._base_backoff_seconds = settings.dispatch_base_backoff_seconds
        self._lease_seconds = settings.dispatch_lease_seconds

    def bootstrap_nonproduction_schema(self) -> None:
        if self._environment != "production":
            Base.metadata.create_all(self._engine)

    def ready(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1 FROM dispatch_jobs LIMIT 1"))
            return True
        except Exception:
            return False

    def enqueue(
        self, workspace_id: str, meeting_id: str, command: IntegrationCommand
    ) -> bool:
        if command.approval_status is not ApprovalStatus.approved:
            raise ValueError("only approved commands can be queued")
        now = datetime.now(UTC)
        job_id = str(command.id)
        with Session(self._engine) as session:
            if session.get(DispatchJobRecord, job_id) is not None:
                return False
            session.add(
                DispatchJobRecord(
                    id=job_id,
                    workspace_id=workspace_id,
                    meeting_id=meeting_id,
                    command_json=command.model_dump_json(),
                    status=DispatchStatus.queued.value,
                    attempts=0,
                    next_attempt_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.commit()
        return True

    def recover_stale_running(self) -> int:
        """Return abandoned running jobs to the queue after a bounded worker lease."""
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=self._lease_seconds)
        recovered = 0
        with Session(self._engine) as session:
            records = session.scalars(
                select(DispatchJobRecord).where(
                    DispatchJobRecord.status == DispatchStatus.running.value,
                    DispatchJobRecord.updated_at <= cutoff,
                )
            ).all()
            for record in records:
                record.status = DispatchStatus.queued.value
                record.next_attempt_at = now
                record.updated_at = now
                recovered += 1
            session.commit()
        return recovered

    def claim_next(self) -> DispatchJob | None:
        now = datetime.now(UTC)
        with Session(self._engine) as session:
            statement = (
                select(DispatchJobRecord)
                .where(
                    DispatchJobRecord.status == DispatchStatus.queued.value,
                    DispatchJobRecord.next_attempt_at <= now,
                )
                .order_by(DispatchJobRecord.created_at)
                .limit(1)
            )
            if self._engine.dialect.name != "sqlite":
                statement = statement.with_for_update(skip_locked=True)
            record = session.scalar(statement)
            if record is None:
                return None
            record.status = DispatchStatus.running.value
            record.attempts += 1
            record.updated_at = now
            session.commit()
            session.refresh(record)
            return self._to_job(record)

    def succeed(self, job_id: str, result: DispatchResult) -> None:
        now = datetime.now(UTC)
        with Session(self._engine) as session:
            record = session.get(DispatchJobRecord, job_id)
            if record is None:
                raise KeyError(job_id)
            if record.status == DispatchStatus.cancelled.value:
                return
            record.status = DispatchStatus.succeeded.value
            record.result_json = result.model_dump_json()
            record.last_error = None
            record.updated_at = now
            session.commit()

    def fail(self, job_id: str, error: str) -> DispatchStatus:
        now = datetime.now(UTC)
        with Session(self._engine) as session:
            record = session.get(DispatchJobRecord, job_id)
            if record is None:
                raise KeyError(job_id)
            if record.status == DispatchStatus.cancelled.value:
                return DispatchStatus.cancelled
            record.last_error = error[:2000]
            record.updated_at = now
            if record.attempts >= self._max_attempts:
                record.status = DispatchStatus.dead_letter.value
            else:
                record.status = DispatchStatus.queued.value
                delay = self._base_backoff_seconds * (2 ** max(record.attempts - 1, 0))
                record.next_attempt_at = now + timedelta(seconds=min(delay, 3600))
            session.commit()
            return DispatchStatus(record.status)

    def retry_dead_letter(self, workspace_id: str, job_id: str) -> bool:
        now = datetime.now(UTC)
        with Session(self._engine) as session:
            record = session.scalar(
                select(DispatchJobRecord).where(
                    DispatchJobRecord.id == job_id,
                    DispatchJobRecord.workspace_id == workspace_id,
                )
            )
            if record is None or record.status != DispatchStatus.dead_letter.value:
                return False
            record.status = DispatchStatus.queued.value
            record.attempts = 0
            record.next_attempt_at = now
            record.last_error = None
            record.updated_at = now
            session.commit()
            return True

    def cancel(self, workspace_id: str, job_id: str) -> bool:
        with Session(self._engine) as session:
            record = session.scalar(
                select(DispatchJobRecord).where(
                    DispatchJobRecord.id == job_id,
                    DispatchJobRecord.workspace_id == workspace_id,
                )
            )
            if record is None or record.status in {
                DispatchStatus.succeeded.value,
                DispatchStatus.cancelled.value,
            }:
                return False
            record.status = DispatchStatus.cancelled.value
            record.updated_at = datetime.now(UTC)
            session.commit()
            return True

    def list_jobs(
        self, workspace_id: str, meeting_id: str | None = None
    ) -> list[DispatchJob]:
        with Session(self._engine) as session:
            statement = select(DispatchJobRecord).where(
                DispatchJobRecord.workspace_id == workspace_id
            )
            if meeting_id is not None:
                statement = statement.where(DispatchJobRecord.meeting_id == meeting_id)
            records = session.scalars(
                statement.order_by(DispatchJobRecord.created_at.desc()).limit(250)
            ).all()
            return [self._to_job(record) for record in records]

    @staticmethod
    def _to_job(record: DispatchJobRecord) -> DispatchJob:
        result = (
            DispatchResult.model_validate_json(record.result_json)
            if record.result_json
            else None
        )
        return DispatchJob(
            id=record.id,
            workspace_id=record.workspace_id,
            meeting_id=record.meeting_id,
            status=DispatchStatus(record.status),
            attempts=record.attempts,
            next_attempt_at=record.next_attempt_at,
            last_error=record.last_error,
            command=IntegrationCommand.model_validate_json(record.command_json),
            result=result,
        )
