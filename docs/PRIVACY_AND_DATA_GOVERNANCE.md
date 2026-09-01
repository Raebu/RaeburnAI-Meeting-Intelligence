# Privacy and Data Governance

This document defines the minimum privacy, retention and processor-governance controls required before Meeting Intelligence is used with production customer data. It is an engineering and operational baseline, not legal advice and not a substitute for a customer-specific data processing agreement (DPA).

## 1. Current production-readiness status

Meeting Intelligence is not yet approved for unrestricted production use with authoritative external writebacks.

Known limitations that materially affect privacy and data governance include:

- meeting/result storage is not yet fully durable across restarts;
- organisation/workspace isolation and full RBAC are not yet complete;
- per-workspace least-privilege integration credentials are not yet complete;
- durable queueing, persisted approvals and audit events are not yet complete;
- automated retention-policy enforcement is not yet complete;
- the complete subprocessor list must be finalised from the actual production deployment and enabled integrations.

Until those controls exist, production deployments must minimise customer data, keep external writebacks approval-gated, and avoid representing this service as enterprise-ready.

## 2. Data categories

The service may process the following data categories depending on configuration and integrations:

| Category | Examples | Default handling expectation |
| --- | --- | --- |
| Meeting source data | transcript text, speaker labels, timestamps | minimise, encrypt in transit/at rest, apply retention policy |
| Extracted intelligence | summaries, decisions, action items, risks | treat as customer confidential data |
| Identity data | user/workspace identifiers, approver identity | minimise and restrict to authorised workspace members |
| Integration data | CRM/Jira/GitHub/email identifiers and command payloads | least privilege, approval-gated writeback |
| Operational metadata | request IDs, hashed/redacted references, timing, status | transcript-safe logging only |
| Credentials/secrets | API keys, OAuth tokens, webhook secrets | secret manager only; never log or persist in plaintext application data |

Do not ingest special-category/sensitive personal data merely because a source system contains it. Customers and operators should configure meeting capture to avoid unnecessary data collection.

## 3. Roles and responsibility model

For customer-provided meeting content, the customer is normally expected to determine purpose and means of processing and therefore act as controller (or equivalent role under the applicable law), while the service operator acts as processor/service provider.

The production DPA must define at minimum:

- subject matter and duration of processing;
- nature and purpose of processing;
- categories of personal data and data subjects;
- confidentiality obligations;
- documented-instruction requirements;
- security controls;
- subprocessor authorisation and change notification;
- data-subject request assistance;
- breach/incident notification obligations;
- deletion/return at termination;
- audit and assurance rights;
- international transfer mechanism where applicable.

Do not claim a jurisdiction-specific compliance status until counsel or the responsible compliance owner has reviewed the actual deployment, contracts and subprocessors.

## 4. Data minimisation

Production integrations must request only scopes required for the enabled workflow.

Minimum rules:

1. Do not collect a complete upstream object when only a subset of fields is needed.
2. Do not persist provider responses that are not required for retry, audit or customer functionality.
3. Do not duplicate transcripts into logs, exception messages, traces or analytics.
4. Use stable redacted references in operational logs rather than raw meeting, actor, IP or customer identifiers.
5. Disable optional telemetry that would expose customer content unless explicitly reviewed and documented.
6. Store integration credentials separately from meeting and extracted-content records.

## 5. Retention policy

Every production workspace must have an explicit retention configuration before customer data is accepted. A deployment must not silently retain meeting content forever.

Recommended baseline configuration:

| Data class | Suggested default | Notes |
| --- | ---: | --- |
| Raw transcript/source content | 30 days | shorten where operationally possible |
| Extracted meeting intelligence | 90 days | customer-configurable subject to contractual needs |
| Approval/audit events | 1 year | must not include raw transcript payloads |
| Operational logs | 30 days | identifiers must remain redacted/hashed |
| Security audit logs | 1 year | retain only metadata needed for security/audit |
| Backups | 35 days | deletion must age out of backups on a documented schedule |

These are engineering defaults, not universal legal requirements. A customer's contract, regulatory environment or lawful instruction may require shorter or longer periods.

Automated expiry must ultimately be enforced by the persistent storage layer. Until that exists, any deployment with customer data requires an operator-owned manual deletion process and must be treated as pre-production/limited use.

## 6. Deletion and export

The API provides authenticated meeting export and deletion controls. Production behaviour must additionally ensure deletion is propagated through all durable stores once they exist.

A complete deletion workflow must cover:

- primary meeting/transcript records;
- extracted decisions/actions/results;
- pending queue messages and dead-letter items;
- integration command payloads where deletion is legally/contractually required;
- search/vector indexes if introduced;
- caches;
- derived files/artifacts;
- backups according to the documented backup expiry schedule.

Deletion must be idempotent, auditable without retaining deleted content, and scoped to the correct workspace/tenant.

Exports must be authenticated, non-cacheable by shared caches, workspace-scoped, and produce only data the requester is authorised to access.

## 7. Subprocessors

The subprocessor register must reflect the exact production architecture, enabled providers and deployment region. Do not maintain a fictional or aspirational list.

For each subprocessor record:

- legal entity and service name;
- purpose of processing;
- categories of data received;
- processing/storage location or region;
- transfer mechanism where relevant;
- security/compliance evidence reviewed;
- DPA or equivalent contractual terms;
- date approved;
- owner and review date;
- deletion/retention behaviour;
- customer notification requirements for changes.

Suggested register format:

| Provider | Purpose | Data shared | Region | Contract/DPA reviewed | Owner | Last review |
| --- | --- | --- | --- | --- | --- | --- |
| _Populate from actual deployment_ | | | | | | |

The production release gate requires this table (or the organisation's authoritative external register) to be populated for every enabled third party that processes customer personal data.

## 8. International transfers

Before enabling a production subprocessor outside the customer's relevant jurisdiction, confirm the required transfer mechanism and contractual terms. Examples may include adequacy decisions, the UK IDTA/Addendum, EU Standard Contractual Clauses, or another lawful mechanism applicable to the deployment.

Do not infer transfer compliance from a provider's marketing page alone.

## 9. Data-subject and customer requests

The operator must maintain a documented process for access, deletion, correction and export requests.

At minimum:

1. authenticate the requester and verify tenant/workspace authority;
2. locate data across primary storage, extracted records, audit metadata and downstream integrations as applicable;
3. preserve an audit record of the request without copying the underlying content into logs;
4. perform or coordinate the requested action within contractual/legal timelines;
5. verify completion across active stores and document backup-expiry behaviour;
6. notify the customer of completion or any lawful limitation.

## 10. Security requirements for personal data

Production deployments must maintain:

- TLS for data in transit;
- encryption at rest for durable customer-data stores;
- secret-manager-backed credentials;
- least-privilege workspace-scoped access;
- explicit human approval for external writebacks;
- tenant/workspace isolation;
- MFA/SSO path for commercial customers;
- transcript-safe structured logging;
- dependency, secret, CodeQL and container scanning gates;
- incident response and credential-rotation procedures;
- tested backup/restore once durable persistence is implemented.

## 11. Incident and breach handling

Follow `docs/OPERATIONS_RUNBOOK.md` for immediate containment and evidence handling.

For an incident involving personal data:

1. stop further exposure while preserving necessary evidence;
2. identify affected workspaces, data categories, timeframe and subprocessors;
3. avoid placing transcript/customer content into incident chat or tickets unless strictly required and access-controlled;
4. notify the responsible privacy/security owner immediately;
5. assess contractual and statutory notification requirements;
6. document decisions, remediation and verification;
7. rotate affected credentials and invalidate tokens where relevant;
8. perform a post-incident review and implement preventive controls.

## 12. Privacy review release gate

Before the service is described as production-ready, verify all of the following:

- [ ] durable workspace-scoped persistence is deployed and migration-reviewed;
- [ ] automated retention and deletion propagation are tested;
- [ ] export/deletion access is tenant-scoped and authorised;
- [ ] full RBAC and least-privilege integration credentials are enforced;
- [ ] persisted audit events do not contain transcripts or secrets;
- [ ] DPA template/terms are approved by the responsible legal/compliance owner;
- [ ] production subprocessor register is complete and reviewed;
- [ ] international transfer mechanism is documented where applicable;
- [ ] data-subject/customer request process has an accountable owner;
- [ ] backup deletion/expiry is documented and restore tested;
- [ ] privacy/security incident notification process is documented;
- [ ] customer-facing privacy/retention statements match actual system behaviour.

No checkbox in this document should be treated as satisfied solely because documentation exists; each control requires implementation or operational evidence.