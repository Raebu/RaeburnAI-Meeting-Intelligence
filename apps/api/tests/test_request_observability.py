from __future__ import annotations

import re

from fastapi.testclient import TestClient

from meeting_intelligence import main


def test_health_response_has_server_generated_request_id() -> None:
    client = TestClient(main.app)

    response = client.get("/healthz", headers={"x-request-id": "attacker-controlled"})

    assert response.status_code == 200
    request_id = response.headers["x-request-id"]
    assert request_id != "attacker-controlled"
    assert re.fullmatch(r"[0-9a-f]{32}", request_id)


def test_request_id_helper_falls_back_for_uninstrumented_request() -> None:
    class State:
        pass

    class RequestLike:
        state = State()

    assert main._request_id(RequestLike()) == "unavailable"  # type: ignore[arg-type]
