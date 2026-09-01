from meeting_intelligence.main import analyse_meeting, get_meeting_result
from meeting_intelligence.schemas import MeetingAnalyseRequest


def _request(meeting_id: str) -> MeetingAnalyseRequest:
    return MeetingAnalyseRequest(
        meeting_id=meeting_id,
        title="State isolation test",
        transcript="We decided to create a GitHub issue. Sarah will create it by Friday.",
        attendees=[{"name": "Sarah", "email": "sarah@example.com"}],
        context={"repository": "Raebu/example"},
    )


def test_analysis_response_does_not_alias_stored_result() -> None:
    meeting_id = "test-analysis-response-isolation"
    response_result = analyse_meeting(_request(meeting_id))
    response_result.audit_events.append("response-only-mutation")

    stored = get_meeting_result(meeting_id)

    assert "response-only-mutation" not in stored.audit_events


def test_get_response_does_not_alias_stored_result() -> None:
    meeting_id = "test-get-response-isolation"
    analyse_meeting(_request(meeting_id))

    first_read = get_meeting_result(meeting_id)
    first_read.audit_events.append("read-only-mutation")
    second_read = get_meeting_result(meeting_id)

    assert "read-only-mutation" not in second_read.audit_events
