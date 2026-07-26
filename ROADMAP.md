# Roadmap

The roadmap separates implemented capabilities from work that still requires engineering or external production evidence.

## Implemented foundation

- Deterministic meeting intelligence extraction.
- Decision and action-item detection with owner inference.
- CRM update and follow-up drafting.
- Approval-first integration command model.
- Durable SQLAlchemy meeting, approval and audit persistence.
- Reversible Alembic migrations and real database readiness checks.
- Strict input bounds, API authentication, structured logs and safe errors.
- Docker Compose local stack with a one-shot migration service.
- CI for linting, formatting, strict typing, tests, coverage, builds, dependency audits, CodeQL and image scans.

## P0 — required before customer production deployment

- Commit and enforce a web package-manager lockfile, then replace `npm install` with a frozen install.
- Add a durable Redis-backed dispatch worker with retries, idempotency, dead-letter handling and reconciliation.
- Implement authenticated organisations, users and role-based approval permissions.
- Add an authenticated dashboard approval queue and immutable audit view.
- Implement and test at least one real CRM adapter in a sandbox environment.
- Add transcript retention, deletion, export and encryption controls.
- Add automated backups and demonstrate PostgreSQL restore and deployment rollback.
- Complete privacy, DPA, subprocessor, accessibility and independent security review.

## P1 — enterprise capability

- SSO through OIDC/SAML and enforced MFA policy.
- HubSpot and Salesforce production adapters.
- Slack and Microsoft Teams notification adapters.
- OpenAI-compatible extraction with redaction, data-residency and evaluation controls.
- Extraction quality evaluation datasets and regression thresholds.
- Per-tenant quotas, rate limits, retention policies and integration credentials.
- Load, queue-failure and provider-outage testing.

## Later

- On-premises and private-cloud deployment profiles.
- SOC 2 aligned evidence collection and operational controls.
- Multi-region disaster recovery.
- Cross-module orchestration through RaeburnAI Chain.
