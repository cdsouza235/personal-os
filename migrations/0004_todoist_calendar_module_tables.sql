CREATE TABLE IF NOT EXISTS todoist_tasks (
    todoist_task_id TEXT PRIMARY KEY,
    task_title TEXT NOT NULL,
    description TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    project TEXT NOT NULL,
    labels_json TEXT NOT NULL,
    due_date_or_due_string TEXT NOT NULL,
    priority INTEGER NOT NULL,
    risk_level TEXT NOT NULL,
    approval_mode TEXT NOT NULL,
    dedupe_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    external_task_id TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    CHECK (priority BETWEEN 1 AND 4),
    CHECK (risk_level IN ('low', 'medium', 'high')),
    CHECK (approval_mode IN ('auto_allowed', 'approval_required', 'manual_only')),
    CHECK (
        status IN (
            'proposed',
            'needs_approval',
            'approved_for_dev_test',
            'simulated_created',
            'cancelled',
            'failed'
        )
    )
);

CREATE TABLE IF NOT EXISTS calendar_blocks (
    calendar_block_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    calendar_id TEXT NOT NULL,
    timezone TEXT NOT NULL,
    approval_mode TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    dedupe_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    external_event_id TEXT,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    CHECK (duration_minutes > 0),
    CHECK (risk_level IN ('low', 'medium', 'high')),
    CHECK (approval_mode IN ('auto_allowed', 'approval_required', 'manual_only')),
    CHECK (
        status IN (
            'proposed',
            'needs_approval',
            'approved_for_dev_test',
            'simulated_created',
            'cancelled',
            'failed'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_todoist_tasks_status
ON todoist_tasks (status);

CREATE INDEX IF NOT EXISTS idx_todoist_tasks_source
ON todoist_tasks (source_type, source_id);

CREATE INDEX IF NOT EXISTS idx_calendar_blocks_status
ON calendar_blocks (status);

CREATE INDEX IF NOT EXISTS idx_calendar_blocks_window
ON calendar_blocks (start_time, end_time);
