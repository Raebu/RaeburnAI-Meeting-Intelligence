from fastapi import Response
from fastapi.testclient import TestClient

from meeting_intelligence.config import Settings, get_settings
from meeting_intelligence.main import app
from meeting_intelligence.security import apply_security_headers


def test_api_responses_include_browser_security_headers() -> None:
    client = TestClient(app, client=("security-headers-test", 50000))
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["permissions-policy"] == (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    )
    assert "strict-transport-security" not in response.headers


def test_production_security_headers_enable_hsts() -> None:
    production = Settings(
        RAEBURN_ENV="production",
        RAEBURN_API_KEY="a" * 32,
        RAEBURN_PUBLIC_BASE_URL="https://meeting.example.com",
    )

    response = apply_security_headers(Response(), production)

    assert response.headers["strict-transport-security"] == (
        "max-age=31536000; includeSubDomains"
    )


def test_security_headers_do_not_override_stricter_response_policy() -> None:
    response = Response(headers={"Referrer-Policy": "same-origin"})

    secured = apply_security_headers(response, get_settings())

    assert secured.headers["referrer-policy"] == "same-origin"
