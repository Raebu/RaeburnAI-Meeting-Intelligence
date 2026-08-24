CREATE TABLE IF NOT EXISTS meeting_results (
    meeting_id VARCHAR(255) PRIMARY KEY,
    payload TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_meeting_results_updated_at
    ON meeting_results (updated_at DESC);
