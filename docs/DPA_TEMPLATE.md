# Data Processing Addendum Template

> Engineering template only. This document must be reviewed and approved by the organisation's legal/privacy owner before customer execution. It is designed to ensure the product's technical controls and contractual commitments are described consistently.

## 1. Parties and scope

This Data Processing Addendum (DPA) forms part of the agreement between the customer (the **Controller**) and the Meeting Intelligence service operator (the **Processor**) for processing personal data through Meeting Intelligence.

The Processor will process personal data only to provide, secure, support and maintain the Meeting Intelligence service and only on documented instructions from the Controller, unless processing is required by applicable law.

## 2. Processing details

| Item | Description |
| --- | --- |
| Subject matter | Meeting transcription/intelligence processing, approvals, audit records and approved integration writebacks |
| Duration | For the term of the customer agreement plus the documented deletion/backup-expiry period |
| Purpose | Extract summaries, decisions, actions and risks; support approval workflows; execute approved integrations; provide auditability |
| Data subjects | Customer users, meeting participants, contacts and other individuals referenced in customer-provided meeting content |
| Personal data categories | Meeting content, names/user identifiers, speaker labels, business contact data, extracted decisions/actions, integration identifiers and limited operational metadata |
| Special-category data | Not intentionally required. Customers should avoid unnecessary capture; any unavoidable processing must be specifically authorised and documented |

## 3. Processor obligations

The Processor will:

1. process personal data only on documented Controller instructions;
2. ensure authorised personnel are subject to confidentiality obligations;
3. implement appropriate technical and organisational security measures;
4. assist the Controller with data-subject requests where reasonably necessary;
5. assist with security, breach, DPIA and regulator-consultation obligations where applicable;
6. delete or return personal data at termination according to documented retention and backup-expiry controls, unless law requires retention;
7. maintain records sufficient to demonstrate compliance with these obligations; and
8. make appropriate audit/assurance information available subject to reasonable confidentiality and security constraints.

## 4. Security measures

The service's minimum technical baseline includes:

- TLS for data in transit;
- encryption at rest for production durable stores;
- workspace-scoped authentication and role-based access control;
- least-privilege workspace-specific integration credentials;
- human approval before external writebacks by default;
- MFA capability for workspace principals;
- durable audit, approval and dispatch state;
- transcript-safe operational logging;
- dependency, secret, static-analysis and container security gates;
- documented incident response, credential rotation, backup/restore and rollback procedures;
- configurable retention, export and deletion controls.

The authoritative implementation baseline is maintained in `docs/PRIVACY_AND_DATA_GOVERNANCE.md`, `SECURITY.md`, `docs/OPERATIONS_RUNBOOK.md` and `docs/PRODUCTION_RECOVERY_DRILL.md`.

## 5. Subprocessors

The Controller authorises the Processor to use subprocessors listed in the production subprocessor register, subject to the agreed notification mechanism.

The Processor will:

- perform proportionate due diligence before onboarding a subprocessor;
- impose data-protection obligations materially equivalent to those applicable to the Processor;
- remain responsible for the subprocessor's processing to the extent required by applicable law and contract;
- maintain a current register describing purpose, data categories and processing region; and
- provide advance notice of material subprocessor changes using the contractual notification channel.

See `docs/SUBPROCESSOR_REGISTER.md` for the release-gate register and required evidence.

## 6. International transfers

Where personal data is transferred internationally, the parties will use an applicable lawful transfer mechanism. The production record must identify the mechanism used for each relevant subprocessor or hosting arrangement rather than relying on generic provider marketing statements.

Where applicable, this may include an adequacy decision, EU Standard Contractual Clauses, the UK International Data Transfer Agreement/Addendum, or another mechanism recognised by the governing law.

## 7. Data-subject requests

The Processor will provide reasonable assistance for authenticated requests involving access, correction, export, restriction or deletion. The operational process must verify workspace authority and avoid copying customer content into support or incident records unless strictly required.

## 8. Retention and deletion

Production workspaces must have an explicit retention policy. Unless a customer contract specifies otherwise, engineering defaults and deletion propagation requirements are defined in `docs/PRIVACY_AND_DATA_GOVERNANCE.md`.

Deletion must cover active application data, derived records, pending/dead-letter jobs, caches and applicable backups according to the documented backup-expiry schedule. Audit evidence may retain non-content metadata needed to prove that deletion occurred.

## 9. Security incidents and personal-data breaches

The Processor will maintain an incident-response process and notify the Controller without undue delay after confirming a personal-data breach affecting Controller data, subject to the specific timeframe and content agreed in the customer contract.

Notifications should include, as information becomes available:

- nature and scope of the incident;
- affected data categories and workspaces;
- containment and remediation steps;
- likely consequences where known; and
- contact point for follow-up.

The Processor will not make unsupported claims about regulatory notification obligations or breach severity before appropriate assessment.

## 10. Audit and assurance

Before enterprise deployment, the operator should be able to provide appropriate evidence of the implemented security and privacy controls, such as current CI/security-gate results, architecture/runbook documentation, recovery-drill evidence and independent security review results where required by the customer agreement.

Any customer audit right should be exercised with reasonable notice and safeguards that protect other customers, system security and confidential information.

## 11. Termination

At termination, the Processor will delete or return Controller personal data according to the Controller's documented instruction and the service's retention/backup-expiry process, unless retention is legally required.

## 12. Required commercial completion fields

The final executed DPA must not leave the following unresolved:

- legal names and addresses of both parties;
- governing agreement and effective date;
- applicable law/jurisdiction;
- customer-specific processing instructions;
- approved production subprocessors;
- international-transfer mechanism where relevant;
- breach-notification timeframe/channel;
- audit/assurance mechanism;
- retention/deletion commitments that differ from service defaults; and
- authorised signatories.

This template is considered documentation-complete only as an engineering baseline. Customer execution still requires legal/privacy approval and deployment-specific values.