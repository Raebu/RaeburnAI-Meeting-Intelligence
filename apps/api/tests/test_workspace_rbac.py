import json
from uuid import uuid4

from fastapi.testclient import TestClient

from meeting_intelligence.config import Settings, get_settings
from meeting_intelligence.main import app


def _settings_with_workspace_key(role: str, workspace_id: str, subject: str) -> tuple[Settings, str]:
    workspace_key = f"wk-{uuid4().hex}{uuid4().hex}"
    settings = Settings(
        RAEBURN_ENV="test",
        RAEBURN_API_KEY=f"bootstrap-{uuid4().hex}{uuid4().hex}",
        DATABASE_URL="sqlite+pysqlite:///:memory:",
        RAEBURN_WORKSPACE_API_KEYS=json.dumps(
            {
                workspace_key: {
                    "workspace_id": workspace_id,
                    "role": role,
                    "subject": subject,
                }
            }
        ),
    )
    return settings, workspace_key


def test_workspace_key_resolves_principal_and_enforces_role() -> None:
    settings, workspace_key = _settings_with_workspace_key(
        "viewer", "workspace-a", "viewer@example.test"
    )
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        client = TestClient(app)
        whoami = client.get("/v1/auth/me", headers={"x-api-key": workspace_key})
        assert whoami.status_code == 200
        assert whoami.json() == {
            "workspace_id": "workspace-a",
            "role": "viewer",
            "subject": "viewer@example.test",
        }

        analyse = client.post(
            "/v1/meetings/analyse",
            headers={"x-api-key": workspace_key},
            json={
                "meeting_id": "viewer-cannot-create",
                "title": "RBAC",
                "transcript": "We decided to verify role enforcement.",
            },
        )
        assert analyse.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_meeting_reads_are_isolated_by_workspace() -> None:
    secondary_settings, workspace_key = _settings_with_workspace_key(
        "operator", "workspace-b", "operator@example.test"
    )
    bootstrap_headers = {"x-api-key": get_settings().api_key}
    client = TestClient(app)
    create = client.post(
        "/v1/meetings/analyse",
        headers=bootstrap_headers,
        json={
            "meeting_id": "workspace-isolation-default",
            "title": "Isolation",
            "transcript": "We decided to isolate tenant meeting data.",
        },
    )
    assert create.status_code == 200

    app.dependency_overrides[get_settings] = lambda: secondary_settings
    try:
        isolated_client = TestClient(app)
        hidden = isolated_client.get(
            "/v1/meetings/workspace-isolation-default",
            headers={"x-api-key": workspace_key},
        )
        assert hidden.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_approval_actor_is_authenticated_principal_not_request_claim() -> None:
    settings, workspace_key = _settings_with_workspace_key(
        "approver", "workspace-c", "trusted-approver@example.test"
    )
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        client = TestClient(app)
        # Bootstrap admin creates the record in the configured bootstrap workspace,
        # so create a workspace-c record using an operator-capable key instead.
        operator_key = f"wk-{uuid4().hex}{uuid4().hex}"
        settings.workspace_api_keys_json = json.dumps(
            {
                workspace_key: {
                    "workspace_id": "workspace-c",
                    "role": "approver",
                    "subject": "trusted-approver@example.test",
                },
                operator_key: {
                    "workspace_id": "workspace-c",
                    "role": "operator",
                    "subject": "operator@example.test",
                },
            }
        )
        create = client.post(
            "/v1/meetings/analyse",
            headers={"x-api-key": operator_key},
            json={
                "meeting_id": "workspace-approval-actor",
                "title": "Approval actor",
                "transcript": (
                    "We decided to create a GitHub issue. Sarah will create the GitHub "
                    "issue by Friday."
                ),
                "context": {"repository": "Raebu/example"},
            },
        )
        assert create.status_code == 200
        command_id = create.json()["integration_commands"][0]["id"]

        approve = client.post(
            "/v1/approvals/workspace-approval-actor/approve",
            headers={"x-api-key": workspace_key},
            json={
                "command_ids": [command_id],
                "approved_by": "spoofed@example.test",
            },
        )
        assert approve.status_code == 200
        audit_events = approve.json()["audit_events"]
        assert "commands.approved_by:trusted-approver@example.test" in audit_events
        assert all("spoofed@example.test" not in event for event in audit_events)
    finally:
        app.dependency_overrides.clear()
