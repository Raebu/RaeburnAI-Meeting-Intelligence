import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  approvalQueueStats,
  integrationLabel,
  pendingCommands,
} from '../lib/approval-model.mjs';

const meeting = {
  meeting_id: 'meeting-1',
  integration_commands: [
    {
      id: 'one',
      system: 'github',
      operation: 'create_task',
      approval_status: 'pending',
      payload: {},
    },
    {
      id: 'two',
      system: 'email',
      operation: 'draft_follow_up',
      approval_status: 'approved',
      payload: {},
    },
  ],
};

test('pendingCommands excludes already decided actions', () => {
  assert.deepEqual(
    pendingCommands(meeting).map((command) => command.id),
    ['one'],
  );
});

test('approvalQueueStats counts pending work rather than all commands', () => {
  assert.deepEqual(approvalQueueStats([meeting]), { meetings: 1, commands: 1 });
  assert.deepEqual(approvalQueueStats([]), { meetings: 0, commands: 0 });
});

test('integrationLabel keeps optional integrations generic', () => {
  assert.equal(integrationLabel('github'), 'GitHub');
  assert.equal(integrationLabel('crm'), 'CRM sync');
  assert.equal(integrationLabel('unknown-provider'), 'RaeburnAI action');
});
