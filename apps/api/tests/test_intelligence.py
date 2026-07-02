from datetime import datetime

from meeting_intelligence.intelligence import MeetingIntelligenceEngine
from meeting_intelligence.schemas import Attendee, MeetingAnalyseRequest, MeetingContext


def test_extracts_decisions_actions_and_commands() -> None:
    engine = MeetingIntelligenceEngine()
    request = MeetingAnalyseRequest(
        title="Customer implementation call",
        occurred_at=datetime(2026, 7, 2, 10, 0, 0),
        attendees=[Attendee(name="Sarah", email="sarah@example.com"), Attendee(name="Martin", email="martin@example.com")],
        context=MeetingContext(crm_account_id="acct_123", crm_deal_id="deal_456", repository="Raebu/example"),
        transcript=(
            "We decided to go with the phased rollout. "
            "Sarah will create a Jira ticket for the onboarding workflow by Friday. "
            "Martin will follow up with the customer about the deal next week."
        ),
    )

    result = engine.analyse(request)

    assert len(result.decisions) == 1
    assert "phased rollout" in result.decisions[0].statement
    assert len(result.action_items) == 2
    assert result.action_items[0].owner == "Sarah"
    assert result.crm_update is not None
    assert result.follow_up is not None
    assert any(command.system == "jira" for command in result.integration_commands)
    assert any(command.system == "crm" for command in result.integration_commands)
    assert any(command.system == "email" for command in result.integration_commands)
