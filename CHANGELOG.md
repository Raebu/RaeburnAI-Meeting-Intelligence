# Changelog

All notable changes to this project are documented here. The project follows Keep a Changelog and intends to use Semantic Versioning.

## [Unreleased]

### Added

- Durable SQLAlchemy persistence for meeting results, command approvals and structured audit events.
- Alembic migration framework with an initial reversible schema migration.
- Real database readiness checks and transaction-safe approval updates.
- Strict, bounded Pydantic request validation and unknown-field rejection.
- Request identifiers, latency-aware structured logs and safe generic error responses.
- Unit, integration and end-to-end tests covering authentication, persistence, approvals and validation.
- Coverage enforcement, package builds, dependency audits, migration rollback checks, tracked-secret scanning and container vulnerability gates.
- One-shot migration service and least-privilege Docker Compose defaults.

### Changed

- The API now fails closed on unsafe production API keys, SQLite, automatic schema creation and wildcard CORS.
- API-key comparison now uses constant-time comparison.
- The API container runs as a non-root user with a pinned Python base image and no unnecessary OS packages.
- PostgreSQL and Redis are private to the Compose network and use pinned patch-level images.
- Risky integration commands remain approval-gated by default.
- Documentation now distinguishes the implemented persistence foundation from unfinished enterprise identity, queueing and integration work.

### Security

- Unknown approval command identifiers are rejected atomically rather than partially updating a meeting.
- Operational logs no longer include raw exception text by default.
- Containers drop Linux capabilities, prevent privilege escalation and use a read-only API filesystem.
- High-confidence committed-secret patterns are checked in CI.

### Known limitations

- The web workspace still needs a committed package-manager lockfile before installs are fully deterministic.
- Approved writebacks are not yet executed by a durable queue worker.
- Organisation tenancy, RBAC and SSO are not implemented.
- HubSpot, Salesforce and production notification adapters require real sandbox and staging validation.
- Backup restoration, load testing and independent penetration testing remain external release gates.

## [0.1.0] - 2026-07-02

### Added

- FastAPI backend for meeting analysis and approval workflows.
- Deterministic extraction engine for decisions, actions, owners and follow-up drafts.
- Integration command model for GitHub, Jira, CRM, email and webhook writebacks.
- GitHub, Jira and webhook adapter interfaces.
- Next.js dashboard shell.
- Python SDK.
- Docker and Docker Compose local stack.
- CI pipeline with linting, type checking, tests, Docker build, dependency review and CodeQL.
- Security, contribution, architecture, deployment and product documentation.

### Security

- API key protection for non-development environments.
- CORS origin configuration.
- Request rate limiting.
- Human approval required by default for risky write actions.
- Structured audit events for sensitive operations.
