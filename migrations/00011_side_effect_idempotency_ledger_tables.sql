CREATE TABLE IF NOT EXISTS external_write_intents (
    intent_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_system TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    approval_mode TEXT NOT NULL,
    status TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    dedupe_key TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    validation_report_json TEXT NOT NULL,
    no_external_writes INTEGER NOT NULL DEFAULT 1,
    no_send_mode INTEGER NOT NULL DEFAULT 1,
    live_write INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        target_system IN (
            'todoist',
            'calendar',
            'gmail',
            'personalos_markdown',
            'other'
        )
    ),
    CHECK (
        operation_type IN (
            'create',
            'update',
            'delete',
            'send',
            'export',
            'write_file'
        )
    ),
    CHECK (risk_level IN ('low', 'medium', 'high')),
    CHECK (approval_mode IN ('auto_allowed', 'approval_required', 'manual_only')),
    CHECK (
        status IN (
            'pending_review',
            'approved_for_dry_run',
            'dry_run_recorded',
            'blocked',
            'skipped_duplicate',
            'failed',
            'completed_simulated'
        )
    ),
    CHECK (no_external_writes = 1),
    CHECK (no_send_mode = 1),
    CHECK (live_write = 0),
    UNIQUE (target_system, operation_type, dedupe_key)
);

CREATE TABLE IF NOT EXISTS external_write_attempts (
    attempt_id TEXT PRIMARY KEY,
    intent_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    mode TEXT NOT NULL,
    adapter_name TEXT NOT NULL,
    status TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    response_summary_json TEXT NOT NULL,
    error_message TEXT,
    no_external_writes INTEGER NOT NULL DEFAULT 1,
    no_send_mode INTEGER NOT NULL DEFAULT 1,
    live_write INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (intent_id)
        REFERENCES external_write_intents (intent_id)
        ON DELETE RESTRICT,
    CHECK (attempt_number > 0),
    CHECK (mode IN ('dry_run', 'simulated', 'live_blocked')),
    CHECK (status IN ('succeeded', 'failed', 'blocked', 'skipped_duplicate')),
    CHECK (mode != 'live_blocked' OR status = 'blocked'),
    CHECK (no_external_writes = 1),
    CHECK (no_send_mode = 1),
    CHECK (live_write = 0),
    UNIQUE (intent_id, attempt_number)
);

CREATE TABLE IF NOT EXISTS idempotency_records (
    idempotency_key TEXT PRIMARY KEY,
    target_system TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    dedupe_key TEXT NOT NULL,
    payload_fingerprint TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    status TEXT NOT NULL,
    linked_intent_id TEXT,
    linked_attempt_id TEXT,
    FOREIGN KEY (linked_intent_id)
        REFERENCES external_write_intents (intent_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (linked_attempt_id)
        REFERENCES external_write_attempts (attempt_id)
        ON DELETE RESTRICT,
    CHECK (
        target_system IN (
            'todoist',
            'calendar',
            'gmail',
            'personalos_markdown',
            'other'
        )
    ),
    CHECK (
        operation_type IN (
            'create',
            'update',
            'delete',
            'send',
            'export',
            'write_file'
        )
    ),
    CHECK (
        status IN (
            'pending_review',
            'approved_for_dry_run',
            'dry_run_recorded',
            'blocked',
            'skipped_duplicate',
            'failed',
            'completed_simulated'
        )
    ),
    UNIQUE (target_system, operation_type, dedupe_key)
);

CREATE INDEX IF NOT EXISTS idx_external_write_intents_status
ON external_write_intents (status);

CREATE INDEX IF NOT EXISTS idx_external_write_intents_target
ON external_write_intents (target_system, operation_type);

CREATE INDEX IF NOT EXISTS idx_external_write_intents_source
ON external_write_intents (source_type, source_id);

CREATE INDEX IF NOT EXISTS idx_external_write_attempts_intent
ON external_write_attempts (intent_id, attempt_number);

CREATE INDEX IF NOT EXISTS idx_external_write_attempts_status
ON external_write_attempts (status, mode);

CREATE INDEX IF NOT EXISTS idx_idempotency_records_dedupe
ON idempotency_records (target_system, operation_type, dedupe_key);
