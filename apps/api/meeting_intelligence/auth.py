from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import struct
import time
from enum import StrEnum
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel

from meeting_intelligence.config import Settings, get_settings


class WorkspaceRole(StrEnum):
    viewer = "viewer"
    operator = "operator"
    approver = "approver"
    admin = "admin"


_ROLE_RANK = {
    WorkspaceRole.viewer: 10,
    WorkspaceRole.operator: 20,
    WorkspaceRole.approver: 30,
    WorkspaceRole.admin: 40,
}
_TOTP_PERIOD_SECONDS = 30
_TOTP_DIGITS = 6
_TOTP_WINDOW = 1


class Principal(BaseModel):
    workspace_id: str
    role: WorkspaceRole
    subject: str
    totp_secret: str | None = None


def _configured_principals(settings: Settings) -> dict[str, Principal]:
    try:
        raw = json.loads(settings.workspace_api_keys_json)
    except json.JSONDecodeError as exc:
        raise RuntimeError("RAEBURN_WORKSPACE_API_KEYS must be valid JSON") from exc
    if not isinstance(raw, dict):
        raise RuntimeError("RAEBURN_WORKSPACE_API_KEYS must be a JSON object")

    principals: dict[str, Principal] = {}
    for api_key, value in raw.items():
        if not isinstance(api_key, str) or not isinstance(value, dict):
            raise RuntimeError("workspace API-key entries must map strings to objects")
        workspace_id = value.get("workspace_id")
        role = value.get("role")
        subject = value.get("subject")
        if not all(
            isinstance(item, str) and item for item in (workspace_id, role, subject)
        ):
            raise RuntimeError(
                "workspace API-key entries require workspace_id, role and subject"
            )
        try:
            parsed_role = WorkspaceRole(str(role))
        except ValueError as exc:
            raise RuntimeError(f"unsupported workspace role: {role}") from exc
        totp_secret = value.get("totp_secret")
        if totp_secret is not None and not isinstance(totp_secret, str):
            raise RuntimeError("workspace totp_secret must be a string")
        principals[api_key] = Principal(
            workspace_id=str(workspace_id),
            role=parsed_role,
            subject=str(subject),
            totp_secret=totp_secret,
        )
    return principals


def _decode_totp_secret(secret: str) -> bytes:
    normalized = "".join(secret.upper().split())
    padding = "=" * ((8 - len(normalized) % 8) % 8)
    try:
        decoded = base64.b32decode(normalized + padding, casefold=True)
    except (binascii.Error, ValueError) as exc:
        raise RuntimeError("workspace totp_secret must be valid Base32") from exc
    if len(decoded) < 20:
        raise RuntimeError("workspace totp_secret must decode to at least 20 bytes")
    return decoded


def _totp_at(secret: str, timestamp: int) -> str:
    key = _decode_totp_secret(secret)
    counter = timestamp // _TOTP_PERIOD_SECONDS
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{binary % (10**_TOTP_DIGITS):0{_TOTP_DIGITS}d}"


def _verify_totp(secret: str, supplied_code: str | None, now: int | None = None) -> bool:
    if supplied_code is None or len(supplied_code) != _TOTP_DIGITS or not supplied_code.isdigit():
        return False
    current = int(time.time()) if now is None else now
    return any(
        hmac.compare_digest(
            _totp_at(secret, current + offset * _TOTP_PERIOD_SECONDS), supplied_code
        )
        for offset in range(-_TOTP_WINDOW, _TOTP_WINDOW + 1)
    )


def _enforce_mfa(principal: Principal, supplied_code: str | None) -> None:
    if not principal.totp_secret:
        return
    if not _verify_totp(principal.totp_secret, supplied_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid MFA code required",
            headers={"WWW-Authenticate": "TOTP"},
        )


def authenticate_principal(
    x_api_key: str | None = Header(default=None),
    x_totp_code: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> Principal:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    if hmac.compare_digest(x_api_key, settings.api_key):
        principal = Principal(
            workspace_id=settings.bootstrap_workspace_id,
            role=WorkspaceRole.admin,
            subject="bootstrap-admin",
            totp_secret=settings.bootstrap_totp_secret,
        )
        _enforce_mfa(principal, x_totp_code)
        return principal

    for api_key, principal in _configured_principals(settings).items():
        if hmac.compare_digest(x_api_key, api_key):
            _enforce_mfa(principal, x_totp_code)
            return principal

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )


def require_role(minimum_role: WorkspaceRole) -> Any:
    def dependency(principal: Principal = Depends(authenticate_principal)) -> Principal:
        if _ROLE_RANK[principal.role] < _ROLE_RANK[minimum_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient workspace role",
            )
        return principal

    return dependency
