#!/usr/bin/env python3
"""Fail CI when high-confidence secrets are committed to tracked files.

This intentionally scans only Git-tracked text files so generated artifacts and
local ignored files cannot make CI flaky. Patterns are limited to credential
formats with strong identifying prefixes; generic words such as ``password`` or
``api_key`` are not treated as secrets because configuration examples and tests
legitimately contain those names.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# High-confidence credential formats. Keep these deliberately specific to avoid
# teaching contributors to silence a noisy scanner with broad allowlists.
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("Stripe live secret", re.compile(r"\bsk_live_[A-Za-z0-9]{20,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("OpenAI API key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
)

# These extensions are commonly binary and are not useful to decode as source.
BINARY_SUFFIXES = {
    ".7z",
    ".avif",
    ".bin",
    ".bmp",
    ".class",
    ".dll",
    ".eot",
    ".gif",
    ".gz",
    ".ico",
    ".jar",
    ".jpeg",
    ".jpg",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".so",
    ".tar",
    ".ttf",
    ".webp",
    ".woff",
    ".woff2",
    ".zip",
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def scan_file(path: Path) -> list[tuple[int, str]]:
    if path.suffix.lower() in BINARY_SUFFIXES:
        return []

    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    findings: list[tuple[int, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for name, pattern in PATTERNS:
            if pattern.search(line):
                findings.append((line_number, name))
    return findings


def main() -> int:
    findings: list[tuple[Path, int, str]] = []
    for path in tracked_files():
        for line_number, name in scan_file(path):
            findings.append((path.relative_to(ROOT), line_number, name))

    if findings:
        print("Potential committed secrets detected:", file=sys.stderr)
        for path, line_number, name in findings:
            # Do not print the matching line or secret value into CI logs.
            print(f"  {path}:{line_number}: {name}", file=sys.stderr)
        return 1

    print("Secret scan passed: no high-confidence credential patterns found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
