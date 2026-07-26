# Production deployment

This guide describes the minimum deployment path for the implemented persistence foundation. It does not replace an organisation-specific security, privacy or disaster-recovery review.

## Local Docker Compose

```bash
cp .env.example .env
# Replace the local API and database placeholders before exposing any port.
docker compose config --quiet
docker compose up --build --wait
curl http://127.0.0.1:8080/healthz
curl http://127.0.0.1:8080/readyz
```

The `migrate` service runs `alembic upgrade head` before the API starts. PostgreSQL and Redis are not published to the host. The API and web ports bind to loopback by default.

## Required production configuration

- Set `RAEBURN_ENV=production`.
- Generate a unique `RAEBURN_API_KEY` in a secret manager.
- Set `AUTO_CREATE_SCHEMA=false`; execute Alembic as a separately approved release step.
- Use a managed PostgreSQL service with TLS and a least-privilege application role.
- Use managed Redis only when the queue worker is implemented; do not expose Redis publicly.
- Set an explicit HTTPS `RAEBURN_CORS_ORIGINS` allowlist.
- Terminate TLS at a trusted ingress and configure trusted proxy handling there.
- Leave every writeback feature disabled until its credentials, sandbox tests and failure handling are approved.
- Keep `APPROVALS_REQUIRED=true`.

The application refuses to start in production with a placeholder API key, SQLite, automatic schema creation or wildcard CORS.

## Release sequence

1. Build immutable API and web images from a reviewed commit.
2. Produce and retain software bill of materials and vulnerability results.
3. Back up the current database and verify the backup is readable.
4. Run `alembic upgrade head` as a one-shot migration job.
5. Deploy API and web images without running schema mutation during compilation or startup.
6. Verify `/healthz` and `/readyz` through the production ingress.
7. Execute the authenticated staging/production smoke test.
8. Monitor errors, latency and database saturation during the release window.
9. Roll back the application image if necessary. Run schema downgrade only when the migration has been explicitly assessed as safely reversible.

## Suggested architecture

```text
Browser
  -> TLS/WAF/rate-limited ingress
  -> authenticated web application
  -> Meeting Intelligence API
       -> PostgreSQL (meetings, approvals, audit)
       -> queue worker / Redis (TODO)
       -> scoped external adapters (disabled by default)
```

Use separate development, staging and production databases, credentials and integration accounts. Never share production databases directly with another RaeburnAI module; integrate through versioned APIs and scoped credentials.

## Backup and recovery

Before launch, document and test:

- encrypted automated PostgreSQL backups;
- retention and deletion periods;
- point-in-time recovery where available;
- restoration into an isolated environment;
- application rollback;
- credential rotation;
- audit-log preservation;
- recovery time and recovery point objectives.

A configured backup is not sufficient evidence. Record a successful restore drill.

## Monitoring

At minimum alert on:

- readiness failures;
- elevated 5xx or 429 rates;
- database connection or transaction failures;
- approval queue age once queueing exists;
- failed or repeatedly retried writebacks;
- unusual authentication failures;
- backup failures;
- high storage growth or retention-policy violations.

## Release checklist

- [ ] CI, CodeQL, dependency review and image scans pass for the exact commit.
- [ ] Web lockfile is committed and frozen installs pass.
- [ ] Production secrets are stored outside source control.
- [ ] Database migration and rollback implications are reviewed.
- [ ] Backup restoration is demonstrated.
- [ ] Approval workflow is tested with authorised and unauthorised users.
- [ ] Integration tokens have minimum scopes and separate environments.
- [ ] Privacy, retention, DPA and subprocessors are approved.
- [ ] Accessibility and security testing are complete.
- [ ] A named owner and rollback decision-maker are available during release.
