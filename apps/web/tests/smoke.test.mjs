import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const page = readFileSync(new URL('../app/page.tsx', import.meta.url), 'utf8');

test('dashboard describes Meeting Intelligence positioning', () => {
  assert.match(page, /Meetings should update the business automatically/);
  assert.match(page, /Decision detection/);
  assert.match(page, /Human approval workflow/);
});
