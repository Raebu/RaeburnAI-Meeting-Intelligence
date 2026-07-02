const features = [
  'Decision detection',
  'Action extraction',
  'Owner assignment',
  'CRM update preparation',
  'Jira/GitHub task creation',
  'Human approval workflow',
];

export default function Page() {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <section className="mx-auto flex max-w-6xl flex-col gap-10 px-6 py-16">
        <div className="rounded-3xl border border-blue-400/30 bg-white/5 p-10 shadow-2xl shadow-blue-950/30">
          <p className="mb-4 text-sm font-semibold uppercase tracking-[0.3em] text-blue-300">
            RaeburnAI Meeting Intelligence
          </p>
          <h1 className="max-w-4xl text-5xl font-black tracking-tight md:text-7xl">
            Meetings should update the business automatically.
          </h1>
          <p className="mt-6 max-w-3xl text-lg text-slate-300">
            Detect decisions, extract actions, assign owners, prepare CRM updates, create Jira/GitHub tasks and draft follow-ups with approval-first governance.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {features.map((feature) => (
            <div key={feature} className="rounded-2xl border border-white/10 bg-white/[0.04] p-6">
              <div className="mb-4 h-2 w-12 rounded-full bg-blue-300" />
              <h2 className="text-xl font-bold">{feature}</h2>
              <p className="mt-2 text-sm text-slate-400">
                Built as an auditable, integration-ready workflow step rather than another transcript archive.
              </p>
            </div>
          ))}
        </div>

        <div className="rounded-2xl border border-white/10 bg-slate-900 p-6">
          <h2 className="text-2xl font-bold">Operational pipeline</h2>
          <ol className="mt-4 grid gap-3 text-slate-300 md:grid-cols-5">
            <li>1. Ingest transcript</li>
            <li>2. Extract intelligence</li>
            <li>3. Review approvals</li>
            <li>4. Dispatch updates</li>
            <li>5. Audit outcomes</li>
          </ol>
        </div>
      </section>
    </main>
  );
}
