from __future__ import annotations

import hmac
import json
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


class Principal(BaseModel):
    workspace_id: str
    role: WorkspaceRole
    subject: str


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
        if not all(isinstance(item, str) and item for item in (workspace_id, role, subject)):
            raise RuntimeError(
                "workspace API-key entries require workspace_id, role and subject"
            )
        try:
            parsed_role = WorkspaceRole(role)
        except ValueError as exc:
            raise RuntimeError(f"unsupported workspace role: {role}") from exc
        principals[api_key] = Principal(
            workspace_id=workspace_id,
            role=parsed_role,
            subject=subject,
        )
    return principals


def authenticate_principal(
    x_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> Principal:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    if hmac.compare_digest(x_api_key, settings.api_key):
        return Principal(
            workspace_id=settings.bootstrap_workspace_id,
            role=WorkspaceRole.admin,
            subject="bootstrap-admin",
        )

    for api_key, principal in _configured_principals(settings).items():
        if hmac.compare_digest(x_api_key, api_key):
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
