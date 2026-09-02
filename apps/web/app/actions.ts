'use server';

import { revalidatePath } from 'next/cache';

import { decideCommands } from '../lib/meeting-api';

async function decide(formData: FormData, decision: 'approve' | 'reject') {
  const meetingId = formData.get('meetingId');
  const commandIds = formData.getAll('commandId');
  if (typeof meetingId !== 'string' || !meetingId) {
    throw new Error('meeting-id-required');
  }
  const safeCommandIds = commandIds.filter(
    (value): value is string => typeof value === 'string' && value.length > 0,
  );
  if (safeCommandIds.length === 0) {
    throw new Error('command-id-required');
  }
  await decideCommands(meetingId, safeCommandIds, decision);
  revalidatePath('/');
}

export async function approveCommands(formData: FormData) {
  await decide(formData, 'approve');
}

export async function rejectCommands(formData: FormData) {
  await decide(formData, 'reject');
}
