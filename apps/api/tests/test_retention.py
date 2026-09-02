from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from meeting_intelligence.config import get_settings
from meeting_intelligence.main import _store, app
from meeting_intelligence.storage import MeetingResultRecord

API_HEADERS = {"x-api-key": get_settings().api_key}


def _stored_at(meeting_id: str) -> datetime:
    with Session(_store._engine) as session:
        record = session.get(MeetingResultRecord, meeting_id)
        assert record is not None
        stored_at = record.stored_at
        if stored_at.tzinfo is None:
            stored_at = stored_at.replace(tzinfo=UTC)
        return stored_at


def _expire(meeting_id: str) -> None:
    with Session(_store._engine) as session:
        record = session.get(MeetingResultRecord, meeting_id)
        assert record is not None
        record.stored_at = datetime.now(UTC) - timedelta(
            seconds=get_settings().meeting_retention_seconds + 1
        )
        session.commit()


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

    _expire(meeting_id)

    read_response = client.get(f"/v1/meetings/{meeting_id}", headers=API_HEADERS)
    assert read_response.status_code == 404
    with Session(_store._engine) as session:
        assert session.get(MeetingResultRecord, meeting_id) is None

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
    first_stored_at = _stored_at(meeting_id)

    with Session(_store._engine) as session:
        record = session.get(MeetingResultRecord, meeting_id)
        assert record is not None
        record.stored_at = first_stored_at - timedelta(seconds=10)
        session.commit()

    second_response = client.post(
        "/v1/meetings/analyse", headers=API_HEADERS, json=payload
    )
    assert second_response.status_code == 200
    assert _stored_at(meeting_id) > first_stored_at - timedelta(seconds=10)
