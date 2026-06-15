CREATE TABLE IF NOT EXISTS composer_packets (
    id TEXT PRIMARY KEY,
    packet_type TEXT NOT NULL,
    briefing_window TEXT,
    source_date TEXT NOT NULL,
    timezone TEXT NOT NULL,
    packet_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (packet_type IN ('daily_brief', 'window_brief', 'ad_hoc_preview')),
    CHECK (
        briefing_window IS NULL
        OR briefing_window IN ('morning', 'midday', 'afternoon', 'evening', 'none')
    ),
    CHECK (status IN ('draft', 'validated', 'sent_to_fake_model', 'completed', 'failed', 'rejected'))
);

CREATE TABLE IF NOT EXISTS composer_outputs (
    id TEXT PRIMARY KEY,
    packet_id TEXT NOT NULL REFERENCES composer_packets(id),
    output_json TEXT NOT NULL,
    readable_text TEXT NOT NULL,
    validation_status TEXT NOT NULL,
    route_report_json TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (validation_status IN ('received', 'validated', 'rejected', 'failed')),
    CHECK (status IN ('received', 'validated', 'routed', 'rejected', 'failed'))
);

CREATE TABLE IF NOT EXISTS model_runs (
    id TEXT PRIMARY KEY,
    packet_id TEXT NOT NULL REFERENCES composer_packets(id),
    output_id TEXT REFERENCES composer_outputs(id),
    model_role TEXT NOT NULL,
    model_name TEXT NOT NULL,
    adapter_name TEXT NOT NULL,
    dry_run INTEGER NOT NULL,
    status TEXT NOT NULL,
    input_token_count INTEGER,
    output_token_count INTEGER,
    error_message TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    CHECK (model_role IN ('composer_model')),
    CHECK (adapter_name IN ('fake_composer_adapter')),
    CHECK (dry_run IN (0, 1)),
    CHECK (status IN ('dry_run', 'completed', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_composer_packets_status
ON composer_packets (status);

CREATE INDEX IF NOT EXISTS idx_composer_packets_source_date
ON composer_packets (source_date, briefing_window);

CREATE INDEX IF NOT EXISTS idx_composer_outputs_packet
ON composer_outputs (packet_id);

CREATE INDEX IF NOT EXISTS idx_model_runs_packet
ON model_runs (packet_id);
