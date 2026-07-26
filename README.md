# RaeburnAI Meeting Intelligence

[![CI](https://github.com/Raebu/RaeburnAI-Meeting-Intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/Raebu/RaeburnAI-Meeting-Intelligence/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-production--candidate-orange.svg)](docs/PRODUCTION_TODOS.md)

Meeting intelligence that turns transcripts and notes into decisions, owners, approval-gated actions and auditable operational records.

RaeburnAI Meeting Intelligence is not a transcription archive and does not silently write to external systems. It extracts structured decisions and action items, prepares CRM and follow-up material, stores results and approvals durably, and requires explicit human approval before risky writeback commands can progress.

## Features

- Deterministic local extraction for decisions, actions, owners and evidence.
- CRM update and follow-up email drafting.
- Approval-first commands for GitHub, Jira, CRM, email and webhooks.
- Durable SQLAlchemy persistence for results, approvals and structured audit events.
- Reversible Alembic database migrations.
- Strict Pydantic input validation and bounded transcript/request sizes.
- API-key authentication, explicit CORS, rate limiting and constant-time credential checks.
- Request IDs, structured logs, safe error responses, health and database readiness endpoints.
- Non-root containers and least-privilege Docker Compose defaults.
- Python SDK and Next.js product dashboard shell.
- Unit, integration and basic end-to-end approval tests.
- CI, coverage, CodeQL, dependency review, audits, tracked-secret scanning and image scans.

## Architecture

```text
Browser / API client
        |
        v
Meeting Intelligence API
        |
        +--> extraction engine
        |
        +--> PostgreSQL
        |      meetings / commands / approvals / audit events
        |
        +--> durable dispatch queue (P0 TODO)
                  |
                  +--> approved GitHub / Jira / CRM / email / webhook adapters
```

Repository layout:

```text
apps/api        FastAPI API, persistence, migrations and tests
apps/web        Next.js dashboard shell
packages/sdk    Python client SDK
examples        Synthetic request/demo data
docs            Architecture, deployment, security and screenshot guidance
.github         CI, dependency review and CodeQL
```

The API persists analysis and approval state transactionally. The one-shot migration service updates PostgreSQL before the API starts. External writeback implementations remain disabled by default and are not represented as production-complete merely because adapter interfaces exist.

See [Architecture](docs/ARCHITECTURE.md) and [Production blockers](docs/PRODUCTION_TODOS.md).

## Quick start

Requirements:

- Docker 24+ with Compose v2; or
- Python 3.12 and Node.js 22 for native development.

```bash
cp .env.example .env
# Replace local placeholders before exposing the service.
docker compose config --quiet
docker compose up --build --wait
curl http://127.0.0.1:8080/healthz
curl http://127.0.0.1:8080/readyz
```

API documentation: `http://127.0.0.1:8080/docs`  
Dashboard: `http://127.0.0.1:3000`

Native verification:

```bash
make install
make lint
make format-check
make typecheck
make test
make build
make audit
make security
make migration-check
make compose-check
make docker-build
```

`make verify` runs all repository quality and deployment gates. The web workspace still needs a committed lockfile before its installation is fully deterministic; this is an explicit P0 blocker rather than a hidden production claim.

## Example usage

Synthetic input is available at [`examples/meeting-request.json`](examples/meeting-request.json).

```bash
curl -X POST http://127.0.0.1:8080/v1/meetings/analyse \
  -H 'content-type: application/json' \
  -H 'x-api-key: change-me-use-a-secret-manager-in-production' \
  --data @examples/meeting-request.json
```

Retrieve the durable result:

```bash
curl http://127.0.0.1:8080/v1/meetings/example-meeting-001 \
  -H 'x-api-key: change-me-use-a-secret-manager-in-production'
```

Approve selected commands only after review:

```bash
curl -X POST http://127.0.0.1:8080/v1/approvals/example-meeting-001/approve \
  -H 'content-type: application/json' \
  -H 'x-api-key: change-me-use-a-secret-manager-in-production' \
  -d '{"command_ids":["REPLACE-WITH-COMMAND-UUID"],"approved_by":"reviewer@example.com","reason":"Checked against transcript"}'
```

Unknown command identifiers are rejected atomically. Approval does not yet imply dispatch; durable queue-backed execution remains a documented P0 item.

## Environment variables

Safe placeholders and local defaults are in [`.env.example`](.env.example).

| Variable | Purpose |
|---|---|
| `RAEBURN_ENV` | `development`, `test` or `production`. Production enables fail-closed validation. |
| `RAEBURN_API_KEY` | API credential. Must be replaced and secret-managed in production. |
| `RAEBURN_CORS_ORIGINS` | Explicit comma-separated browser-origin allowlist. |
| `RAEBURN_RATE_LIMIT_PER_MINUTE` | Process-level request limit; production ingress should add distributed limits. |
| `DATABASE_URL` | SQLAlchemy connection string. Production requires PostgreSQL. |
| `AUTO_CREATE_SCHEMA` | Local/test convenience. Must be `false` in production; use Alembic. |
| `REDIS_URL` | Reserved for durable queue/cache work. |
| `APPROVALS_REQUIRED` | Keeps risky commands pending by default. Keep `true`. |
| `LLM_PROVIDER` | `deterministic` or a future reviewed OpenAI-compatible integration. |
| `*_WRITEBACK_ENABLED` | Individual integration kill switches; all default to `false`. |

Production startup is rejected when the API key is a placeholder, SQLite is configured, automatic schema creation is enabled or CORS contains `*`.

## Testing and quality

- `make lint` — Ruff and ESLint.
- `make format-check` — Python formatting verification.
- `make typecheck` — strict mypy and TypeScript checks.
- `make test` — unit, integration and E2E-marked tests with 80% API coverage enforcement.
- `make build` — Python source/wheel and Next.js production builds.
- `make audit` — Python and npm vulnerability audits.
- `make security` — high-confidence tracked-secret scanning.
- `make migration-check` — upgrade, rollback and re-upgrade against an isolated database.
- `make docker-build` — API and web container builds.

CI additionally runs dependency review, CodeQL and HIGH/CRITICAL container vulnerability scans.

## Security model

- Risky commands are pending until explicitly approved.
- Approval changes are transactional and durably audited.
- API credentials are compared in constant time.
- Input models reject unknown fields and enforce size limits.
- Logs include request identifiers and timings without exposing raw exception messages.
- External integrations are disabled by default and require least-privilege credentials.
- The API container runs non-root, drops capabilities and uses a read-only filesystem in Compose.
- PostgreSQL and Redis are private to the Compose network.
- Secrets belong in a platform secret manager, never source control or browser bundles.

The current in-process rate limit protects one API process. Multi-replica production deployment requires edge or Redis-backed distributed limits. See [SECURITY.md](SECURITY.md).

## Deployment

Read [Production deployment](docs/DEPLOYMENT.md) before an internet-facing rollout. The release flow separates migrations from image build/startup, requires managed PostgreSQL, explicit CORS, TLS/WAF, backup restoration, monitoring and rollback evidence.

A green application build is not sufficient production evidence. The exact release commit must pass CI, security checks, staging E2E, restore/rollback exercises and privacy/security approval.

## Screenshots

The project contains a dashboard shell, but authenticated approval and audit screens remain unfinished. [`docs/screenshots/README.md`](docs/screenshots/README.md) contains the capture checklist and placeholder policy. No fabricated product screenshots are included.

## RaeburnAI ecosystem

Meeting Intelligence is the conversation-to-action module within the RaeburnAI ecosystem. It can provide approved, structured decisions and tasks to Proposal Generator, CRM, Workflow Auditor and RaeburnAI Chain. Modules should communicate through versioned APIs and separately scoped credentials—not shared databases or copied secrets.

## Roadmap and production status

Implemented in this hardening branch:

- durable result, approval and audit persistence;
- versioned migrations and real readiness checks;
- strict validation and safer operational logging;
- least-privilege containers and expanded quality/security gates.

Remaining blockers include the web lockfile, durable queue-backed dispatch, authenticated organisations/RBAC, SSO, real CRM adapters, transcript lifecycle controls, restore evidence, load testing and independent security review.

See [ROADMAP.md](ROADMAP.md), [CHANGELOG.md](CHANGELOG.md) and [Production blockers](docs/PRODUCTION_TODOS.md).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Contributions must preserve approval-first behaviour, fail-closed production configuration and auditable sensitive actions.

## Licence

Licensed under the [Apache License 2.0](LICENSE).
