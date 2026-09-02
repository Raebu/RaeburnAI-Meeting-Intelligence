CREATE TABLE IF NOT EXISTS dispatch_jobs (
    id VARCHAR(36) PRIMARY KEY,
    workspace_id VARCHAR(255) NOT NULL,
    meeting_id VARCHAR(255) NOT NULL,
    command_json TEXT NOT NULL,
    status VARCHAR(32) NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    last_error TEXT NULL,
    result_json TEXT NULL
);

CREATE INDEX IF NOT EXISTS ix_dispatch_jobs_workspace_id
    ON dispatch_jobs (workspace_id);
CREATE INDEX IF NOT EXISTS ix_dispatch_jobs_meeting_id
    ON dispatch_jobs (meeting_id);
CREATE INDEX IF NOT EXISTS ix_dispatch_jobs_status
    ON dispatch_jobs (status);
CREATE INDEX IF NOT EXISTS ix_dispatch_jobs_due
    ON dispatch_jobs (status, next_attempt_at, created_at);
