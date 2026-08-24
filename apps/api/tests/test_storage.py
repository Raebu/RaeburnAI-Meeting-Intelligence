from datetime import datetime

from meeting_intelligence.config import Settings
from meeting_intelligence.intelligence import MeetingIntelligenceEngine
from meeting_intelligence.schemas import Attendee, MeetingAnalyseRequest
from meeting_intelligence.storage import MeetingResultStore


def test_meeting_result_store_round_trip(tmp_path) -> None:
    database_path = tmp_path / "meeting-intelligence.db"
    settings = Settings(
        RAEBURN_ENV="development",
        DATABASE_URL=f"sqlite:///{database_path}",
    )
    store = MeetingResultStore(settings)
    store.bootstrap_development_schema()

    request = MeetingAnalyseRequest(
        meeting_id="meeting-123",
        title="Persistence test",
        occurred_at=datetime(2026, 8, 24, 9, 0, 0),
        attendees=[Attendee(name="Martin", email="martin@example.com")],
        transcript="We decided to run the production migration. Martin will verify it tomorrow.",
    )
    result = MeetingIntelligenceEngine().analyse(request)

    store.put(request.meeting_id, result)
    restored = store.get(request.meeting_id)

    assert store.ready() is True
    assert restored is not None
    assert restored.meeting_id == result.meeting_id
    assert restored.model_dump() == result.model_dump()
