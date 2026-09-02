import {
  approvalQueueStats,
  integrationLabel,
  pendingCommands,
} from '../lib/approval-model.mjs';
import {
  currentPrincipal,
  dashboardConfigured,
  pendingApprovals,
} from '../lib/meeting-api';
import { approveCommands, rejectCommands } from './actions';

export const dynamic = 'force-dynamic';

function payloadSummary(payload: Record<string, unknown>): string {
  const action = payload.action;
  if (action && typeof action === 'object') {
    const title = (action as Record<string, unknown>).title;
    if (typeof title === 'string' && title) return title;
  }
  const subject = payload.subject;
  if (typeof subject === 'string' && subject) return subject;
  return 'Review the proposed action before it leaves RaeburnAI.';
}

export default async function Page() {
  if (!dashboardConfigured()) {
    return (
      <main className="min-h-screen bg-slate-950 px-6 py-16 text-white">
        <section className="mx-auto max-w-4xl rounded-3xl border border-amber-300/30 bg-amber-300/5 p-8">
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-amber-200">
            RaeburnAI Meeting Intelligence
          </p>
          <h1 className="mt-4 text-4xl font-black">Approval centre is locked</h1>
          <p className="mt-4 max-w-2xl text-slate-300">
            Configure a server-side RAEBURN_DASHBOARD_API_KEY (or RAEBURN_API_KEY)
            before this workspace console can read or approve meeting actions. The
            credential is never sent to the browser.
          </p>
        </section>
      </main>
    );
  }

  try {
    const [principal, meetings] = await Promise.all([
      currentPrincipal(),
      pendingApprovals(),
    ]);
    const stats = approvalQueueStats(meetings);

    return (
      <main className="min-h-screen bg-slate-950 text-white">
        <section className="mx-auto flex max-w-7xl flex-col gap-8 px-6 py-12">
          <header className="rounded-3xl border border-cyan-300/20 bg-white/[0.04] p-8 shadow-2xl shadow-cyan-950/20">
            <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.3em] text-cyan-300">
                  RaeburnAI native workspace
                </p>
                <h1 className="mt-3 text-4xl font-black tracking-tight md:text-6xl">
                  Approval centre
                </h1>
                <p className="mt-4 max-w-3xl text-slate-300">
                  Review what RaeburnAI intends to do, approve only the actions you
                  trust, and keep external systems as optional destinations rather
                  than the product&apos;s source of truth.
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-slate-900/80 px-5 py-4 text-sm text-slate-300">
                <p className="font-semibold text-white">{principal.subject}</p>
                <p>{principal.workspace_id}</p>
                <p className="mt-1 uppercase tracking-wider text-cyan-300">
                  {principal.role}
                </p>
              </div>
            </div>
          </header>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-6">
              <p className="text-sm uppercase tracking-widest text-slate-400">
                Meetings awaiting review
              </p>
              <p className="mt-2 text-4xl font-black">{stats.meetings}</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-6">
              <p className="text-sm uppercase tracking-widest text-slate-400">
                Pending actions
              </p>
              <p className="mt-2 text-4xl font-black">{stats.commands}</p>
            </div>
          </div>

          {meetings.length === 0 ? (
            <div className="rounded-3xl border border-emerald-300/20 bg-emerald-300/5 p-10 text-center">
              <h2 className="text-2xl font-bold">Nothing is waiting for approval</h2>
              <p className="mt-2 text-slate-300">
                New decisions and actions will appear here before any external
                writeback can run.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {meetings.map((meeting) => {
                const commands = pendingCommands(meeting);
                return (
                  <article
                    key={meeting.meeting_id}
                    className="rounded-3xl border border-white/10 bg-slate-900/70 p-6"
                  >
                    <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-300">
                          Meeting
                        </p>
                        <h2 className="mt-1 text-2xl font-bold">{meeting.meeting_id}</h2>
                      </div>
                      <p className="rounded-full border border-white/10 px-3 py-1 text-sm text-slate-300">
                        {commands.length} pending
                      </p>
                    </div>

                    <div className="mt-5 space-y-3">
                      {commands.map((command) => (
                        <div
                          key={command.id}
                          className="rounded-2xl border border-white/10 bg-black/20 p-5"
                        >
                          <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                            <div>
                              <p className="font-semibold text-white">
                                {integrationLabel(command.system)} · {command.operation}
                              </p>
                              <p className="mt-2 text-sm text-slate-300">
                                {payloadSummary(command.payload)}
                              </p>
                            </div>
                            <code className="text-xs text-slate-500">{command.id}</code>
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="mt-6 grid gap-3 sm:grid-cols-2">
                      <form action={approveCommands}>
                        <input type="hidden" name="meetingId" value={meeting.meeting_id} />
                        {commands.map((command) => (
                          <input
                            key={command.id}
                            type="hidden"
                            name="commandId"
                            value={command.id}
                          />
                        ))}
                        <button
                          type="submit"
                          className="min-h-11 w-full rounded-xl bg-emerald-400 px-5 py-3 font-bold text-slate-950 transition hover:bg-emerald-300"
                        >
                          Approve all pending actions
                        </button>
                      </form>
                      <form action={rejectCommands}>
                        <input type="hidden" name="meetingId" value={meeting.meeting_id} />
                        {commands.map((command) => (
                          <input
                            key={command.id}
                            type="hidden"
                            name="commandId"
                            value={command.id}
                          />
                        ))}
                        <button
                          type="submit"
                          className="min-h-11 w-full rounded-xl border border-rose-300/40 px-5 py-3 font-bold text-rose-200 transition hover:bg-rose-300/10"
                        >
                          Reject all pending actions
                        </button>
                      </form>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </main>
    );
  } catch {
    return (
      <main className="min-h-screen bg-slate-950 px-6 py-16 text-white">
        <section className="mx-auto max-w-4xl rounded-3xl border border-rose-300/30 bg-rose-300/5 p-8">
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-rose-200">
            RaeburnAI Meeting Intelligence
          </p>
          <h1 className="mt-4 text-4xl font-black">Approval service unavailable</h1>
          <p className="mt-4 text-slate-300">
            The console failed closed. No action has been approved or dispatched.
            Check the API readiness endpoint and dashboard credential configuration.
          </p>
        </section>
      </main>
    );
  }
}
