from fastapi.testclient import TestClient

from meeting_intelligence.main import app


def test_health_and_readiness() -> None:
    client = TestClient(app)
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200


def test_analyse_meeting_end_to_end() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/meetings/analyse",
        json={
            "meeting_id": "test-meeting-1",
            "title": "Implementation meeting",
            "transcript": "We decided to use GitHub Issues. Sarah will create the GitHub issue by Friday.",
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

    get_response = client.get("/v1/meetings/test-meeting-1")
    assert get_response.status_code == 200
    assert get_response.json()["meeting_id"] == "test-meeting-1"
