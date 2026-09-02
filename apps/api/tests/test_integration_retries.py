from __future__ import annotations

from collections import deque

import httpx
import pytest

from meeting_intelligence import integrations


class StubAsyncClient:
    def __init__(self, outcomes: list[httpx.Response | Exception]) -> None:
        self.outcomes = deque(outcomes)
        self.calls = 0

    async def post(self, url: str, **kwargs: object) -> httpx.Response:
        del url, kwargs
        self.calls += 1
        outcome = self.outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.mark.asyncio
async def test_post_with_retry_retries_transient_status(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_sleep(delay: float) -> None:
        del delay

    monkeypatch.setattr(integrations.asyncio, "sleep", no_sleep)
    client = StubAsyncClient([httpx.Response(503), httpx.Response(200)])

    response = await integrations._post_with_retry(client, "https://example.test")  # type: ignore[arg-type]

    assert response.status_code == 200
    assert client.calls == 2


@pytest.mark.asyncio
async def test_post_with_retry_does_not_retry_permanent_client_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_sleep(delay: float) -> None:
        del delay

    monkeypatch.setattr(integrations.asyncio, "sleep", no_sleep)
    client = StubAsyncClient([httpx.Response(400)])

    response = await integrations._post_with_retry(client, "https://example.test")  # type: ignore[arg-type]

    assert response.status_code == 400
    assert client.calls == 1


@pytest.mark.asyncio
async def test_post_with_retry_retries_network_failure_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_sleep(delay: float) -> None:
        del delay

    monkeypatch.setattr(integrations.asyncio, "sleep", no_sleep)
    request = httpx.Request("POST", "https://example.test")
    client = StubAsyncClient(
        [httpx.ConnectError("temporary failure", request=request), httpx.Response(200)]
    )

    response = await integrations._post_with_retry(client, "https://example.test")  # type: ignore[arg-type]

    assert response.status_code == 200
    assert client.calls == 2


@pytest.mark.asyncio
async def test_post_with_retry_raises_after_bounded_network_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_sleep(delay: float) -> None:
        del delay

    monkeypatch.setattr(integrations.asyncio, "sleep", no_sleep)
    request = httpx.Request("POST", "https://example.test")
    failures = [
        httpx.ConnectError("temporary failure", request=request)
        for _ in range(integrations._MAX_DISPATCH_ATTEMPTS)
    ]
    client = StubAsyncClient(failures)

    with pytest.raises(httpx.ConnectError):
        await integrations._post_with_retry(client, "https://example.test")  # type: ignore[arg-type]

    assert client.calls == integrations._MAX_DISPATCH_ATTEMPTS
