# Security policy

## Supported versions

The `main` branch is the active development branch until the first stable release.

## Reporting a vulnerability

Please do not open public issues for security vulnerabilities. Email the maintainers or use GitHub private vulnerability reporting when enabled.

Include:

- Affected component
- Steps to reproduce
- Impact
- Suggested fix, if known

## Security principles

- Meeting data may be sensitive and must be treated as confidential.
- External writebacks should require human approval by default.
- Store secrets only in secret managers or environment variables.
- Never commit API keys, transcripts, CRM data or customer information.
- Prefer deterministic/local mode for highly sensitive deployments.
- Log audit metadata, not raw sensitive transcript content.
