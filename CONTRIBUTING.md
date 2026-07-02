# Contributing

Thank you for helping improve RaeburnAI Meeting Intelligence.

## Development standards

- Keep extraction outputs auditable and explainable.
- Add tests for every extractor and integration adapter change.
- Never introduce silent external writebacks.
- Keep integrations behind adapter interfaces.
- Avoid vendor lock-in where practical.

## Local workflow

```bash
cp .env.example .env
docker compose up --build
```

## Pull request checklist

- Tests added or updated.
- Documentation updated where behaviour changes.
- No secrets or customer data committed.
- Approval workflow preserved for external writes.
- Errors are clear and actionable.
