from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, String, Text, create_engine, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.pool import StaticPool

from meeting_intelligence.config import Settings
from meeting_intelligence.schemas import MeetingIntelligenceResult


class Base(DeclarativeBase):
    pass


class MeetingResultRecord(Base):
    __tablename__ = "meeting_results"

    meeting_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    stored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def _build_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite"):
        if ":memory:" in database_url:
            return create_engine(
                database_url,
                pool_pre_ping=True,
                future=True,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        return create_engine(
            database_url,
            pool_pre_ping=True,
            future=True,
            connect_args={"check_same_thread": False},
        )
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        future=True,
    )


class MeetingResultStore:
    """Durable store for meeting results and approval/audit state."""

    def __init__(self, settings: Settings) -> None:
        self._engine = _build_engine(settings.database_url)
        self._environment = settings.environment
        self._retention_seconds = settings.meeting_retention_seconds

    def bootstrap_nonproduction_schema(self) -> None:
        """Create disposable local/test schema; production uses explicit migrations."""
        if self._environment != "production":
            Base.metadata.create_all(self._engine)

    def ready(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                connection.execute(text("SELECT 1 FROM meeting_results LIMIT 1"))
            return True
        except Exception:
            return False

    def put(
        self,
        meeting_id: str,
        result: MeetingIntelligenceResult,
        *,
        reset_retention: bool,
    ) -> None:
        payload = result.model_dump_json()
        now = datetime.now(UTC)
        with Session(self._engine) as session:
            existing = session.get(MeetingResultRecord, meeting_id)
            if existing is None:
                session.add(
                    MeetingResultRecord(
                        meeting_id=meeting_id,
                        payload=payload,
                        stored_at=now,
                        updated_at=now,
                    )
                )
            else:
                existing.payload = payload
                existing.updated_at = now
                if reset_retention:
                    existing.stored_at = now
            session.commit()

    def get(self, meeting_id: str) -> MeetingIntelligenceResult | None:
        cutoff = datetime.now(UTC) - timedelta(seconds=self._retention_seconds)
        with Session(self._engine) as session:
            record = session.scalar(
                select(MeetingResultRecord).where(
                    MeetingResultRecord.meeting_id == meeting_id
                )
            )
            if record is None:
                return None
            stored_at = record.stored_at
            if stored_at.tzinfo is None:
                stored_at = stored_at.replace(tzinfo=UTC)
            if stored_at <= cutoff:
                session.delete(record)
                session.commit()
                return None
            return MeetingIntelligenceResult.model_validate_json(record.payload)

    def delete(self, meeting_id: str) -> bool:
        with Session(self._engine) as session:
            record = session.get(MeetingResultRecord, meeting_id)
            if record is None:
                return False
            session.delete(record)
            session.commit()
            return True
