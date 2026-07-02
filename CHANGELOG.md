# Changelog

All notable changes to this project will be documented in this file.

## 0.1.0 - 2026-07-02

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
