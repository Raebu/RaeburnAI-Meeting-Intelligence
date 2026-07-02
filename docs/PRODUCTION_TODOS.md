# Production TODOs

These items are intentionally documented rather than hidden. The repository is a strong production-ready foundation, but the following are required before handling real customer data at enterprise scale.

## Required before enterprise customer deployment

- Replace in-memory meeting result storage with Postgres persistence.
- Add database migrations and retention controls.
- Add queue-backed dispatch worker for approved integration commands.
- Add organisation/user model with RBAC.
- Add SSO/OIDC or SAML for dashboard access.
- Add full CRM adapters for HubSpot and Salesforce.
- Add encrypted transcript storage or avoid storing transcripts entirely.
- Add automated extraction quality evaluation datasets.
- Capture real UI screenshots after deployment.

## Requires external credentials

- GitHub issue writeback.
- Jira task creation.
- CRM update dispatch.
- Email follow-up sending.
- Webhook dispatch.

## Connector-blocked during repository hardening

- `apps/web/tsconfig.json` creation was blocked by the GitHub connector safety layer and should be retried locally.
- `NOTICE` creation was blocked by the GitHub connector safety layer and should be retried locally if formal attribution notices are required.
