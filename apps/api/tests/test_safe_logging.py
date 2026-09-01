from __future__ import annotations

import asyncio
import hashlib
from typing import Any

from starlette.requests import Request

from meeting_intelligence import main


def _request(path: str, route_template: str | None = None) -> Request:
    scope: dict[str, Any] = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "https",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 443),
    }
    if route_template is not None:
        scope["route"] = type("Route", (), {"path": route_template})()
    return Request(scope)


def test_safe_ref_is_stable_and_does_not_expose_source_value() -> None:
    value = "customer-meeting-会议-123"

    reference = main._safe_ref(value)

    assert reference == hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    assert value not in reference
    assert len(reference) == 12


def test_safe_route_path_uses_route_template_not_user_path() -> None:
    request = _request(
        "/v1/meetings/customer-secret-123/export",
        "/v1/meetings/{meeting_id}/export",
    )

    route = main._safe_route_path(request)

    assert route == "/v1/meetings/{meeting_id}/export"
    assert "customer-secret-123" not in route


def test_safe_route_path_falls_back_without_resolved_route() -> None:
    assert main._safe_route_path(_request("/private-value")) == "unresolved"


def test_unhandled_exception_log_omits_exception_message(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    class CapturingLogger:
        def error(self, event: str, **kwargs: Any) -> None:
            captured["event"] = event
            captured.update(kwargs)

    monkeypatch.setattr(main, "logger", CapturingLogger())
    request = _request(
        "/v1/meetings/customer-secret-123",
        "/v1/meetings/{meeting_id}",
    )

    response = asyncio.run(
        main.unhandled_exception_handler(request, ValueError("TRANSCRIPT_SECRET"))
    )

    assert response.status_code == 500
    assert captured == {
        "event": "unhandled_exception",
        "route": "/v1/meetings/{meeting_id}",
        "error_type": "ValueError",
    }
    assert "TRANSCRIPT_SECRET" not in repr(captured)
