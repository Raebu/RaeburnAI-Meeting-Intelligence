# Production Subprocessor Register

This register is the release-gate template for third parties that process customer personal data on behalf of Meeting Intelligence. It must reflect the **actual enabled production architecture**, not every provider the codebase is capable of integrating with.

No provider should be listed as approved until deployment ownership, contractual terms and data flows have been verified.

## Required register

| Provider / legal entity | Service / purpose | Customer data received | Processing / storage region | Contract / DPA reviewed | Transfer mechanism | Retention / deletion verified | Security evidence reviewed | Owner | Last review | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| _Populate before production use_ | | | | | | | | | | Pending |

## Inclusion rules

Add a provider when it can receive, store or otherwise process customer personal data while operating the production service. Typical categories may include:

- infrastructure/database hosting;
- model or inference providers receiving meeting content;
- observability vendors if telemetry can contain customer-related metadata;
- email delivery providers;
- CRM, Jira, GitHub or webhook destinations when operated as processor subprocessors rather than independently controlled customer destinations;
- backup/storage providers; and
- support tooling if customer data is intentionally transferred into it.

Do **not** add a provider merely because an optional adapter exists in the repository. A customer-controlled destination may instead be a third party selected by the Controller; that classification must be documented in the customer contract and data-flow record.

## Approval evidence

Before changing a row from `Pending` to `Approved`, record or link evidence for all applicable items:

1. exact legal entity and contracted service;
2. production region(s) and any support-access locations;
3. categories of customer data transmitted or stored;
4. signed DPA/processor terms or equivalent contractual protection;
5. international-transfer mechanism if data leaves the applicable jurisdiction;
6. retention and deletion behaviour, including backups;
7. security/compliance evidence proportionate to risk;
8. least-privilege configuration and scopes;
9. subprocessor-change notification mechanism; and
10. accountable internal owner and next review date.

## Change control

A new or materially changed subprocessor must not silently enter production. The operator must:

1. update this register or the organisation's authoritative external register;
2. complete the approval evidence above;
3. determine whether customer notice or consent is contractually required;
4. verify the production data flow and least-privilege configuration;
5. update the DPA/privacy documentation if the processing purpose or data categories change; and
6. record the review date and owner.

## Removal

When a provider is removed:

- stop new data transfers;
- revoke credentials/tokens;
- request or verify deletion according to contract;
- allow only documented backup-expiry retention where unavoidable;
- retain non-sensitive evidence that offboarding completed; and
- mark the row `Removed` with the effective date rather than erasing the historical governance record.

## Review cadence

Review the active register at least annually and additionally before an enterprise release, after a material architecture change, after a provider security incident affecting the service, or before enabling a new region/data flow.

A populated and reviewed register is deployment evidence. This template by itself does not prove that production subprocessors have been approved.