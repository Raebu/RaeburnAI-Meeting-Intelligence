from datetime import datetime

from meeting_intelligence.evaluation import ExtractionExpectation, evaluate_extraction
from meeting_intelligence.intelligence import MeetingIntelligenceEngine
from meeting_intelligence.schemas import (
    Attendee,
    MeetingAnalyseRequest,
    MeetingContext,
)


def _benchmark_cases() -> list[tuple[MeetingAnalyseRequest, ExtractionExpectation]]:
    return [
        (
            MeetingAnalyseRequest(
                title="Implementation planning",
                occurred_at=datetime(2026, 7, 2, 10, 0, 0),
                attendees=[
                    Attendee(name="Sarah", email="sarah@example.com"),
                    Attendee(name="Martin", email="martin@example.com"),
                ],
                context=MeetingContext(
                    crm_account_id="acct_123",
                    crm_deal_id="deal_456",
                    repository="Raebu/example",
                ),
                transcript=(
                    "We decided to go with the phased rollout. "
                    "Sarah will create a Jira ticket for onboarding by Friday. "
                    "Martin will follow up with the customer about the deal next week."
                ),
            ),
            ExtractionExpectation(
                decision_fragments=("phased rollout",),
                action_fragments=("Jira ticket", "follow up with the customer"),
                owners=("Sarah", "Martin"),
                systems=("jira", "crm"),
            ),
        ),
        (
            MeetingAnalyseRequest(
                title="Release decision",
                occurred_at=datetime(2026, 7, 6, 9, 0, 0),
                attendees=[Attendee(name="Alex", email="alex@example.com")],
                context=MeetingContext(repository="Raebu/product"),
                transcript=(
                    "Decision: launch the release on Monday. "
                    "Alex will open a GitHub issue tomorrow."
                ),
            ),
            ExtractionExpectation(
                decision_fragments=("launch the release",),
                action_fragments=("GitHub issue",),
                owners=("Alex",),
                systems=("github",),
            ),
        ),
        (
            MeetingAnalyseRequest(
                title="Discovery discussion",
                occurred_at=datetime(2026, 7, 8, 14, 0, 0),
                attendees=[Attendee(name="Jo", email="jo@example.com")],
                context=MeetingContext(),
                transcript=(
                    "The team discussed customer feedback and current architecture. "
                    "No commitments were made during this session."
                ),
            ),
            ExtractionExpectation(),
        ),
        (
            MeetingAnalyseRequest(
                title="Customer follow-up",
                occurred_at=datetime(2026, 7, 9, 11, 0, 0),
                attendees=[Attendee(name="Priya", email="priya@example.com")],
                context=MeetingContext(),
                transcript="Priya needs to follow up with the customer next week.",
            ),
            ExtractionExpectation(
                action_fragments=("follow up with the customer",),
                owners=("Priya",),
                systems=("crm",),
            ),
        ),
    ]


def test_extraction_quality_gate() -> None:
    engine = MeetingIntelligenceEngine()

    for meeting_request, expectation in _benchmark_cases():
        quality = evaluate_extraction(engine.analyse(meeting_request), expectation)

        assert quality.score >= 0.95
        assert quality.precision_proxy >= 0.95
        assert quality.decision_recall >= 0.90
        assert quality.action_recall >= 0.90
        assert quality.owner_recall >= 0.90
        assert quality.system_recall >= 0.90
