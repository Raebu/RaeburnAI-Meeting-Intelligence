from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import httpx
import pytest

from meeting_intelligence.config import Settings
from meeting_intelligence.dispatch_worker import _adapter_for
from meeting_intelligence.integrations import HubSpotAdapter
from meeting_intelligence.schemas import ApprovalStatus, IntegrationCommand


class StubAsyncClient:
    last_url: str | None = None
    last_headers: dict[str, str] | None = None
    last_json: dict[str, Any] | None = None

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    async def __aenter__(self) -> StubAsyncClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        del args

    async def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        type(self).last_url = url
        type(self).last_headers = kwargs.get("headers")
        type(self).last_json = kwargs.get("json")
        request = httpx.Request("PATCH", url)
        return httpx.Response(200, json={"id": "deal-42"}, request=request)


@pytest.mark.asyncio
async def test_hubspot_uses_only_requested_workspace_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "meeting_intelligence.integrations.httpx.AsyncClient", StubAsyncClient
    )
    workspace_integrations = json.dumps(
        {
            "alpha": {"crm": {"api_key": "alpha-token"}},
            "beta": {"crm": {"api_key": "beta-token"}},
        }
    )
    settings = Settings(
        RAEBURN_ENV="test",
        RAEBURN_API_KEY="test-key",
        DATABASE_URL="sqlite+pysqlite:///:memory:",
        CRM_WRITEBACK_ENABLED=True,
        RAEBURN_WORKSPACE_INTEGRATIONS=workspace_integrations,
    )
    adapter = _adapter_for(settings, "alpha", "crm")
    assert isinstance(adapter, HubSpotAdapter)

    command = IntegrationCommand(
        id=uuid4(),
        system="crm",
        operation="update_meeting_summary",
        payload={
            "deal_id": "deal-42",
            "summary": "Approved meeting summary",
            "next_step": "Send proposal",
        },
        approval_status=ApprovalStatus.approved,
    )
    result = await adapter.dispatch(command)

    assert result.status == "dispatched"
    assert StubAsyncClient.last_url == (
        "https://api.hubapi.com/crm/v3/objects/deals/deal-42"
    )
    assert StubAsyncClient.last_headers is not None
    assert StubAsyncClient.last_headers["Authorization"] == "Bearer alpha-token"
    assert "beta-token" not in json.dumps(StubAsyncClient.last_headers)
    assert StubAsyncClient.last_json == {
        "properties": {
            "description": "Approved meeting summary",
            "hs_next_step": "Send proposal",
        }
    }


@pytest.mark.asyncio
async def test_production_adapter_does_not_fall_back_to_global_credentials() -> None:
    settings = Settings(
        RAEBURN_ENV="production",
        RAEBURN_API_KEY="a" * 32,
        RAEBURN_PUBLIC_BASE_URL="https://meeting.example.com",
        RAEBURN_CORS_ORIGINS="https://meeting.example.com",
        DATABASE_URL="postgresql+psycopg://user:pass@db/meeting_intelligence",
        CRM_WRITEBACK_ENABLED=True,
        CRM_API_KEY="global-token-that-must-not-be-used",
        RAEBURN_WORKSPACE_INTEGRATIONS=json.dumps(
            {"configured": {"crm": {"api_key": "workspace-token"}}}
        ),
    )
    adapter = _adapter_for(settings, "unconfigured", "crm")
    command = IntegrationCommand(
        system="crm",
        operation="update_meeting_summary",
        payload={"deal_id": "deal-1", "summary": "Summary"},
        approval_status=ApprovalStatus.approved,
    )

    result = await adapter.dispatch(command)

    assert result.status == "failed"
    assert result.detail == "missing workspace config"
