from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text, create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from meeting_intelligence.config import Settings
from meeting_intelligence.schemas import MeetingIntelligenceResult


class Base(DeclarativeBase):
    pass


class MeetingResultRecord(Base):
    __tablename__ = "meeting_results"

    meeting_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class MeetingResultStore:
    def __init__(self, settings: Settings) -> None:
        self._engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            future=True,
        )
        self._environment = settings.environment

    def bootstrap_development_schema(self) -> None:
        # Production schema changes are always explicit migrations. Development
        # and test environments may bootstrap disposable local databases.
        if self._environment in {"development", "test"}:
            Base.metadata.create_all(self._engine)

    def ready(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                connection.execute(text("SELECT 1 FROM meeting_results LIMIT 1"))
            return True
        except Exception:
            return False

    def put(self, meeting_id: str, result: MeetingIntelligenceResult) -> None:
        payload = result.model_dump_json()
        now = datetime.now(UTC)
        with Session(self._engine) as session:
            existing = session.get(MeetingResultRecord, meeting_id)
            if existing is None:
                session.add(
                    MeetingResultRecord(
                        meeting_id=meeting_id,
                        payload=payload,
                        created_at=now,
                        updated_at=now,
                    )
                )
            else:
                existing.payload = payload
                existing.updated_at = now
            session.commit()

    def get(self, meeting_id: str) -> MeetingIntelligenceResult | None:
        with Session(self._engine) as session:
            record = session.scalar(
                select(MeetingResultRecord).where(MeetingResultRecord.meeting_id == meeting_id)
            )
            if record is None:
                return None
            return MeetingIntelligenceResult.model_validate_json(record.payload)
