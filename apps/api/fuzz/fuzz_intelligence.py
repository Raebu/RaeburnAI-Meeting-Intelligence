import sys
from datetime import datetime

import atheris

with atheris.instrument_imports():
    from meeting_intelligence.intelligence import MeetingIntelligenceEngine
    from meeting_intelligence.schemas import (
        Attendee,
        MeetingAnalyseRequest,
        MeetingContext,
    )


engine = MeetingIntelligenceEngine()


def test_one_input(data: bytes) -> None:
    provider = atheris.FuzzedDataProvider(data)
    transcript = provider.ConsumeUnicodeNoSurrogates(16000)
    attendee_name = provider.ConsumeUnicodeNoSurrogates(120) or "Attendee"

    request = MeetingAnalyseRequest(
        title="Fuzzed meeting",
        occurred_at=datetime(2026, 1, 1, 12, 0, 0),
        attendees=[Attendee(name=attendee_name)],
        context=MeetingContext(),
        transcript=transcript,
    )
    result = engine.analyse(request)

    result.model_dump(mode="json")


def main() -> None:
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
