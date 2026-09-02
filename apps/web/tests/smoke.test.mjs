import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const page = readFileSync(new URL('../app/page.tsx', import.meta.url), 'utf8');
const apiClient = readFileSync(
  new URL('../lib/meeting-api.ts', import.meta.url),
  'utf8',
);

test('dashboard is positioned as a native RaeburnAI approval centre', () => {
  assert.match(page, /RaeburnAI native workspace/);
  assert.match(page, /Approval centre/);
  assert.match(page, /optional destinations rather than the product&apos;s source of truth/);
});

test('dashboard authentication remains server-side and fails closed', () => {
  assert.match(apiClient, /RAEBURN_DASHBOARD_API_KEY/);
  assert.doesNotMatch(apiClient, /NEXT_PUBLIC_.*API_KEY/);
  assert.match(page, /The credential is never sent to the browser/);
  assert.match(page, /No action has been approved or dispatched/);
});
