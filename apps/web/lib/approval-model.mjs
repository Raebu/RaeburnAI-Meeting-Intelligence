export function pendingCommands(meeting) {
  if (!meeting || !Array.isArray(meeting.integration_commands)) return [];
  return meeting.integration_commands.filter(
    (command) => command?.approval_status === 'pending',
  );
}

export function approvalQueueStats(meetings) {
  const safeMeetings = Array.isArray(meetings) ? meetings : [];
  return {
    meetings: safeMeetings.length,
    commands: safeMeetings.reduce(
      (total, meeting) => total + pendingCommands(meeting).length,
      0,
    ),
  };
}

export function integrationLabel(system) {
  const labels = {
    github: 'GitHub',
    jira: 'Jira',
    crm: 'CRM sync',
    email: 'Email',
    webhook: 'Webhook',
  };
  return labels[system] ?? 'RaeburnAI action';
}
