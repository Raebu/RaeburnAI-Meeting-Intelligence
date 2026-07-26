# Production blockers and external release gates

This file deliberately records what is **not** complete. The repository has a materially hardened application and persistence foundation, but it must not be presented as fully enterprise-certified until the items below are completed and evidenced.

## Implemented in the current hardening branch

- PostgreSQL-compatible durable persistence for meetings, commands, approvals and audit events.
- Reversible Alembic migrations and database-backed readiness checks.
- Transactional approval updates that reject unknown command identifiers atomically.
- Strict request validation, bounded transcripts and approval payloads.
- Non-root containers, private data services and least-privilege Compose settings.
- Unit, integration and basic end-to-end approval tests.
- Coverage, dependency audit, CodeQL, tracked-secret and image-scanning gates.
- Branch-restricted verification is installed on `main`; command results must be green before this PR is merged.

## P0 — required before handling real enterprise customer data

- Generate and commit a reviewed lockfile for `apps/web`; use `npm ci` or an equivalent frozen install in CI and containers.
- Add organisation/user tenancy, RBAC and authenticated approval screens.
- Add SSO/OIDC or SAML and an MFA policy for privileged users.
- Add a durable queue worker for approved commands with retries, idempotency, dead-letter handling and reconciliation.
- Implement real HubSpot or Salesforce integration and prove it against a sandbox.
- Define transcript storage policy: encrypted storage with per-tenant retention, or do not persist raw transcripts.
- Add deletion, export, legal hold and suppression workflows.
- Automate PostgreSQL backups and demonstrate restoration and deployment rollback.
- Add monitoring, alerts, operational ownership and incident-response exercises.
- Complete privacy, DPA, subprocessor, accessibility and independent penetration-test reviews.

## External credentials and validation still required

- GitHub issue writeback with a least-privilege GitHub App or scoped token.
- Jira task creation with project-scoped credentials.
- CRM update dispatch.
- Email follow-up sending with delivery and bounce reconciliation.
- Signed and allowlisted webhook dispatch.

No adapter should be marked production-ready solely because environment-variable placeholders exist. Each needs contract tests, sandbox evidence, failure handling and a named operational owner.

## UI evidence

Real screenshots must be captured from a deployed staging environment after authentication and approval screens exist. The repository intentionally does not contain fabricated screenshots; see `docs/screenshots/README.md`.
