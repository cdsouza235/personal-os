-- P-RAIL-LEDGER-01: add 'completed_live' / 'live' ledger states so a real live write
-- can be recorded honestly, instead of the 'completed_simulated' mislabel both rails
-- were forced into by migration 00011's absolute CHECK (live_write = 0) constraints
-- (see audits/h2-rail-dispatch-design-consult-fable-report.md §5.2).
--
-- SQLite cannot ALTER a CHECK constraint, so this rebuilds all three ledger tables
-- following SQLite's documented 12-step ALTER TABLE procedure (foreign_keys off for
-- the rebuild, since external_write_attempts and idempotency_records both hold FKs
-- into tables being rebuilt here).

PRAGMA foreign_keys = OFF;

BEGIN;

CREATE TABLE external_write_intents_v2 (
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
            'completed_simulated',
            'completed_live'
        )
    ),
    -- Honest-ledger invariant (D-PO-017 item 6): live_write and the two "no_*" safety
    -- flags always move together (no half-live mixture is expressible), and a
    -- live_write=1 row is only ever expressible when status says so explicitly, in
    -- both directions.
    CHECK (live_write = 0 OR status = 'completed_live'),
    CHECK (status != 'completed_live' OR live_write = 1),
    CHECK (live_write = 1 OR (no_external_writes = 1 AND no_send_mode = 1)),
    CHECK (live_write = 0 OR (no_external_writes = 0 AND no_send_mode = 0)),
    UNIQUE (target_system, operation_type, dedupe_key)
);

INSERT INTO external_write_intents_v2 (
    intent_id,
    source_type,
    source_id,
    target_system,
    operation_type,
    risk_level,
    approval_mode,
    status,
    idempotency_key,
    dedupe_key,
    payload_json,
    validation_report_json,
    no_external_writes,
    no_send_mode,
    live_write,
    created_at,
    updated_at
)
SELECT
    intent_id,
    source_type,
    source_id,
    target_system,
    operation_type,
    risk_level,
    approval_mode,
    status,
    idempotency_key,
    dedupe_key,
    payload_json,
    validation_report_json,
    no_external_writes,
    no_send_mode,
    live_write,
    created_at,
    updated_at
FROM external_write_intents;

DROP TABLE external_write_intents;
ALTER TABLE external_write_intents_v2 RENAME TO external_write_intents;

CREATE TABLE external_write_attempts_v2 (
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
    CHECK (mode IN ('dry_run', 'simulated', 'live_blocked', 'live')),
    CHECK (status IN ('succeeded', 'failed', 'blocked', 'skipped_duplicate')),
    CHECK (mode != 'live_blocked' OR status = 'blocked'),
    CHECK (live_write = 0 OR mode = 'live'),
    CHECK (mode != 'live' OR live_write = 1),
    CHECK (live_write = 1 OR (no_external_writes = 1 AND no_send_mode = 1)),
    CHECK (live_write = 0 OR (no_external_writes = 0 AND no_send_mode = 0)),
    UNIQUE (intent_id, attempt_number)
);

INSERT INTO external_write_attempts_v2 (
    attempt_id,
    intent_id,
    attempt_number,
    mode,
    adapter_name,
    status,
    request_fingerprint,
    response_summary_json,
    error_message,
    no_external_writes,
    no_send_mode,
    live_write,
    created_at
)
SELECT
    attempt_id,
    intent_id,
    attempt_number,
    mode,
    adapter_name,
    status,
    request_fingerprint,
    response_summary_json,
    error_message,
    no_external_writes,
    no_send_mode,
    live_write,
    created_at
FROM external_write_attempts;

DROP TABLE external_write_attempts;
ALTER TABLE external_write_attempts_v2 RENAME TO external_write_attempts;

CREATE TABLE idempotency_records_v2 (
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
            'completed_simulated',
            'completed_live'
        )
    ),
    UNIQUE (target_system, operation_type, dedupe_key)
);

INSERT INTO idempotency_records_v2 (
    idempotency_key,
    target_system,
    operation_type,
    source_type,
    source_id,
    dedupe_key,
    payload_fingerprint,
    first_seen_at,
    last_seen_at,
    status,
    linked_intent_id,
    linked_attempt_id
)
SELECT
    idempotency_key,
    target_system,
    operation_type,
    source_type,
    source_id,
    dedupe_key,
    payload_fingerprint,
    first_seen_at,
    last_seen_at,
    status,
    linked_intent_id,
    linked_attempt_id
FROM idempotency_records;

DROP TABLE idempotency_records;
ALTER TABLE idempotency_records_v2 RENAME TO idempotency_records;

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

COMMIT;

PRAGMA foreign_keys = ON;
