from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient

from meeting_intelligence.config import get_settings
from meeting_intelligence.main import app

API_HEADERS = {"x-api-key": get_settings().api_key}


def test_concurrent_approval_decisions_are_terminal() -> None:
    meeting_id = "test-concurrent-approval-terminal-state"
    with TestClient(app) as client:
        create = client.post(
            "/v1/meetings/analyse",
            headers=API_HEADERS,
            json={
                "meeting_id": meeting_id,
                "title": "Concurrent approval integrity test",
                "transcript": (
                    "We decided to create a GitHub issue. Sarah will create the GitHub "
                    "issue by Friday."
                ),
                "attendees": [{"name": "Sarah", "email": "sarah@example.com"}],
                "context": {"repository": "Raebu/example"},
            },
        )
        assert create.status_code == 200
        command_id = create.json()["integration_commands"][0]["id"]

    barrier = Barrier(2)

    def decide(action: str, actor: str) -> tuple[int, str | None]:
        barrier.wait()
        with TestClient(app) as client:
            response = client.post(
                f"/v1/approvals/{meeting_id}/{action}",
                headers=API_HEADERS,
                json={"command_ids": [command_id], "approved_by": actor},
            )
            status_value = None
            if response.status_code == 200:
                command = response.json()["integration_commands"][0]
                status_value = command["approval_status"]
            return response.status_code, status_value

    with ThreadPoolExecutor(max_workers=2) as executor:
        approve_future = executor.submit(decide, "approve", "approver@example.com")
        reject_future = executor.submit(decide, "reject", "rejector@example.com")
        outcomes = [approve_future.result(), reject_future.result()]

    assert sorted(status_code for status_code, _ in outcomes) == [200, 409]
    successful_status = next(value for code, value in outcomes if code == 200)
    assert successful_status in {"approved", "rejected"}

    with TestClient(app) as client:
        stored = client.get(f"/v1/meetings/{meeting_id}", headers=API_HEADERS)
    assert stored.status_code == 200
    stored_command = stored.json()["integration_commands"][0]
    assert stored_command["approval_status"] == successful_status
