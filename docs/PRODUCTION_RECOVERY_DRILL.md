# Production recovery validation drill

This document defines the evidence required before Meeting Intelligence can be treated as recoverable in production. It is deliberately stricter than a prose runbook: every drill must produce timestamped, reviewable evidence and must be repeated after material persistence, queue, deployment, or credential changes.

> **Current limitation:** the service still has process-local meeting state and is not yet eligible to pass the persistence/recovery portions of this drill. Do not record a recovery drill as passing until durable PostgreSQL storage and durable queue-backed execution are implemented.

## 1. Preconditions

Run against an isolated staging environment containing synthetic meeting data only.

Required before starting:

- the exact application commit SHA and container image digest are recorded;
- the database schema revision is recorded;
- a known-good previous application image is available for rollback;
- backup retention and encryption are enabled on the staging database;
- queue retry/DLQ configuration is recorded once a durable queue exists;
- no production integration credential is reused in staging;
- an operator and independent verifier are named in the evidence record.

Abort the drill if any prerequisite is missing. A partial exercise is useful diagnostic work but is not a passing recovery test.

## 2. Evidence record

Create one evidence record per drill containing:

- UTC start/end time;
- operator and verifier;
- commit SHA, image digest, schema revision and deployment identifier;
- backup identifier and creation time;
- synthetic meeting IDs used for verification;
- queue job/command IDs used for verification;
- commands or control-plane actions executed;
- observed recovery point objective (RPO);
- observed recovery time objective (RTO);
- screenshots/log excerpts with transcript content redacted;
- pass/fail result for every section below;
- remediation issue links for every failure.

Never copy transcript text, API keys, OAuth tokens, webhook secrets, database passwords or connection strings into the evidence record.

## 3. Database backup and restore

### Backup

1. Create synthetic records representing a meeting, extracted decisions/actions, pending approval, approved command and audit events.
2. Record their identifiers and a non-sensitive checksum/count of expected records.
3. Trigger the platform-supported PostgreSQL backup/snapshot mechanism.
4. Record the immutable backup identifier and timestamp.
5. Make one additional synthetic change after the backup so restoration can demonstrate the exact recovery point.

### Restore

1. Restore the backup into a new isolated database or isolated staging branch. Never overwrite the only usable staging database as the first recovery test.
2. Apply only the schema/migration procedure documented for the restored application version.
3. Point an isolated API instance at the restored database.
4. Verify the pre-backup synthetic meeting, approval, integration command and audit records are present.
5. Verify the deliberately post-backup change is absent unless point-in-time recovery was intentionally configured beyond the backup timestamp.
6. Verify API reads work after restart and that pending/approved states are unchanged.
7. Record measured RPO and RTO.

**Pass condition:** expected durable records are present and internally consistent, the recovery point is understood, and restarting the API does not lose restored work.

## 4. Queue crash/retry/DLQ recovery

This section becomes mandatory when durable dispatch is implemented.

1. Enqueue synthetic approved writebacks with stable idempotency keys.
2. Stop a worker while at least one job is in-flight.
3. Restart the worker and verify the job is recovered without duplicate external effects.
4. Force a retryable provider failure and verify bounded exponential retry behavior.
5. Force a permanent failure and verify the job enters the DLQ after the configured attempt ceiling.
6. Replay one DLQ item through the supported operator path and verify the audit trail records the replay.
7. Restart queue/worker components and verify pending jobs survive.

**Pass condition:** no approved command is silently lost, duplicate side effects are prevented, permanent failures are visible, and recovery actions are auditable.

## 5. Application rollback

1. Deploy a deliberately identifiable staging release from the candidate commit.
2. Exercise health, readiness, authenticated meeting retrieval and approval paths using synthetic data.
3. Roll back to the recorded known-good image without changing DNS or external production infrastructure.
4. Verify database compatibility with the rolled-back application.
5. Verify no pending approved work disappears and no command is dispatched twice.
6. Re-deploy the candidate release and repeat the smoke checks.

If a migration is not backward compatible, the release must document an explicit expand/migrate/contract strategy or a tested database rollback procedure before production use.

**Pass condition:** the previous release can be restored within the target RTO without corrupting durable state or creating duplicate external actions.

## 6. Credential rotation drill

Use staging-only credentials.

For each enabled integration and API credential:

1. create a replacement secret/token with the minimum required scope;
2. update the staging secret store using the normal deployment path;
3. restart/roll the relevant service if required;
4. verify the replacement credential works;
5. revoke the old credential;
6. prove the old credential no longer works;
7. verify logs contain no secret values;
8. record the credential type, rotation time and verifier, but never the secret itself.

Include the Meeting Intelligence API key, database credential, external LLM key, GitHub/Jira credentials and webhook signing secret when those integrations are enabled.

**Pass condition:** replacement credentials work, old credentials are revoked, least privilege is preserved, and no secret appears in logs/evidence.

## 7. Incident simulation

Run at least these scenarios with synthetic data:

- database temporarily unavailable;
- queue/worker unavailable once durable queueing exists;
- external provider returns sustained 5xx responses;
- invalid/revoked integration credential;
- rate-limit exhaustion;
- attempted replay/duplicate integration command;
- application restart during pending approval and during dispatch.

For each scenario verify:

- failure is visible in structured operational telemetry;
- user-facing/API behavior fails safely;
- no transcript content or credentials leak into logs;
- no external write occurs without required approval;
- recovery does not create duplicate external effects;
- operator remediation is documented and auditable.

## 8. Release gate

A release is **not recovery-ready** if any of the following is true:

- durable state or queued work is lost after restart;
- database restore has not been demonstrated;
- rollback cannot be completed safely;
- a permanently failed integration command can disappear silently;
- idempotency cannot be demonstrated across worker/application restarts;
- credentials cannot be rotated and revoked without downtime beyond the accepted RTO;
- critical recovery steps depend on undocumented personal knowledge;
- evidence contains sensitive transcript or credential material.

Failures must create a tracked repository issue with severity, reproduction steps, owner, remediation plan and re-test evidence.

## 9. Suggested initial service targets

Until commercial SLOs are agreed, use these as engineering targets rather than contractual promises:

- staging recovery drill: at least once before each production-bound architecture change affecting persistence/queueing;
- backup restoration: demonstrated before first production launch and periodically thereafter;
- credential rotation: demonstrated before first production launch and after material credential-management changes;
- rollback: demonstrated for every production-bound release mechanism change;
- recovery evidence retention: long enough to support security review and incident learning, without retaining transcript content.

These targets do not replace customer-specific RPO/RTO requirements or infrastructure-provider backup guarantees.
