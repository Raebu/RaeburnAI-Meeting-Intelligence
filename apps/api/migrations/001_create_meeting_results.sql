CREATE TABLE IF NOT EXISTS meeting_results (
    meeting_id VARCHAR(255) PRIMARY KEY,
    payload TEXT NOT NULL,
    stored_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_meeting_results_stored_at
    ON meeting_results (stored_at);
