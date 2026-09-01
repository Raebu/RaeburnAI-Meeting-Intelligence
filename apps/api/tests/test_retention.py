import time

from fastapi.testclient import TestClient

from meeting_intelligence.config import get_settings
from meeting_intelligence.main import _result_stored_at, _results, app

API_HEADERS = {"x-api-key": get_settings().api_key}


def test_expired_meeting_is_purged_before_read_export_and_approval() -> None:
    client = TestClient(app)
    meeting_id = "retention-expired-meeting"
    create_response = client.post(
        "/v1/meetings/analyse",
        headers=API_HEADERS,
        json={
            "meeting_id": meeting_id,
            "title": "Retention enforcement test",
            "transcript": (
                "We decided to use GitHub Issues. Sarah will create the GitHub "
                "issue by Friday."
            ),
            "attendees": [{"name": "Sarah", "email": "sarah@example.com"}],
            "context": {"repository": "Raebu/example"},
        },
    )
    assert create_response.status_code == 200
    command_id = create_response.json()["integration_commands"][0]["id"]

    _result_stored_at[meeting_id] = (
        time.time() - get_settings().meeting_retention_seconds - 1
    )

    read_response = client.get(f"/v1/meetings/{meeting_id}", headers=API_HEADERS)
    assert read_response.status_code == 404
    assert meeting_id not in _results
    assert meeting_id not in _result_stored_at

    export_response = client.get(
        f"/v1/meetings/{meeting_id}/export", headers=API_HEADERS
    )
    assert export_response.status_code == 404

    approval_response = client.post(
        f"/v1/approvals/{meeting_id}/approve",
        headers=API_HEADERS,
        json={"command_ids": [command_id], "approved_by": "retention-test"},
    )
    assert approval_response.status_code == 404


def test_reanalysis_refreshes_retention_timestamp() -> None:
    client = TestClient(app)
    meeting_id = "retention-refresh-meeting"
    payload = {
        "meeting_id": meeting_id,
        "title": "Retention refresh test",
        "transcript": "We decided to refresh the retained meeting record.",
        "attendees": [],
        "context": {},
    }

    first_response = client.post(
        "/v1/meetings/analyse", headers=API_HEADERS, json=payload
    )
    assert first_response.status_code == 200
    first_stored_at = _result_stored_at[meeting_id]

    _result_stored_at[meeting_id] = first_stored_at - 10
    second_response = client.post(
        "/v1/meetings/analyse", headers=API_HEADERS, json=payload
    )
    assert second_response.status_code == 200
    assert _result_stored_at[meeting_id] > first_stored_at - 10
