from fastapi.testclient import TestClient

from meeting_intelligence.config import get_settings
from meeting_intelligence.main import app

API_HEADERS = {"x-api-key": get_settings().api_key}


def test_analysis_materializes_native_work_and_tracks_outcome() -> None:
    client = TestClient(app)
    meeting_id = "native-api-meeting"
    payload = {
        "meeting_id": meeting_id,
        "title": "Native operating layer",
        "transcript": (
            "We decided to make RaeburnAI the source of truth. "
            "Martin will ship native action tracking by Friday."
        ),
        "attendees": [{"name": "Martin", "email": "martin@example.test"}],
        "context": {},
    }

    analysed = client.post("/v1/meetings/analyse", headers=API_HEADERS, json=payload)
    assert analysed.status_code == 200

    decisions = client.get(
        "/v1/native/decisions",
        headers=API_HEADERS,
        params={"meeting_id": meeting_id},
    )
    actions = client.get(
        "/v1/native/actions",
        headers=API_HEADERS,
        params={"meeting_id": meeting_id},
    )
    assert decisions.status_code == 200
    assert actions.status_code == 200
    assert len(decisions.json()) == 1
    assert len(actions.json()) == 1

    action_id = actions.json()[0]["id"]
    completed = client.patch(
        f"/v1/native/actions/{action_id}",
        headers=API_HEADERS,
        json={"status": "done", "outcome": "Released to production"},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "done"
    assert completed.json()["outcome"] == "Released to production"

    reanalysed = client.post("/v1/meetings/analyse", headers=API_HEADERS, json=payload)
    assert reanalysed.status_code == 200
    reloaded = client.get(
        "/v1/native/actions",
        headers=API_HEADERS,
        params={"meeting_id": meeting_id},
    )
    assert len(reloaded.json()) == 1
    assert reloaded.json()[0]["status"] == "done"
    assert reloaded.json()[0]["outcome"] == "Released to production"


def test_meeting_deletion_removes_native_work() -> None:
    client = TestClient(app)
    meeting_id = "native-api-delete"
    created = client.post(
        "/v1/meetings/analyse",
        headers=API_HEADERS,
        json={
            "meeting_id": meeting_id,
            "title": "Deletion",
            "transcript": (
                "We decided to delete derived work. Martin will remove the record."
            ),
            "attendees": [{"name": "Martin"}],
            "context": {},
        },
    )
    assert created.status_code == 200

    deleted = client.delete(f"/v1/meetings/{meeting_id}", headers=API_HEADERS)
    assert deleted.status_code == 204

    decisions = client.get(
        "/v1/native/decisions",
        headers=API_HEADERS,
        params={"meeting_id": meeting_id},
    )
    actions = client.get(
        "/v1/native/actions",
        headers=API_HEADERS,
        params={"meeting_id": meeting_id},
    )
    assert decisions.json() == []
    assert actions.json() == []
