# Deployment

## Docker Compose

```bash
cp .env.example .env
docker compose up --build -d
```

## Required production changes

- Replace `RAEBURN_API_KEY` and `RAEBURN_SECRETS_KEY`.
- Use managed Postgres and Redis.
- Restrict CORS origins in `apps/api/meeting_intelligence/main.py`.
- Put the API behind TLS.
- Enable only the integrations you need.
- Keep `APPROVALS_REQUIRED=true` unless you have strong compensating controls.

## Suggested production architecture

- API: container app, Kubernetes, Fly.io, Render, Railway, ECS, Cloud Run or Azure Container Apps.
- Web: Vercel, container app or static Next.js hosting.
- Database: Supabase, Neon, RDS, Cloud SQL or Azure Database for PostgreSQL.
- Queue/cache: Upstash Redis, Elasticache, Memorystore or Azure Cache for Redis.
- Secrets: platform secret manager.

## Readiness checklist

- Health endpoint returns `ok`.
- CI passes.
- Backups configured.
- Approval workflow tested.
- Integration tokens scoped to minimum permissions.
- Audit retention policy agreed.
- Data processing terms reviewed for customer deployments.
