CREATE TABLE IF NOT EXISTS native_decisions (
    id VARCHAR(36) PRIMARY KEY,
    workspace_id VARCHAR(255) NOT NULL,
    meeting_id VARCHAR(255) NOT NULL,
    statement TEXT NOT NULL,
    rationale TEXT NULL,
    owner VARCHAR(255) NULL,
    confidence DOUBLE PRECISION NOT NULL,
    evidence TEXT NULL,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_native_decisions_workspace_id
    ON native_decisions (workspace_id);
CREATE INDEX IF NOT EXISTS ix_native_decisions_meeting_id
    ON native_decisions (meeting_id);
CREATE INDEX IF NOT EXISTS ix_native_decisions_status
    ON native_decisions (status);

CREATE TABLE IF NOT EXISTS native_actions (
    id VARCHAR(36) PRIMARY KEY,
    workspace_id VARCHAR(255) NOT NULL,
    meeting_id VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    owner VARCHAR(255) NULL,
    owner_email VARCHAR(320) NULL,
    due_date TIMESTAMPTZ NULL,
    priority VARCHAR(32) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    evidence TEXT NULL,
    status VARCHAR(32) NOT NULL,
    outcome TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_native_actions_workspace_id
    ON native_actions (workspace_id);
CREATE INDEX IF NOT EXISTS ix_native_actions_meeting_id
    ON native_actions (meeting_id);
CREATE INDEX IF NOT EXISTS ix_native_actions_status
    ON native_actions (status);
