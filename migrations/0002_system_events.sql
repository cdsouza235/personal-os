CREATE TABLE IF NOT EXISTS system_events (
    event_id TEXT PRIMARY KEY,
    timestamp_utc TEXT NOT NULL,
    source TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);
