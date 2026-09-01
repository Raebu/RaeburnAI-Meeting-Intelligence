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


def test_export_meeting_requires_auth_and_returns_attachment() -> None:
    client = TestClient(app)
    meeting_id = "test-meeting-export"
    create_response = client.post(
        "/v1/meetings/analyse",
        headers=API_HEADERS,
        json={
            "meeting_id": meeting_id,
            "title": "Retention export test",
            "transcript": "We decided to export the meeting record for review.",
            "attendees": [],
            "context": {},
        },
    )
    assert create_response.status_code == 200

    unauthorized = client.get(f"/v1/meetings/{meeting_id}/export")
    assert unauthorized.status_code == 401

    export_response = client.get(
        f"/v1/meetings/{meeting_id}/export", headers=API_HEADERS
    )
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("application/json")
    assert export_response.headers["cache-control"] == "private, no-store"
    assert export_response.headers["vary"] == "X-API-Key"
    disposition = export_response.headers["content-disposition"]
    assert 'filename="meeting-export.json"' in disposition
    assert "filename*=UTF-8''meeting-test-meeting-export.json" in disposition
    assert export_response.json()["meeting_id"] == meeting_id

    schema = client.get("/openapi.json").json()
    export_schema = schema["paths"]["/v1/meetings/{meeting_id}/export"]["get"]
    response_schema = export_schema["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    assert response_schema["$ref"].endswith("/MeetingIntelligenceResult")

    missing = client.get("/v1/meetings/missing/export", headers=API_HEADERS)
    assert missing.status_code == 404


def test_export_meeting_supports_unicode_identifier() -> None:
    client = TestClient(app)
    meeting_id = "会议"
    create_response = client.post(
        "/v1/meetings/analyse",
        headers=API_HEADERS,
        json={
            "meeting_id": meeting_id,
            "title": "Unicode export test",
            "transcript": "We decided to verify unicode-safe meeting exports.",
            "attendees": [],
            "context": {},
        },
    )
    assert create_response.status_code == 200

    export_response = client.get(
        f"/v1/meetings/{meeting_id}/export", headers=API_HEADERS
    )
    assert export_response.status_code == 200
    disposition = export_response.headers["content-disposition"]
    assert 'filename="meeting-export.json"' in disposition
    assert "filename*=UTF-8''meeting-%E4%BC%9A%E8%AE%AE.json" in disposition
    assert export_response.json()["meeting_id"] == meeting_id


def test_delete_meeting_requires_auth_and_removes_result() -> None:
    client = TestClient(app)
    meeting_id = "test-meeting-delete"
    create_response = client.post(
        "/v1/meetings/analyse",
        headers=API_HEADERS,
        json={
            "meeting_id": meeting_id,
            "title": "Retention deletion test",
            "transcript": "We decided to archive the transcript after review.",
            "attendees": [],
            "context": {},
        },
    )
    assert create_response.status_code == 200

    unauthorized = client.delete(f"/v1/meetings/{meeting_id}")
    assert unauthorized.status_code == 401

    delete_response = client.delete(f"/v1/meetings/{meeting_id}", headers=API_HEADERS)
    assert delete_response.status_code == 204
    assert delete_response.content == b""

    missing_response = client.get(f"/v1/meetings/{meeting_id}", headers=API_HEADERS)
    assert missing_response.status_code == 404

    repeat_delete = client.delete(f"/v1/meetings/{meeting_id}", headers=API_HEADERS)
    assert repeat_delete.status_code == 404


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
