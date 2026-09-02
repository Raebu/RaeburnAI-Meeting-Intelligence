from meeting_intelligence.auth import Principal, WorkspaceRole
from meeting_intelligence.main import analyse_meeting, get_meeting_result
from meeting_intelligence.schemas import MeetingAnalyseRequest

TEST_PRINCIPAL = Principal(
    workspace_id="default",
    role=WorkspaceRole.admin,
    subject="state-isolation-test",
)


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
    response_result = analyse_meeting(_request(meeting_id), TEST_PRINCIPAL)
    response_result.audit_events.append("response-only-mutation")

    stored = get_meeting_result(meeting_id, TEST_PRINCIPAL)

    assert "response-only-mutation" not in stored.audit_events


def test_get_response_does_not_alias_stored_result() -> None:
    meeting_id = "test-get-response-isolation"
    analyse_meeting(_request(meeting_id), TEST_PRINCIPAL)

    first_read = get_meeting_result(meeting_id, TEST_PRINCIPAL)
    first_read.audit_events.append("read-only-mutation")
    second_read = get_meeting_result(meeting_id, TEST_PRINCIPAL)

    assert "read-only-mutation" not in second_read.audit_events
