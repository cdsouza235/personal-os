CREATE TABLE IF NOT EXISTS routines (
    routine_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    enabled INTEGER NOT NULL,
    settings_json TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    CHECK (enabled IN (0, 1))
);

CREATE TABLE IF NOT EXISTS routine_completions (
    completion_id TEXT PRIMARY KEY,
    routine_id TEXT NOT NULL,
    completed_for_date TEXT NOT NULL,
    completed_at_utc TEXT NOT NULL,
    source TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    FOREIGN KEY (routine_id) REFERENCES routines (routine_id)
);

CREATE TABLE IF NOT EXISTS priorities (
    priority_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS followups (
    followup_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS permission_settings (
    category TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    updated_by TEXT NOT NULL
);
