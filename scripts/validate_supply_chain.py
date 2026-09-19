from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
SHA40 = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
USES = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)(?:\s+#.*)?$", re.MULTILINE)
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}", re.IGNORECASE)
failures: list[str] = []


def read(relative: str) -> str:
    path = ROOT / relative
    if not path.exists():
        failures.append(f"{relative} is required")
        return ""
    return path.read_text(encoding="utf-8")


def require(source: str, relative: str, label: str, marker: str) -> None:
    if marker not in source:
        failures.append(f"{relative} is missing {label}: {marker}")


workflow_sources: dict[str, str] = {}
for path in sorted(WORKFLOWS.glob("*.y*ml")):
    relative = str(path.relative_to(ROOT))
    source = path.read_text(encoding="utf-8")
    workflow_sources[relative] = source
    for reference in USES.findall(source):
        if reference.startswith("./") or reference.startswith("docker://"):
            continue
        action, sep, ref = reference.rpartition("@")
        if not sep or not action or not SHA40.fullmatch(ref):
            failures.append(
                f"{relative} must pin third-party action to a 40-character commit SHA: {reference}"
            )

read("apps/api/requirements.lock")
read("apps/api/requirements-dev.lock")
read("apps/web/package-lock.json")

for dockerfile in ("apps/api/Dockerfile", "apps/web/Dockerfile"):
    source = read(dockerfile)
    first_from = next((line for line in source.splitlines() if line.startswith("FROM ")), "")
    if not DIGEST.search(first_from):
        failures.append(f"{dockerfile} must pin its base image by sha256 digest")

api_docker = read("apps/api/Dockerfile")
web_docker = read("apps/web/Dockerfile")
require(api_docker, "apps/api/Dockerfile", "hash-locked Python install", "--require-hashes -r requirements.lock")
require(web_docker, "apps/web/Dockerfile", "deterministic npm install", "npm ci --ignore-scripts --no-audit --no-fund")

compose = read("docker-compose.yml")
for image in ("postgres:16-alpine", "redis:7-alpine"):
    line = next((line for line in compose.splitlines() if f"image: {image}" in line), "")
    if not DIGEST.search(line):
        failures.append(f"docker-compose.yml must pin {image} by sha256 digest")

hardening = read(".github/workflows/hardening-verification.yml")
for marker in (
    "python scripts/validate_supply_chain.py",
    "pip-audit -r requirements.lock",
    "npm audit --audit-level=high",
    "aquasecurity/trivy-action@",
    "meeting-intelligence-api:" + "$" + "{{ github.sha }}",
    "meeting-intelligence-web:" + "$" + "{{ github.sha }}",
    "http://127.0.0.1:8080/healthz",
    "http://127.0.0.1:3000/",
):
    require(hardening, ".github/workflows/hardening-verification.yml", "required hardening control", marker)
if "ignore-unfixed: true" in hardening:
    failures.append(".github/workflows/hardening-verification.yml must not suppress unfixed High/Critical findings")

for legacy in (".github/workflows/provenance.yml", ".github/workflows/release-signing.yml"):
    if (ROOT / legacy).exists():
        failures.append(f"{legacy} must be removed; release assets require one canonical owner")

release_path = ".github/workflows/release-trust.yml"
release = read(release_path)
for marker in (
    "workflow_call:",
    "git archive --format=tar",
    "gzip -n",
    "spdx-json",
    "cyclonedx-json",
    "SHA256SUMS",
    "cosign sign-blob",
    "cosign verify-blob",
    "actions/attest@",
    "gh attestation verify",
    "gh release upload",
):
    require(release, release_path, "release trust control", marker)

upload_count = release.count("gh release upload")
if upload_count != 1:
    failures.append(
        f"{release_path} must contain exactly one gh release upload command; found {upload_count}"
    )

owners = [
    name
    for name, source in workflow_sources.items()
    if "gh release upload" in source or re.search(r"upload-release-assets:\s*true", source)
]
if owners != [release_path]:
    failures.append(
        "release assets must have exactly one canonical workflow owner; found: "
        + (", ".join(owners) if owners else "none")
    )

sbom = read(".github/workflows/sbom.yml")
require(sbom, ".github/workflows/sbom.yml", "repository-only release setting", "upload-release-assets: false")
if re.search(r"\brelease:\s*\n\s*types:\s*\[published\]", sbom):
    failures.append(".github/workflows/sbom.yml must not own release-event packaging")

policy = read("docs/software-supply-chain.md")
require(policy, "docs/software-supply-chain.md", "Critical remediation expectation", "**Critical:**")
require(policy, "docs/software-supply-chain.md", "High remediation expectation", "**High:**")
require(policy, "docs/software-supply-chain.md", "real release evidence boundary", "Real release evidence")

if failures:
    print("Software supply-chain policy validation failed:")
    for failure in failures:
        print(f"- {failure}")
    raise SystemExit(1)

print(
    "Software supply-chain policy validated: immutable action refs, digest-pinned "
    "images, strict vulnerability/runtime gates and one canonical release owner are present."
)
