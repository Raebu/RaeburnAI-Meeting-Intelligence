from fastapi.testclient import TestClient

from meeting_intelligence.config import get_settings
from meeting_intelligence.main import app

API_HEADERS = {"x-api-key": get_settings().api_key}


def test_approval_queue_lists_only_pending_workspace_meetings() -> None:
    client = TestClient(app)
    meeting_id = "approval-queue-list-test"
    created = client.post(
        "/v1/meetings/analyse",
        headers=API_HEADERS,
        json={
            "meeting_id": meeting_id,
            "title": "Native approval centre",
            "transcript": (
                "We decided to create a GitHub issue. Sarah will create the GitHub "
                "issue by Friday."
            ),
            "attendees": [{"name": "Sarah", "email": "sarah@example.com"}],
            "context": {"repository": "Raebu/example"},
        },
    )
    assert created.status_code == 200
    commands = created.json()["integration_commands"]
    assert commands

    unauthorized = client.get("/v1/approvals")
    assert unauthorized.status_code == 401

    queue = client.get("/v1/approvals", headers=API_HEADERS)
    assert queue.status_code == 200
    queued_meeting = next(
        item for item in queue.json() if item["meeting_id"] == meeting_id
    )
    assert any(
        command["approval_status"] == "pending"
        for command in queued_meeting["integration_commands"]
    )

    command_ids = [command["id"] for command in commands]
    approved = client.post(
        f"/v1/approvals/{meeting_id}/approve",
        headers=API_HEADERS,
        json={"command_ids": command_ids, "approved_by": "ignored@example.com"},
    )
    assert approved.status_code == 200

    after = client.get("/v1/approvals", headers=API_HEADERS)
    assert after.status_code == 200
    assert all(item["meeting_id"] != meeting_id for item in after.json())
