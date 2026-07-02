# RaeburnAI Meeting Intelligence

[![CI](https://github.com/Raebu/RaeburnAI-Meeting-Intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/Raebu/RaeburnAI-Meeting-Intelligence/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-production--foundation-brightgreen.svg)](docs/PRODUCTION_TODOS.md)

## 1. Project name

**RaeburnAI Meeting Intelligence**

## 2. One-line positioning statement

Meeting intelligence that turns conversations into decisions, owners, approved actions, CRM updates and delivery tasks.

## 3. Short product description

RaeburnAI Meeting Intelligence is not another transcription archive. It analyses meeting transcripts and notes to detect decisions, extract action items, assign owners, prepare follow-ups, create approval-gated integration commands, and update operational systems such as CRMs, Jira and GitHub once approved.

## 4. Part of the RaeburnAI Platform

RaeburnAI is an open, modular enterprise AI platform for building commercially credible AI operations, governance, workflow automation and decision intelligence systems.

Each RaeburnAI module follows the same operating model: secure-by-default architecture, auditable AI workflows, human approval for risky actions, production-grade deployment patterns, consistent documentation, and practical business value rather than demo-only AI.

### RaeburnAI ecosystem map

```text
RaeburnAI Platform
├── RaeburnAI Compliance Engine        AI governance, GDPR, ISO and EU AI Act controls
├── Universal AI Knowledge Graph       Shared organisational knowledge and relationship layer
├── RaeburnAI Business Twin            Business simulation, planning and operational intelligence
├── RaeburnAI Executive Briefing       Board-level reporting and decision support
├── OpenAI Operations Dashboard        AI usage, spend, latency, safety and audit observability
├── RaeburnAI Proposal Generator       Consultant proposal, roadmap, pricing and ROI generation
├── RaeburnAI Workflow Auditor         SOP/process analysis and automation opportunity mapping
├── RaeburnAI Meeting Intelligence     Meeting decisions, actions, owners and writebacks
└── RaeburnAI Chain                    Cross-module orchestration layer
```

### Core project links

- [RaeburnAI Compliance Engine](https://github.com/Raebu/RaeburnAI-Compliance-Engine)
- [Universal AI Knowledge Graph](https://github.com/Raebu/Universal-AI-Knowledge-Graph)
- [RaeburnAI Business Twin](https://github.com/Raebu/RaeburnAI-Business-Twin)
- [RaeburnAI Executive Briefing](https://github.com/Raebu/RaeburnAI-Executive-Briefing)
- [OpenAI Operations Dashboard](https://github.com/Raebu/OpenAI-Operations-Dashboard)
- [RaeburnAI Proposal Generator](https://github.com/Raebu/RaeburnAI-Proposal-Generator)
- [RaeburnAI Workflow Auditor](https://github.com/Raebu/RaeburnAI-Workflow-Auditor)
- [RaeburnAI Chain](https://github.com/Raebu/RaeburnAI-Chain)

## 5. Core features

- Decision detection from transcripts and notes.
- Action extraction with owner, due date, priority and confidence.
- Owner inference from attendee context and explicit transcript mentions.
- CRM update preparation for account/deal notes and next steps.
- Jira and GitHub task command generation.
- Follow-up email drafting.
- Human approval workflow before external writebacks.
- Structured audit events for sensitive actions.
- Deterministic local extraction mode for private/offline development.
- Integration adapter interfaces for GitHub, Jira, CRM, email and webhooks.
- API health and readiness endpoints.
- Dashboard shell for product positioning and future approval queue.

## 6. Architecture

```text
apps/api        FastAPI service, schemas, extraction engine and approval endpoints
apps/web        Next.js dashboard shell
packages/sdk    Python SDK client
docs            architecture, deployment, screenshots and production TODOs
.github         CI, CodeQL and dependency review
```

Core workflow:

```text
Transcript / notes
  -> extraction engine
  -> decisions + actions + owners + CRM update + follow-up
  -> approval-gated integration commands
  -> GitHub / Jira / CRM / email / webhook writeback
  -> audit trail
```

More detail: [Architecture documentation](docs/ARCHITECTURE.md)

## 7. Quick start

```bash
cp .env.example .env
docker compose up --build
```

API documentation: `http://localhost:8080/docs`

Dashboard: `http://localhost:3000`

Local API development:

```bash
cd apps/api
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
uvicorn meeting_intelligence.main:app --reload --port 8080
```

Local web development:

```bash
cd apps/web
npm install
npm run dev
```

Root commands:

```bash
make install
make lint
make typecheck
make test
make build
make docker-build
```

## 8. Environment variables

See [.env.example](.env.example) for the full template.

| Variable | Purpose |
| --- | --- |
| `RAEBURN_ENV` | Runtime environment. |
| `RAEBURN_API_KEY` | API key for protected endpoints outside local development. |
| `RAEBURN_CORS_ORIGINS` | Comma-separated allowed browser origins. |
| `RAEBURN_RATE_LIMIT_PER_MINUTE` | Basic per-client API rate limit. |
| `DATABASE_URL` | Postgres connection string. |
| `REDIS_URL` | Redis connection string for future queue/cache use. |
| `LLM_PROVIDER` | `deterministic` or future OpenAI-compatible provider. |
| `APPROVALS_REQUIRED` | Keeps risky writebacks pending by default. |
| `GITHUB_WRITEBACK_ENABLED` | Enables GitHub issue dispatch when configured. |
| `JIRA_WRITEBACK_ENABLED` | Enables Jira issue dispatch when configured. |
| `CRM_WRITEBACK_ENABLED` | Enables CRM update dispatch when configured. |
| `EMAIL_FOLLOWUP_ENABLED` | Enables email follow-up sending when configured. |

## 9. Usage examples

Analyse a meeting:

```bash
curl -X POST http://localhost:8080/v1/meetings/analyse \
  -H 'content-type: application/json' \
  -d @examples/meeting-request.json
```

Health checks:

```bash
curl http://localhost:8080/healthz
curl http://localhost:8080/readyz
```

Python SDK:

```python
from meeting_intelligence_sdk import MeetingIntelligenceClient

client = MeetingIntelligenceClient('http://localhost:8080')
```

## 10. Security model

- API key protection is required outside local development.
- CORS is configured with `RAEBURN_CORS_ORIGINS` rather than wildcard origins.
- Basic request rate limiting is enabled at the API edge.
- Human approval is required by default for risky external writebacks.
- Integration tokens are disabled unless explicitly configured.
- Audit events are created for analysis, approval and rejection actions.
- Secrets belong in environment variables or a secret manager, never source control.
- Deterministic mode allows private/local use without sending transcripts to third-party LLMs.

See [SECURITY.md](SECURITY.md) and [Production TODOs](docs/PRODUCTION_TODOS.md).

## 11. Production readiness

Included:

- FastAPI backend with Pydantic validation.
- Health and readiness endpoints.
- Structured logging and safe error handling.
- Approval-first integration command model.
- GitHub, Jira and webhook adapter interfaces.
- Next.js dashboard shell.
- Python SDK.
- Dockerfiles and Docker Compose.
- CI with linting, type checking, tests, Docker build, CodeQL and dependency review.
- Unit, integration and smoke tests.
- Deployment, architecture, security and screenshot documentation.

Honest limitations before enterprise customer deployment:

- Meeting results are currently stored in memory and must be moved to Postgres persistence.
- Dispatch should be moved to a queue-backed worker.
- Dashboard needs authenticated approval queue screens.
- CRM adapters require real HubSpot/Salesforce implementation and credentials.
- SSO/RBAC is not yet implemented.

See [Production TODOs](docs/PRODUCTION_TODOS.md).

## 12. Roadmap

See [ROADMAP.md](ROADMAP.md).

Near-term priorities:

- Postgres persistence and migrations.
- Queue-backed dispatch worker.
- HubSpot and Salesforce adapters.
- Dashboard approval queue.
- RBAC and organisation model.
- Extraction evaluation harness.

## 13. Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and keep the approval-first security model intact.

## 14. Licence

Licensed under the [Apache License 2.0](LICENSE).
