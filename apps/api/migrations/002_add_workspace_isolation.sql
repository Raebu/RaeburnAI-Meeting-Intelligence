-- Add workspace isolation to persisted meeting records.
-- Existing single-tenant data is assigned to the bootstrap/default workspace.
ALTER TABLE meeting_results
    ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(255) NOT NULL DEFAULT 'default';

CREATE INDEX IF NOT EXISTS ix_meeting_results_workspace_id
    ON meeting_results (workspace_id);
