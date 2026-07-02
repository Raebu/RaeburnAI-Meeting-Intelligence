from __future__ import annotations

from typing import Any

import httpx


class MeetingIntelligenceClient:
    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"content-type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    async def analyse_meeting(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/v1/meetings/analyse",
                headers=self._headers(),
                json=payload,
            )
        response.raise_for_status()
        return response.json()

    async def get_result(self, meeting_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/v1/meetings/{meeting_id}",
                headers=self._headers(),
            )
        response.raise_for_status()
        return response.json()
