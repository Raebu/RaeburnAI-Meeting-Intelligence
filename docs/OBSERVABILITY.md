# Production observability

The API uses structured logs plus the dependency-free `meeting_intelligence.observability` primitives for bounded metrics and trace spans. Telemetry must never contain transcript text, meeting titles, user-entered descriptions, integration payloads, credentials, email addresses, workspace IDs, meeting IDs or actor subjects. When correlation is necessary, use `safe_ref()` and the server-generated request ID.

## Required instrumentation

Record request count/latency by method, route template and status; extraction latency/outcome; approval count/outcome; dispatch queue claims/success/retry/dead-letter/cancel and provider latency by system/outcome; persistence readiness failures; and unhandled exceptions. Do not use raw path values as metric labels because meeting/job IDs create both privacy exposure and unbounded cardinality.

`prometheus_metrics()` renders the in-process bounded metric registry in Prometheus text format for an authenticated/internal scrape adapter. Production deployments should expose it only on a private operations network or through an authenticated collector, never as an unauthenticated Internet endpoint. `trace_span()` emits correlation-safe structured start/completion/failure events and duration metrics without exporting transcript payloads.

## Minimum alert policy

Configure the deployment monitoring platform to page on: readiness failing for 5 consecutive minutes; HTTP 5xx >= 5% for 5 minutes with at least 20 requests; dispatch dead-letter increase >= 5 jobs in 10 minutes; dispatch queue oldest pending age > 10 minutes; provider failure rate >= 20% over 10 minutes with at least 10 attempts; or backup/restore verification overdue. Warn on p95 request latency > 2 seconds for 15 minutes and extraction-quality benchmark regression below repository gates.

Alerts must link to the incident and recovery runbooks. Never include transcript excerpts or integration payloads in alert notifications. Retain operational telemetry only according to the deployment privacy/retention policy and restrict access to operations personnel.

## Verification

Before enterprise release, exercise each alert in staging with synthetic non-customer data, verify routing and acknowledgement, confirm metrics contain no transcript/user content, and attach screenshots/exported evidence to the release record. This external alert-routing evidence is an acceptance requirement and cannot be proven by repository tests alone.
