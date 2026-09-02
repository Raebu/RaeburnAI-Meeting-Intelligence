CREATE TABLE IF NOT EXISTS webhook_receipts (
    workspace_id VARCHAR(255) NOT NULL,
    event_id VARCHAR(255) NOT NULL,
    body_digest VARCHAR(64) NOT NULL,
    received_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (workspace_id, event_id)
);

CREATE INDEX IF NOT EXISTS ix_webhook_receipts_received_at
    ON webhook_receipts (received_at);
