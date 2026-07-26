from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from meeting_intelligence.main import app

AUTH_HEADERS = {"x-api-key": "test-api-key-not-a-production-secret"}


def meeting_payload(meeting_id: str) -> dict[str, object]:
    return {
        "meeting_id": meeting_id,
        "title": "Implementation meeting",
        "transcript": "We decided to use GitHub Issues. Sarah will create the GitHub issue by Friday.",
        "attendees": [{"name": "Sarah", "email": "sarah@example.com"}],
        "context": {"repository": "Raebu/example"},
    }


def test_health_and_database_readiness() -> None:
    with TestClient(app) as client:
        health = client.get("/healthz")
        readiness = client.get("/readyz")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert readiness.status_code == 200
    assert readiness.json()["status"] == "ready"
    assert health.headers["x-request-id"]


def test_protected_routes_require_api_key() -> None:
    with TestClient(app) as client:
        response = client.post("/v1/meetings/analyse", json=meeting_payload("unauthorised"))

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key"


@pytest.mark.integration
def test_analyse_and_retrieve_persisted_meeting() -> None:
    meeting_id = "test-meeting-persisted"
    with TestClient(app) as client:
        response = client.post(
            "/v1/meetings/analyse",
            json=meeting_payload(meeting_id),
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["meeting_id"] == meeting_id
        assert len(payload["decisions"]) == 1
        assert len(payload["action_items"]) == 1
        assert payload["integration_commands"]

        get_response = client.get(f"/v1/meetings/{meeting_id}", headers=AUTH_HEADERS)

    assert get_response.status_code == 200
    assert get_response.json() == payload


@pytest.mark.e2e
def test_approval_workflow_is_persisted_and_audited() -> None:
    meeting_id = "test-meeting-approval"
    with TestClient(app) as client:
        analysed = client.post(
            "/v1/meetings/analyse",
            json=meeting_payload(meeting_id),
            headers=AUTH_HEADERS,
        )
        command_id = analysed.json()["integration_commands"][0]["id"]

        approved = client.post(
            f"/v1/approvals/{meeting_id}/approve",
            headers=AUTH_HEADERS,
            json={
                "command_ids": [command_id],
                "approved_by": "security-reviewer@example.com",
                "reason": "Reviewed against the meeting transcript",
            },
        )
        persisted = client.get(f"/v1/meetings/{meeting_id}", headers=AUTH_HEADERS)

    assert approved.status_code == 200
    assert approved.json()["integration_commands"][0]["approval_status"] == "approved"
    assert approved.json()["audit_events"][-1].startswith("commands.approved_by:")
    assert persisted.json() == approved.json()


@pytest.mark.integration
def test_unknown_approval_command_is_rejected_without_partial_update() -> None:
    meeting_id = "test-meeting-invalid-command"
    with TestClient(app) as client:
        analysed = client.post(
            "/v1/meetings/analyse",
            json=meeting_payload(meeting_id),
            headers=AUTH_HEADERS,
        )
        original = analysed.json()

        response = client.post(
            f"/v1/approvals/{meeting_id}/approve",
            headers=AUTH_HEADERS,
            json={"command_ids": [str(uuid4())], "approved_by": "reviewer@example.com"},
        )
        persisted = client.get(f"/v1/meetings/{meeting_id}", headers=AUTH_HEADERS)

    assert response.status_code == 400
    assert response.json()["detail"].startswith("Unknown command IDs:")
    assert persisted.json() == original


def test_request_validation_rejects_unknown_fields() -> None:
    payload = meeting_payload("test-validation")
    payload["unexpected"] = "not allowed"

    with TestClient(app) as client:
        response = client.post(
            "/v1/meetings/analyse",
            json=payload,
            headers=AUTH_HEADERS,
        )

    assert response.status_code == 422
