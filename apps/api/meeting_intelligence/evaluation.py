from __future__ import annotations

from dataclasses import dataclass

from meeting_intelligence.schemas import MeetingIntelligenceResult


@dataclass(frozen=True)
class ExtractionExpectation:
    """Expected semantic signals for one benchmark meeting."""

    decision_fragments: tuple[str, ...] = ()
    action_fragments: tuple[str, ...] = ()
    owners: tuple[str, ...] = ()
    systems: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractionQuality:
    decision_recall: float
    action_recall: float
    owner_recall: float
    system_recall: float
    precision_proxy: float

    @property
    def score(self) -> float:
        values = [
            self.decision_recall,
            self.action_recall,
            self.owner_recall,
            self.system_recall,
            self.precision_proxy,
        ]
        return round(sum(values) / len(values), 4)


def _recall(expected: tuple[str, ...], actual: list[str]) -> float:
    if not expected:
        return 1.0

    lowered = [value.lower() for value in actual]
    matched = 0
    for fragment in expected:
        if any(fragment.lower() in value for value in lowered):
            matched += 1
    return matched / len(expected)


def evaluate_extraction(
    result: MeetingIntelligenceResult,
    expectation: ExtractionExpectation,
) -> ExtractionQuality:
    """Score deterministic extraction output for release gating in CI."""

    decisions = [item.statement for item in result.decisions]
    actions = [item.description for item in result.action_items]
    owners = [item.owner for item in result.action_items if item.owner]
    systems = sorted(
        {
            command.system
            for command in result.integration_commands
            if command.system != "email"
        }
    )

    expected_semantic_items = len(expectation.decision_fragments) + len(
        expectation.action_fragments
    )
    actual_semantic_items = len(decisions) + len(actions)
    unexpected = max(actual_semantic_items - expected_semantic_items, 0)

    precision_proxy = 1.0
    if actual_semantic_items:
        precision_proxy = max(0.0, 1.0 - unexpected / actual_semantic_items)

    return ExtractionQuality(
        decision_recall=_recall(expectation.decision_fragments, decisions),
        action_recall=_recall(expectation.action_fragments, actions),
        owner_recall=_recall(expectation.owners, owners),
        system_recall=_recall(expectation.systems, systems),
        precision_proxy=precision_proxy,
    )
