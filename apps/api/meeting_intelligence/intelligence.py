from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from dateutil.parser import parse as parse_datetime

from meeting_intelligence.schemas import (
    ActionItem,
    CrmUpdate,
    Decision,
    FollowUp,
    IntegrationCommand,
    MeetingAnalyseRequest,
    MeetingIntelligenceResult,
    Priority,
)


@dataclass(frozen=True)
class ExtractionSignals:
    decision_markers: tuple[str, ...] = (
        "we decided",
        "decision:",
        "agreed that",
        "we agreed",
        "approved",
        "signed off",
        "go with",
    )
    action_markers: tuple[str, ...] = (
        "action:",
        "todo:",
        "next step",
        "follow up",
        "will",
        "needs to",
        "can you",
        "please",
    )


class MeetingIntelligenceEngine:
    """Extraction engine with deterministic fallback.

    The deterministic extractor makes the product useful in development, tests and private deployments
    without sending transcripts to a third-party LLM. Production deployments can wrap this class with an
    LLM adapter and keep the same output contract.
    """

    def __init__(self, signals: ExtractionSignals | None = None) -> None:
        self.signals = signals or ExtractionSignals()

    def analyse(self, request: MeetingAnalyseRequest) -> MeetingIntelligenceResult:
        sentences = self._split_sentences(request.transcript)
        decisions = self._extract_decisions(sentences)
        actions = self._extract_actions(sentences, request)
        crm_update = self._build_crm_update(request, decisions, actions)
        follow_up = self._build_follow_up(request, decisions, actions)
        commands = self._build_integration_commands(request, actions, crm_update, follow_up)

        return MeetingIntelligenceResult(
            meeting_id=request.meeting_id,
            decisions=decisions,
            action_items=actions,
            crm_update=crm_update,
            follow_up=follow_up,
            integration_commands=commands,
            audit_events=[
                "meeting.ingested",
                f"decisions.detected:{len(decisions)}",
                f"actions.detected:{len(actions)}",
                f"integration_commands.created:{len(commands)}",
            ],
        )

    def _split_sentences(self, transcript: str) -> list[str]:
        parts = re.split(r"(?<=[.!?])\s+|\n+", transcript.strip())
        return [part.strip(" -\t") for part in parts if part.strip()]

    def _extract_decisions(self, sentences: list[str]) -> list[Decision]:
        decisions: list[Decision] = []
        for sentence in sentences:
            lowered = sentence.lower()
            if any(marker in lowered for marker in self.signals.decision_markers):
                decisions.append(
                    Decision(
                        statement=self._clean_marker(sentence),
                        rationale="Detected from explicit decision language.",
                        confidence=0.82,
                        evidence=sentence,
                    )
                )
        return decisions

    def _extract_actions(
        self, sentences: list[str], request: MeetingAnalyseRequest
    ) -> list[ActionItem]:
        attendee_lookup = {attendee.name.lower(): attendee for attendee in request.attendees}
        actions: list[ActionItem] = []
        for sentence in sentences:
            lowered = sentence.lower()
            if not any(marker in lowered for marker in self.signals.action_markers):
                continue
            owner_name, owner_email = self._infer_owner(sentence, attendee_lookup)
            due_date = self._infer_due_date(sentence, request.occurred_at)
            actions.append(
                ActionItem(
                    title=self._title_from_sentence(sentence),
                    description=self._clean_marker(sentence),
                    owner=owner_name,
                    owner_email=owner_email,
                    due_date=due_date,
                    priority=self._infer_priority(sentence),
                    confidence=0.78 if owner_name else 0.64,
                    evidence=sentence,
                    suggested_systems=self._suggest_systems(sentence),
                )
            )
        return actions

    def _infer_owner(
        self, sentence: str, attendee_lookup: dict[str, object]
    ) -> tuple[str | None, str | None]:
        lowered = sentence.lower()
        for name, attendee in attendee_lookup.items():
            if name in lowered:
                return getattr(attendee, "name"), getattr(attendee, "email")
        match = re.search(r"\b([A-Z][a-z]+)\b\s+(?:will|to|can|should|needs)", sentence)
        if match:
            return match.group(1), None
        return None, None

    def _infer_due_date(self, sentence: str, occurred_at: datetime) -> datetime | None:
        lowered = sentence.lower()
        if "tomorrow" in lowered:
            return occurred_at + timedelta(days=1)
        if "next week" in lowered:
            return occurred_at + timedelta(days=7)
        if "friday" in lowered:
            return occurred_at + timedelta(days=(4 - occurred_at.weekday()) % 7 or 7)
        date_match = re.search(r"\b(?:by|on|before)\s+([A-Za-z]+\s+\d{1,2}(?:,\s*\d{4})?)", sentence)
        if date_match:
            try:
                return parse_datetime(date_match.group(1), default=occurred_at)
            except (ValueError, OverflowError):
                return None
        return None

    def _infer_priority(self, sentence: str) -> Priority:
        lowered = sentence.lower()
        if any(word in lowered for word in ("urgent", "critical", "blocked", "escalate")):
            return Priority.critical
        if any(word in lowered for word in ("important", "high priority", "risk")):
            return Priority.high
        if any(word in lowered for word in ("nice to have", "low priority")):
            return Priority.low
        return Priority.medium

    def _suggest_systems(self, sentence: str) -> list[str]:
        lowered = sentence.lower()
        systems: list[str] = []
        if any(word in lowered for word in ("bug", "issue", "repo", "github", "pull request")):
            systems.append("github")
        if any(word in lowered for word in ("jira", "sprint", "ticket", "backlog")):
            systems.append("jira")
        if any(word in lowered for word in ("customer", "deal", "crm", "account", "lead")):
            systems.append("crm")
        if "follow up" in lowered or "email" in lowered:
            systems.append("email")
        return systems or ["task"]

    def _build_crm_update(
        self, request: MeetingAnalyseRequest, decisions: list[Decision], actions: list[ActionItem]
    ) -> CrmUpdate | None:
        if not request.context.crm_account_id and not request.context.crm_deal_id:
            return None
        next_step = actions[0].title if actions else None
        risk = "No owner assigned to at least one action." if any(a.owner is None for a in actions) else None
        return CrmUpdate(
            account_id=request.context.crm_account_id,
            deal_id=request.context.crm_deal_id,
            summary=(
                f"Meeting '{request.title}' produced {len(decisions)} decisions and "
                f"{len(actions)} action items."
            ),
            next_step=next_step,
            risk=risk,
            confidence=0.8,
        )

    def _build_follow_up(
        self, request: MeetingAnalyseRequest, decisions: list[Decision], actions: list[ActionItem]
    ) -> FollowUp:
        recipients = [attendee.email for attendee in request.attendees if attendee.email]
        decision_lines = "\n".join(f"- {decision.statement}" for decision in decisions) or "- No explicit decisions detected."
        action_lines = "\n".join(
            f"- {action.title} — owner: {action.owner or 'Unassigned'}" for action in actions
        ) or "- No explicit actions detected."
        body = (
            f"Thanks for joining {request.title}.\n\n"
            f"Decisions\n{decision_lines}\n\n"
            f"Actions\n{action_lines}\n\n"
            "Please reply with any corrections before these are pushed into connected systems."
        )
        return FollowUp(subject=f"Follow-up: {request.title}", body=body, recipients=recipients)

    def _build_integration_commands(
        self,
        request: MeetingAnalyseRequest,
        actions: list[ActionItem],
        crm_update: CrmUpdate | None,
        follow_up: FollowUp,
    ) -> list[IntegrationCommand]:
        commands: list[IntegrationCommand] = []
        for action in actions:
            for system in action.suggested_systems:
                if system == "task":
                    continue
                commands.append(
                    IntegrationCommand(
                        system=system,
                        operation="create_task" if system in {"github", "jira"} else "update_record",
                        payload={"meeting_id": request.meeting_id, "action": action.model_dump(mode="json")},
                    )
                )
        if crm_update:
            commands.append(
                IntegrationCommand(
                    system="crm",
                    operation="update_meeting_summary",
                    payload=crm_update.model_dump(mode="json"),
                )
            )
        commands.append(
            IntegrationCommand(
                system="email",
                operation="draft_follow_up",
                payload=follow_up.model_dump(mode="json"),
            )
        )
        return commands

    def _title_from_sentence(self, sentence: str) -> str:
        clean = self._clean_marker(sentence)
        return clean[:90].rstrip(" .")

    def _clean_marker(self, sentence: str) -> str:
        return re.sub(r"^(decision|action|todo|next step)\s*:\s*", "", sentence.strip(), flags=re.I)
