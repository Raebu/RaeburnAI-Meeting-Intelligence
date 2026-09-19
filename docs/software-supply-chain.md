# Software supply-chain policy

RaeburnAI Meeting Intelligence treats dependency locks, workflow definitions, production images and release evidence as security boundaries.

## Dependency integrity

- API production and dev environments are committed as hash-locked `requirements.lock` and `requirements-dev.lock`.
- API hardening installs the dev lock with `--require-hashes` and audits the production lock with `pip-audit`.
- Web dependencies are committed in `package-lock.json`, installed with `npm ci` and blocked on High/Critical npm audit findings.

## Workflow and container integrity

- Third-party GitHub Actions must use full 40-character commit SHAs.
- API and web images are built with exact Git SHA tags in hardening verification.
- Trivy blocks High/Critical image findings without `ignore-unfixed` suppression.
- The hardening workflow starts both exact images and verifies API `/healthz` plus the web root before passing.
- API uses the verified multi-platform `python:3.12-alpine3.24` OCI index and a separate build/runtime layout that strips pip/setuptools/wheel from runtime.
- Web uses the verified multi-platform Node 22.23.2/Alpine 3.24 OCI index, strips package-manager frontends and runs as the non-root `node` user.
- Compose Postgres and Redis dependencies are pinned to verified OCI indexes.

Verified OCI indexes resolved on a clean GitHub-hosted runner on 2026-09-19:
- Python 3.12 / Alpine 3.24: `sha256:c4634f578a412db396771b61b064c6e546c9d6414c7fb5b1b05d5871f1885f7b`
- Node 22.23.2 / Alpine 3.24: `sha256:b6f26b36c8ff49624cfdac716b8ea1138d606df02586a77d364bb5536a634f85`
- Postgres 16 Alpine: `sha256:3c5c8892d184f738f4fe282d14ddaa613a38f00f4189d2d94725ebe6f2909ddb`
- Redis 7 Alpine: `sha256:520775a41a63e77e06c73e35d2fd9cc15921a609516818796b4ecbb813078bc7`

## Release trust evidence

`.github/workflows/release-trust.yml` is the sole owner of GitHub release file assets. It verifies the exact tag, creates one deterministic `git archive | gzip -n`, generates isolated SPDX and CycloneDX SBOMs, creates one SHA-256 manifest, signs the archive/checksums/SBOMs with keyless Sigstore, creates GitHub build provenance and both SBOM attestations, verifies checksums/Sigstore/GitHub attestation before publication, and performs exactly one `gh release upload`.

`.github/workflows/sbom.yml` remains repository-SBOM-only. The prior independent provenance and release-signing workflows are intentionally removed because independently recreated/clobbered archives can make trust evidence refer to different bytes.

Container publication remains separate: `publish-containers.yml` owns GHCR release images with BuildKit provenance/SBOM metadata and does not own GitHub release file assets.

**Real release evidence** requires an executed exact-tag trust workflow plus inspection of the published assets. Workflow source alone is Coded evidence.

## Remediation expectations

- **Critical:** block release immediately and remediate as soon as practicable, normally within 24 hours. Any exception must be explicit, time-bounded, owned and document compensating controls.
- **High:** block release and remediate normally within 7 days or use the same governed exception process.
- **Medium/Low:** triage based on exploitability, reachability and impact.

Security gates are not weakened merely to make CI green.
