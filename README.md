# RaeburnAI Meeting Intelligence

**Not another meeting transcription tool.** RaeburnAI Meeting Intelligence turns meeting content into operational outcomes: decisions, actions, owners, CRM updates, Jira/GitHub tasks, and automated follow-up.

## What it does

- Detects decisions from transcripts, notes, or meeting recordings processed by your own transcription provider.
- Extracts action items with owners, due dates, priority, blockers, and confidence scores.
- Assigns owners using attendee context, explicit mentions, historical ownership, and fallback rules.
- Creates implementation-ready follow-up summaries.
- Pushes tasks into Jira and GitHub Issues.
- Prepares CRM updates for HubSpot/Salesforce-compatible pipelines.
- Supports human approval workflows before external systems are changed.
- Provides an auditable event trail for every generated decision, action, integration event, and approval.

## Open-source licence

This project is released under the **Apache License 2.0**. It is permissive for commercial use while preserving patent protections and attribution.

## Architecture

```text
apps/api          FastAPI application and domain services
apps/web          Next.js dashboard shell
packages/sdk      Python client SDK
infra             Docker, Compose and deployment manifests
docs              Product, architecture, security and contribution docs
.github           CI, issue templates and security workflow
```

## Core flow

1. Ingest meeting transcript, attendee list, CRM context, and optional raw notes.
2. Run meeting intelligence extraction through an LLM adapter.
3. Normalise decisions, action items, owners and suggested follow-ups.
4. Store audit events and require approval for external updates.
5. Dispatch approved updates to GitHub, Jira, CRM, email or webhook destinations.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

API: `http://localhost:8080/docs`  
Dashboard: `http://localhost:3000`

## Local API development

```bash
cd apps/api
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
uvicorn meeting_intelligence.main:app --reload --port 8080
```

## Local web development

```bash
cd apps/web
npm install
npm run dev
```

## Example API request

```bash
curl -X POST http://localhost:8080/v1/meetings/analyse \
  -H 'content-type: application/json' \
  -d @examples/meeting-request.json
```

## Production readiness included

- API contract with Pydantic validation.
- Deterministic fallback extractor for offline/local development.
- LLM provider abstraction for OpenAI-compatible, local and future providers.
- Human approval model for writeback integrations.
- GitHub/Jira/CRM/email/webhook integration interfaces.
- Docker Compose with API, web, Postgres and Redis.
- CI for linting, tests and security scanning.
- Security policy, contribution guide, code of conduct and architecture docs.
- Health checks and structured audit events.

## Environment variables

See `.env.example` for the complete list.

## Status

This repository is structured as a shippable open-source foundation. Some external integrations require API credentials and should be enabled only after approval workflows are configured.
