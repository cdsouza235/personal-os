DROP INDEX IF EXISTS idx_synthesis_import_previews_source_type;
DROP INDEX IF EXISTS idx_synthesis_import_previews_status;
DROP INDEX IF EXISTS idx_synthesis_import_previews_input_hash;

ALTER TABLE synthesis_import_previews
RENAME TO synthesis_import_previews_legacy;

CREATE TABLE synthesis_import_previews (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    input_format TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    source_timestamp TEXT,
    source_reference TEXT,
    raw_excerpt TEXT NOT NULL,
    parsed_json TEXT NOT NULL,
    preview_report_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        source_type IN (
            'chatgpt_synthesis',
            'manual_structured_import',
            'fake_fixture'
        )
    ),
    CHECK (
        input_format IN (
            'json',
            'markdown_fenced_json',
            'structured_markdown'
        )
    ),
    CHECK (
        status IN (
            'draft',
            'validated',
            'rejected',
            'failed',
            'apply_completed',
            'apply_partially_completed',
            'apply_blocked',
            'apply_failed'
        )
    ),
    CHECK (length(raw_excerpt) <= 2000)
);

INSERT INTO synthesis_import_previews (
    id,
    source_type,
    input_format,
    input_hash,
    source_timestamp,
    source_reference,
    raw_excerpt,
    parsed_json,
    preview_report_json,
    status,
    created_at,
    updated_at
)
SELECT
    id,
    source_type,
    input_format,
    input_hash,
    source_timestamp,
    source_reference,
    raw_excerpt,
    parsed_json,
    preview_report_json,
    status,
    created_at,
    updated_at
FROM synthesis_import_previews_legacy;

DROP TABLE synthesis_import_previews_legacy;

CREATE INDEX IF NOT EXISTS idx_synthesis_import_previews_source_type
ON synthesis_import_previews (source_type, created_at);

CREATE INDEX IF NOT EXISTS idx_synthesis_import_previews_status
ON synthesis_import_previews (status, created_at);

CREATE INDEX IF NOT EXISTS idx_synthesis_import_previews_input_hash
ON synthesis_import_previews (input_hash);

CREATE TABLE IF NOT EXISTS synthesis_apply_runs (
    apply_run_id TEXT PRIMARY KEY,
    preview_id TEXT NOT NULL,
    approval_source_type TEXT NOT NULL,
    approval_source_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    approved_candidate_count INTEGER NOT NULL,
    applied_candidate_count INTEGER NOT NULL,
    blocked_candidate_count INTEGER NOT NULL,
    skipped_candidate_count INTEGER NOT NULL,
    failed_candidate_count INTEGER NOT NULL,
    no_external_writes INTEGER NOT NULL DEFAULT 1,
    no_send_mode INTEGER NOT NULL DEFAULT 1,
    live_write INTEGER NOT NULL DEFAULT 0,
    internal_state_mutation INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    completion_report_json TEXT NOT NULL,
    FOREIGN KEY (preview_id)
        REFERENCES synthesis_import_previews (id)
        ON DELETE RESTRICT,
    CHECK (approval_source_type IN ('json_file', 'json_object')),
    CHECK (
        status IN (
            'completed',
            'partially_completed',
            'blocked',
            'failed',
            'no_op'
        )
    ),
    CHECK (approved_candidate_count >= 0),
    CHECK (applied_candidate_count >= 0),
    CHECK (blocked_candidate_count >= 0),
    CHECK (skipped_candidate_count >= 0),
    CHECK (failed_candidate_count >= 0),
    CHECK (no_external_writes = 1),
    CHECK (no_send_mode = 1),
    CHECK (live_write = 0),
    CHECK (internal_state_mutation IN (0, 1))
);

CREATE TABLE IF NOT EXISTS synthesis_apply_items (
    apply_item_id TEXT PRIMARY KEY,
    apply_run_id TEXT NOT NULL,
    preview_id TEXT NOT NULL,
    candidate_type TEXT NOT NULL,
    candidate_key TEXT NOT NULL,
    candidate_index INTEGER NOT NULL,
    candidate_hash TEXT NOT NULL,
    approval_status TEXT NOT NULL,
    apply_status TEXT NOT NULL,
    target_table TEXT,
    target_id TEXT,
    risk_level TEXT,
    approval_mode TEXT,
    high_stakes INTEGER NOT NULL DEFAULT 0,
    rollback_metadata_json TEXT NOT NULL,
    validation_report_json TEXT NOT NULL,
    error_message TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (apply_run_id)
        REFERENCES synthesis_apply_runs (apply_run_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (preview_id)
        REFERENCES synthesis_import_previews (id)
        ON DELETE RESTRICT,
    CHECK (candidate_index >= 0),
    CHECK (
        approval_status IN (
            'approved',
            'rejected',
            'blocked',
            'unsupported',
            'skipped',
            'review_required'
        )
    ),
    CHECK (
        apply_status IN (
            'applied',
            'not_applied',
            'blocked',
            'skipped_duplicate',
            'failed'
        )
    ),
    CHECK (
        target_table IS NULL
        OR target_table IN ('priorities', 'projects', 'followups')
    ),
    CHECK (risk_level IS NULL OR risk_level IN ('low', 'medium', 'high')),
    CHECK (
        approval_mode IS NULL
        OR approval_mode IN ('auto_allowed', 'approval_required', 'manual_only')
    ),
    CHECK (high_stakes IN (0, 1)),
    UNIQUE (apply_run_id, candidate_key)
);

CREATE INDEX IF NOT EXISTS idx_synthesis_apply_runs_preview
ON synthesis_apply_runs (preview_id, created_at);

CREATE INDEX IF NOT EXISTS idx_synthesis_apply_runs_status
ON synthesis_apply_runs (status, created_at);

CREATE INDEX IF NOT EXISTS idx_synthesis_apply_items_run
ON synthesis_apply_items (apply_run_id, candidate_key);

CREATE INDEX IF NOT EXISTS idx_synthesis_apply_items_preview
ON synthesis_apply_items (preview_id, candidate_type, candidate_index);

CREATE INDEX IF NOT EXISTS idx_synthesis_apply_items_target
ON synthesis_apply_items (target_table, target_id);
