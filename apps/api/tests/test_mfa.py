import json

import pytest
from fastapi import HTTPException

from meeting_intelligence.auth import _totp_at, _verify_totp, authenticate_principal
from meeting_intelligence.config import Settings

# Public RFC 6238 test vector, not a deployable credential.
_RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # noqa: S105


def test_totp_matches_rfc6238_sha1_vector_at_59_seconds() -> None:
    assert _totp_at(_RFC_SECRET, 59) == "287082"


def test_totp_accepts_adjacent_clock_step_and_rejects_bad_codes() -> None:
    code = _totp_at(_RFC_SECRET, 60)
    assert _verify_totp(_RFC_SECRET, code, now=60)
    assert _verify_totp(_RFC_SECRET, code, now=89)
    assert not _verify_totp(_RFC_SECRET, code, now=120)
    assert not _verify_totp(_RFC_SECRET, "abcdef", now=60)
    assert not _verify_totp(_RFC_SECRET, "12345", now=60)


def test_workspace_principal_with_totp_requires_second_factor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("meeting_intelligence.auth.time.time", lambda: 60)
    settings = Settings(
        RAEBURN_ENV="test",
        RAEBURN_API_KEY="bootstrap-test-key",
        RAEBURN_WORKSPACE_API_KEYS=json.dumps(
            {
                "workspace-key": {
                    "workspace_id": "acme",
                    "role": "approver",
                    "subject": "alice@example.com",
                    "totp_secret": _RFC_SECRET,
                }
            }
        ),
        DATABASE_URL="sqlite+pysqlite:///:memory:",
    )

    with pytest.raises(HTTPException) as missing:
        authenticate_principal(
            x_api_key="workspace-key", x_totp_code=None, settings=settings
        )
    assert missing.value.status_code == 401
    assert missing.value.detail == "Valid MFA code required"

    with pytest.raises(HTTPException) as invalid:
        authenticate_principal(
            x_api_key="workspace-key", x_totp_code="000000", settings=settings
        )
    assert invalid.value.status_code == 401

    principal = authenticate_principal(
        x_api_key="workspace-key",
        x_totp_code=_totp_at(_RFC_SECRET, 60),
        settings=settings,
    )
    assert principal.workspace_id == "acme"
    assert principal.subject == "alice@example.com"


def test_principal_without_totp_remains_backward_compatible() -> None:
    settings = Settings(
        RAEBURN_ENV="test",
        RAEBURN_API_KEY="bootstrap-test-key",
        RAEBURN_WORKSPACE_API_KEYS=json.dumps(
            {
                "workspace-key": {
                    "workspace_id": "acme",
                    "role": "viewer",
                    "subject": "reader@example.com",
                }
            }
        ),
        DATABASE_URL="sqlite+pysqlite:///:memory:",
    )

    principal = authenticate_principal(
        x_api_key="workspace-key", x_totp_code=None, settings=settings
    )
    assert principal.role.value == "viewer"
