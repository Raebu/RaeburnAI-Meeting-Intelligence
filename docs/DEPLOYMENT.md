# Deployment

## Docker Compose

```bash
cp .env.example .env
docker compose up --build -d
```

## Required production changes

- Replace `RAEBURN_API_KEY` and `RAEBURN_SECRETS_KEY`.
- Use managed Postgres and Redis after the repository's durable persistence/queue P0 work is complete.
- Restrict CORS origins in `apps/api/meeting_intelligence/main.py`.
- Put the API behind TLS.
- Enable only the integrations you need and scope credentials to the minimum permissions required.
- Keep `APPROVALS_REQUIRED=true`. Production external writebacks must remain explicitly approval-gated; client input or deployment configuration must not weaken this policy.
- Complete every P0 item in issue #16 before treating the service as production-ready.

## Suggested production architecture

- API: container app, Kubernetes, Fly.io, Render, Railway, ECS, Cloud Run or Azure Container Apps.
- Web: Vercel, container app or static Next.js hosting.
- Database: managed PostgreSQL.
- Queue/cache: managed Redis-compatible service or another reviewed durable queue backend.
- Secrets: platform secret manager.

These are architecture examples only. This repository does not authorize or perform production-infrastructure, DNS, billing or credential changes.

## Readiness checklist

- `GET /healthz` returns HTTP 200.
- Clean CI and hardening checks pass, with any infrastructure-only exception explicitly documented rather than counted as green.
- Durable persistence and queueing are implemented and survive component restarts without losing approved or pending work.
- Backup restoration and rollback are demonstrated.
- Approval workflow and sandbox end-to-end writeback are tested.
- Integration tokens are isolated and scoped to minimum permissions.
- Audit and data-retention policy is implemented and verified.
- Data processing terms and privacy documentation are reviewed for customer deployments.
- Incident, rollback, backup/restore and credential-rotation procedures in [OPERATIONS_RUNBOOK.md](./OPERATIONS_RUNBOOK.md) are understood by the operator.

## Operations

See [OPERATIONS_RUNBOOK.md](./OPERATIONS_RUNBOOK.md) for incident containment, rollback, backup/restore requirements, credential rotation, partial-write reconciliation and operational evidence capture.
