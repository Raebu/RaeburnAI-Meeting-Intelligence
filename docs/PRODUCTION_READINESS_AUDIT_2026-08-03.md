# Production readiness audit — RaeburnAI Meeting Intelligence

Date: 2026-08-03  
Branch: `audit/raeburnai-meeting-intelligence-production-readiness-2026-08-03`

## Product and scope

This repository contains a FastAPI meeting-analysis API, a Next.js dashboard shell, and a small Python SDK. The deterministic extractor turns meeting notes into decisions, actions, owners, follow-up drafts and approval-gated integration commands. The README accurately identifies the product as a foundation: results are held in memory, persistence, queues, SSO/RBAC and real CRM adapters are not implemented.

## Baseline evidence

Before remediation, the API installed only under Python 3.11/3.12 because of its declared runtime range. API tests passed 3/3, but Ruff failed 25 findings and mypy failed two errors. The web install generated no lockfile; lint failed because the flat ESLint configuration imported the legacy Next config incorrectly; the web used vulnerable Next.js 15.3.4; and the Docker/CI paths used `npm install`. The compose file required an uncommitted `.env` file, making clean validation fail.

## Changes on this branch

- Added hash-pinned API runtime and development lockfiles and switched API installation/CI/container builds to locked installs.
- Fixed API lint and strict type-check errors in integration and owner inference code.
- Added bounded lengths for meeting IDs, titles, transcripts, attendees and context identifiers, with a regression test for oversized transcripts.
- Upgraded the web to patched Next.js tooling, pinned PostCSS/sharp transitives, committed `package-lock.json`, and corrected the ESLint flat configuration.
- Switched web CI and Docker builds to `npm ci`, and made Compose validation independent of a developer-only `.env` file.
- Enabled the hardening workflow for normal same-repository pull requests instead of a stale historical branch.

## Verification evidence

| Check | Result |
|---|---|
| API install from development lock | Passed in Python 3.11 audit environment |
| API Ruff | Passed |
| API mypy | Passed, 6 modules |
| API tests | Passed, 4 tests |
| Web npm ci | Passed |
| Web lint | Passed |
| Web typecheck | Passed |
| Web tests | Passed, 1 smoke test |
| Web production build | Passed, Next 15.5.22 |
| Web npm audit | Passed, 0 vulnerabilities |
| Compose config | Passed without `.env` |
| Hosted CI / CodeQL / container scan | Pending; credentials/runners and image scan remain external |
| Preview / staging / rollback | Blocked; no deployment access was available |

## Findings and residual risk

The repository is materially more reproducible and testable, but it is not production-ready. Results and audit events remain process-local; rate limiting is process-local; the API uses a shared API key rather than user/workspace authorization; dashboard authentication and RBAC are absent; integration adapters are interfaces rather than verified production connectors; webhook destinations are not yet restricted by an allowlist; and no staging deployment, migration, backup/restore or rollback drill has been evidenced. These are explicit product and deployment blockers, not claims of completed enterprise capability.

Initial score: 41/100  
Current score: 65/100  
Status: Verification Pending / Blocked
