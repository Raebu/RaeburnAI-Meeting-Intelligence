from meeting_intelligence.config import get_settings
from meeting_intelligence.native_work import (
    NativeActionPatch,
    NativeActionStatus,
    NativeDecisionPatch,
    NativeDecisionStatus,
    NativeWorkStore,
)
from meeting_intelligence.schemas import (
    ActionItem,
    Decision,
    MeetingIntelligenceResult,
    Priority,
)


def _result(meeting_id: str) -> MeetingIntelligenceResult:
    return MeetingIntelligenceResult(
        meeting_id=meeting_id,
        decisions=[
            Decision(
                statement="Adopt RaeburnAI as the meeting source of truth",
                rationale="One authoritative operating layer",
                confidence=0.95,
            )
        ],
        action_items=[
            ActionItem(
                title="Ship native action tracking",
                description="Track the commitment inside RaeburnAI",
                owner="Martin",
                priority=Priority.high,
                confidence=0.92,
            )
        ],
        integration_commands=[],
        audit_events=[],
    )


def test_native_work_is_idempotent_and_workspace_scoped() -> None:
    store = NativeWorkStore(get_settings())
    result = _result("native-work-meeting")

    store.ingest("workspace-native", result)
    store.ingest("workspace-native", result)

    decisions = store.list_decisions("workspace-native")
    actions = store.list_actions("workspace-native")
    assert len(decisions) == 1
    assert len(actions) == 1
    assert store.list_actions("other-workspace") == []
    assert store.list_decisions("other-workspace") == []


def test_native_lifecycle_survives_reingestion() -> None:
    store = NativeWorkStore(get_settings())
    result = _result("native-lifecycle-meeting")
    store.ingest("workspace-lifecycle", result)

    decision = store.list_decisions("workspace-lifecycle")[0]
    action = store.list_actions("workspace-lifecycle")[0]

    updated_decision = store.update_decision(
        "workspace-lifecycle",
        decision.id,
        NativeDecisionPatch(status=NativeDecisionStatus.superseded),
    )
    updated_action = store.update_action(
        "workspace-lifecycle",
        action.id,
        NativeActionPatch(
            status=NativeActionStatus.done,
            outcome="Released and verified",
        ),
    )
    assert updated_decision is not None
    assert updated_decision.status is NativeDecisionStatus.superseded
    assert updated_action is not None
    assert updated_action.status is NativeActionStatus.done
    assert updated_action.outcome == "Released and verified"

    store.ingest("workspace-lifecycle", result)
    assert (
        store.list_decisions("workspace-lifecycle")[0].status
        is NativeDecisionStatus.superseded
    )
    reloaded_action = store.list_actions("workspace-lifecycle")[0]
    assert reloaded_action.status is NativeActionStatus.done
    assert reloaded_action.outcome == "Released and verified"


def test_native_work_deletes_with_source_meeting() -> None:
    store = NativeWorkStore(get_settings())
    result = _result("native-delete-meeting")
    store.ingest("workspace-delete", result)

    store.delete_meeting("workspace-delete", result.meeting_id)

    assert store.list_decisions("workspace-delete") == []
    assert store.list_actions("workspace-delete") == []
