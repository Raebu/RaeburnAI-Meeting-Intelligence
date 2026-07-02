# Architecture

RaeburnAI Meeting Intelligence is designed as an approval-first operational intelligence layer.

## Components

## API

The FastAPI service owns the public API, request validation, authentication, extraction orchestration, approval state and dispatch routing.

## Intelligence Engine

The engine converts raw meeting content into a structured object:

- `Decision[]`
- `ActionItem[]`
- `CrmUpdate`
- `FollowUp`
- `IntegrationCommand[]`
- `audit_events[]`

The first implementation includes deterministic extraction so the system is usable without sending meeting data to an external provider. LLM providers can be introduced behind the same contract.

## Approval workflow

All external writebacks are represented as `IntegrationCommand` objects. By default, commands are `pending` and need explicit approval before dispatch.

## Integrations

Adapters live behind a small interface:

```python
class IntegrationAdapter:
    async def dispatch(self, command: IntegrationCommand) -> DispatchResult: ...
```

Current adapters:

- GitHub issue creation
- Jira task creation
- Webhook dispatch

Planned adapters:

- HubSpot note and deal update
- Salesforce task/update
- Gmail/SMTP follow-up sending
- Slack/Teams summaries

## Data model roadmap

For production persistence, use Postgres tables for:

- meetings
- attendees
- decisions
- action_items
- integration_commands
- approvals
- dispatch_results
- audit_events

## Security model

- API key at the edge for machine-to-machine calls.
- Secrets via environment variables or a secret manager.
- Human approval before external writebacks.
- Full audit trail for generated and dispatched actions.
- No third-party LLM required for local/private mode.
