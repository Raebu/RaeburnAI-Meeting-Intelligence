# Meeting Intelligence Operations Runbook

This runbook defines the minimum safe operating procedures for Meeting Intelligence. It is intentionally provider-neutral and does not authorize deployment, credential changes, or unrestricted external writebacks.

> **Production gate:** the service is still under the production-readiness work tracked in issue #16. Do not treat this document as evidence that the service is production-ready, and do not enable unrestricted writebacks until all P0 controls are complete.

## 1. Incident response

### Severity

- **SEV-1:** suspected credential compromise, unauthorized external writeback, cross-workspace data exposure, unrecoverable data loss, or service behavior that can materially alter an external system without valid approval.
- **SEV-2:** persistent API outage, queue/backlog failure, failed approved writebacks that require reconciliation, or material loss of availability without confirmed data exposure.
- **SEV-3:** degraded non-critical functionality, isolated provider errors, or recoverable operational defects.

### First 15 minutes

1. Stop or disable the affected writeback path. Prefer fail-closed behavior; do not bypass approval controls to restore throughput.
2. Preserve evidence: UTC timestamps, request/meeting IDs, deployment SHA, affected integration/workspace identifiers, provider response IDs and relevant redacted logs.
3. Do **not** paste transcripts, API keys, tokens, authorization headers or raw customer payloads into tickets or chat.
4. Identify blast radius: affected workspaces, integrations, meetings, time range and external systems.
5. For suspected credential compromise, follow **Credential rotation** below before re-enabling the integration.
6. For duplicate/partial writes, stop automatic retry until idempotency/reconciliation state is known.

### Recovery criteria

Do not close an incident until the triggering condition is contained, affected records are reconciled, corrective verification has passed, and a short post-incident note records cause, impact, remediation and follow-up controls.

## 2. Rollback

A rollback must use a previously verified source revision or image. Never roll back by deleting migrations or manually editing production data to resemble an older schema.

1. Record the current deployment SHA and the proposed rollback SHA.
2. Confirm whether any database migration occurred between the two revisions.
3. If the change is application-only, deploy the last verified revision using the normal deployment mechanism.
4. If schema changes are involved, use the reviewed Alembic downgrade path only when the migration explicitly supports it and data-loss implications are understood.
5. Re-run health checks and a read-only smoke test.
6. Verify approval-required behavior before allowing any external writeback.
7. Record the rollback outcome and keep the failed revision blocked from redeployment until corrected.

### Rollback verification

At minimum verify:

```text
GET /healthz -> 200
unauthenticated protected request -> rejected
approved-writeback policy -> still fail-closed
representative authenticated read -> succeeds
```

Do not use live customer records for a smoke test when a sandbox/test record is available.

## 3. Backup and restore

The current repository still has a P0 item to replace in-memory storage with PostgreSQL. **In-memory meeting/result state is not durable and cannot be backed up reliably.** Until PostgreSQL persistence is merged and verified, a process restart can lose state and the service must not be represented as restart-safe.

Once PostgreSQL persistence is enabled, the production environment must provide encrypted automated backups with a defined retention window and periodic restore tests. The exact provider command belongs in the environment-specific deployment documentation; this repository must not embed production credentials or provider secrets.

### Restore drill requirements

A restore drill is complete only when it demonstrates all of the following in an isolated environment:

1. Restore a known backup to a clean database instance.
2. Run migrations to the application-supported schema version.
3. Start the API against the restored database.
4. Verify representative meetings/results, approvals, audit events and integration-command state.
5. Confirm pending/approved work is not silently duplicated after worker restart.
6. Run integrity checks and record backup timestamp, restore duration, resulting schema revision and verification result.

Never overwrite the only known-good database while testing a restore.

## 4. Credential rotation

Credentials must be scoped per workspace/integration wherever the provider supports it. Never share a single high-privilege credential across customers.

1. Disable the affected integration or writeback path.
2. Create a replacement credential with the minimum required scopes.
3. Store it only in the approved secret store/environment mechanism; never commit it to Git, fixtures, screenshots or issue comments.
4. Update the integration to use the replacement credential.
5. Verify with a sandbox/read-only operation first, then one explicitly approved write operation if required.
6. Revoke the old credential after the replacement is proven.
7. Confirm the old credential no longer works.
8. Record rotation date, integration/workspace, scope changes and verifier identity without recording the secret value.

For suspected compromise, revoke first when the risk of continued unauthorized access is greater than the operational impact of temporary downtime.

## 5. Failed or partial external writebacks

Until durable queueing, idempotency and reconciliation are complete, operators must assume provider timeouts can have ambiguous outcomes.

1. Do not blindly retry a timed-out write.
2. Query the target system using the operation's stable idempotency/correlation identifier when available.
3. Determine whether the external mutation already occurred.
4. If it occurred, record/reconcile the provider object ID and mark the operation complete rather than retrying.
5. If it did not occur, retry only through the approved path.
6. Escalate any state that cannot be conclusively reconciled.

## 6. Data handling and log redaction

Operational logs and tickets must not contain:

- transcript text unless strictly necessary and explicitly protected;
- access tokens, API keys, cookies or authorization headers;
- full webhook signatures/secrets;
- unnecessary personal data from meeting participants.

Prefer stable IDs, timestamps, status codes, provider request IDs and redacted error summaries. Any future structured-logging implementation should use an allow-list of safe fields rather than attempting to redact arbitrary payloads after logging.

## 7. Pre-release operational checklist

Before a production release is considered safe, verify the repository completion gate and specifically confirm:

- all P0 items in issue #16 are complete;
- migrations have a reviewed upgrade/rollback path;
- API and web build/test/security gates pass;
- dependency, secret, CodeQL and container scans have no unresolved critical/high production blocker;
- durable queue/retry/idempotency behavior has been exercised;
- backup restoration has been demonstrated;
- external writebacks remain approval-gated and sandbox E2E has passed;
- incident owner/on-call path and environment-specific deployment/rollback instructions are recorded outside source control where they contain sensitive infrastructure details.

## 8. Evidence template

Use this compact template for an operational drill or incident record:

```text
UTC start/end:
Environment:
Source SHA:
Schema revision:
Affected component/integration:
Impact/blast radius:
Actions taken:
Verification performed:
Result:
Follow-up issue(s):
```
