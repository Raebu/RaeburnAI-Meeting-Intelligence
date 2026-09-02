export interface ApprovalCommand {
  id: string;
  system: string;
  operation: string;
  approval_status: string;
  payload: Record<string, unknown>;
}

export interface ApprovalMeeting {
  meeting_id: string;
  integration_commands: ApprovalCommand[];
  decisions?: unknown[];
  action_items?: unknown[];
}

export function pendingCommands(meeting: ApprovalMeeting): ApprovalCommand[];
export function approvalQueueStats(meetings: ApprovalMeeting[]): {
  meetings: number;
  commands: number;
};
export function integrationLabel(system: string): string;
