from fastapi.testclient import TestClient

from meeting_intelligence.config import get_settings
from meeting_intelligence.main import app

API_HEADERS = {"x-api-key": get_settings().api_key}


def test_health_and_readiness() -> None:
    client = TestClient(app)
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200


def test_analyse_meeting_end_to_end() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/meetings/analyse",
        headers=API_HEADERS,
        json={
            "meeting_id": "test-meeting-1",
            "title": "Implementation meeting",
            "transcript": (
                "We decided to use GitHub Issues. Sarah will create the GitHub "
                "issue by Friday."
            ),
            "attendees": [{"name": "Sarah", "email": "sarah@example.com"}],
            "context": {"repository": "Raebu/example"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meeting_id"] == "test-meeting-1"
    assert len(payload["decisions"]) == 1
    assert len(payload["action_items"]) == 1
    assert payload["integration_commands"]

    get_response = client.get("/v1/meetings/test-meeting-1", headers=API_HEADERS)
    assert get_response.status_code == 200
    assert get_response.json()["meeting_id"] == "test-meeting-1"


def test_request_cannot_bypass_server_approval_policy() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/meetings/analyse",
        headers=API_HEADERS,
        json={
            "meeting_id": "test-approval-policy",
            "title": "Approval policy test",
            "transcript": (
                "We decided to create a GitHub issue. Sarah will create the GitHub "
                "issue by Friday."
            ),
            "attendees": [{"name": "Sarah", "email": "sarah@example.com"}],
            "context": {"repository": "Raebu/example"},
            "require_approval": False,
        },
    )

    assert response.status_code == 200
    commands = response.json()["integration_commands"]
    assert commands
    assert all(command["approval_status"] == "pending" for command in commands)
