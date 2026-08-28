# Security Policy

## Supported versions

The `main` branch is the active development branch until the first stable release. Security fixes are applied to supported release lines as appropriate.

## Reporting a vulnerability

Please do **not** open a public issue for a suspected security vulnerability. Report it privately through GitHub Security Advisories:

https://github.com/Raebu/RaeburnAI-Meeting-Intelligence/security/advisories/new

If private reporting is unavailable, contact the repository maintainers through the repository owner profile rather than publishing exploit details.

Please include the affected component and version, reproduction steps or proof of concept, the expected impact, and any suggested remediation.

We aim to acknowledge a vulnerability report within **2 business days**, provide an initial assessment within **7 days**, and coordinate remediation and disclosure with the reporter. Unless an actively exploited vulnerability requires a faster response, coordinated public disclosure should normally occur after a fix is available and no later than **90 days** after confirmation.

Please keep vulnerability details confidential during the coordinated disclosure period. We will disclose security fixes transparently once affected users have a reasonable opportunity to update.

## Security principles

- Meeting data may be sensitive and must be treated as confidential.
- External writebacks should require human approval by default.
- Store secrets only in secret managers or environment variables.
- Never commit API keys, transcripts, CRM data or customer information.
- Prefer deterministic/local mode for highly sensitive deployments.
- Log audit metadata, not raw sensitive transcript content.
- Apply least privilege to tokens, integrations and automated workflows.
