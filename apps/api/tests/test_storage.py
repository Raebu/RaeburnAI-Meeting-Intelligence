from pathlib import Path

from meeting_intelligence.config import Settings
from meeting_intelligence.schemas import MeetingIntelligenceResult
from meeting_intelligence.storage import MeetingResultStore


def _settings(database_path: Path) -> Settings:
    return Settings(
        RAEBURN_ENV="test",
        RAEBURN_API_KEY="test-storage-key",
        DATABASE_URL=f"sqlite+pysqlite:///{database_path}",
    )


def _result(meeting_id: str) -> MeetingIntelligenceResult:
    return MeetingIntelligenceResult(
        meeting_id=meeting_id,
        decisions=[],
        action_items=[],
        integration_commands=[],
        audit_events=["meeting.created"],
    )


def test_meeting_result_survives_store_recreation(tmp_path: Path) -> None:
    database_path = tmp_path / "meeting-results.db"
    first = MeetingResultStore(_settings(database_path))
    first.bootstrap_nonproduction_schema()
    first.put("meeting-1", _result("meeting-1"), reset_retention=True)

    second = MeetingResultStore(_settings(database_path))
    stored = second.get("meeting-1")

    assert stored is not None
    assert stored.meeting_id == "meeting-1"
    assert stored.audit_events == ["meeting.created"]


def test_updates_and_deletes_are_durable(tmp_path: Path) -> None:
    database_path = tmp_path / "meeting-results.db"
    store = MeetingResultStore(_settings(database_path))
    store.bootstrap_nonproduction_schema()
    result = _result("meeting-2")
    store.put("meeting-2", result, reset_retention=True)

    result.audit_events.append("commands.approved_by:reviewer@example.com")
    store.put("meeting-2", result, reset_retention=False)

    reloaded = MeetingResultStore(_settings(database_path))
    stored = reloaded.get("meeting-2")
    assert stored is not None
    assert stored.audit_events[-1] == "commands.approved_by:reviewer@example.com"

    assert reloaded.delete("meeting-2") is True
    assert MeetingResultStore(_settings(database_path)).get("meeting-2") is None


def test_readiness_requires_schema(tmp_path: Path) -> None:
    database_path = tmp_path / "meeting-results.db"
    store = MeetingResultStore(_settings(database_path))

    assert store.ready() is False
    store.bootstrap_nonproduction_schema()
    assert store.ready() is True
