from __future__ import annotations

import json
from collections.abc import Iterable
from uuid import UUID

from meeting_intelligence.database import (
    AuditEventRecord,
    MeetingResultRecord,
    lock_result,
    session_scope,
)
from meeting_intelligence.schemas import ApprovalStatus, MeetingIntelligenceResult


class MeetingResultRepository:
    def save_analysis(self, result: MeetingIntelligenceResult) -> MeetingIntelligenceResult:
        with session_scope() as session:
            record = lock_result(session, result.meeting_id)
            if record is None:
                record = MeetingResultRecord(
                    meeting_id=result.meeting_id,
                    result_json=result.model_dump_json(),
                )
                session.add(record)
            else:
                record.result_json = result.model_dump_json()
                record.revision += 1
            session.add(
                AuditEventRecord(
                    meeting_id=result.meeting_id,
                    action="meeting.analysis.saved",
                    details_json=json.dumps(
                        {
                            "decisions": len(result.decisions),
                            "actions": len(result.action_items),
                            "commands": len(result.integration_commands),
                            "revision": record.revision,
                        },
                        sort_keys=True,
                    ),
                )
            )
        return result

    def get(self, meeting_id: str) -> MeetingIntelligenceResult | None:
        with session_scope() as session:
            record = session.get(MeetingResultRecord, meeting_id)
            if record is None:
                return None
            return MeetingIntelligenceResult.model_validate_json(record.result_json)

    def update_approval(
        self,
        meeting_id: str,
        command_ids: Iterable[UUID],
        approval_status: ApprovalStatus,
        actor: str,
        reason: str | None,
    ) -> MeetingIntelligenceResult | None:
        requested_ids = set(command_ids)
        with session_scope() as session:
            record = lock_result(session, meeting_id)
            if record is None:
                return None

            result = MeetingIntelligenceResult.model_validate_json(record.result_json)
            matched_ids: set[UUID] = set()
            for command in result.integration_commands:
                if command.id in requested_ids:
                    command.approval_status = approval_status
                    matched_ids.add(command.id)

            missing_ids = sorted(str(command_id) for command_id in requested_ids - matched_ids)
            if missing_ids:
                raise ValueError(f"Unknown command IDs: {', '.join(missing_ids)}")

            action = f"commands.{approval_status.value}"
            result.audit_events.append(f"{action}_by:{actor}")
            record.result_json = result.model_dump_json()
            record.revision += 1
            session.add(
                AuditEventRecord(
                    meeting_id=meeting_id,
                    action=action,
                    actor=actor,
                    details_json=json.dumps(
                        {
                            "command_ids": sorted(str(command_id) for command_id in requested_ids),
                            "reason": reason,
                            "revision": record.revision,
                        },
                        sort_keys=True,
                    ),
                )
            )
            return result
