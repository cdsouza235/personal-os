CREATE TABLE IF NOT EXISTS runtime_bootstrap_runs (
    id TEXT PRIMARY KEY,
    profile_name TEXT NOT NULL,
    runtime_mode TEXT NOT NULL,
    db_path_label TEXT NOT NULL,
    dry_run INTEGER NOT NULL,
    status TEXT NOT NULL,
    input_json TEXT NOT NULL,
    output_json TEXT NOT NULL,
    error_message TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    CHECK (runtime_mode IN ('dev_runtime', 'local_runtime_preview')),
    CHECK (dry_run IN (0, 1)),
    CHECK (status IN ('planned', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS briefing_windows (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    scheduled_time TEXT NOT NULL,
    timezone TEXT NOT NULL,
    delivery_mode TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (name IN ('morning', 'midday', 'afternoon', 'evening')),
    CHECK (delivery_mode IN ('no_send', 'manual_export')),
    CHECK (status IN ('draft', 'active', 'disabled'))
);

CREATE INDEX IF NOT EXISTS idx_runtime_bootstrap_runs_profile_created
ON runtime_bootstrap_runs (profile_name, created_at);

CREATE INDEX IF NOT EXISTS idx_runtime_bootstrap_runs_status
ON runtime_bootstrap_runs (status);

CREATE INDEX IF NOT EXISTS idx_briefing_windows_status
ON briefing_windows (status, scheduled_time);
