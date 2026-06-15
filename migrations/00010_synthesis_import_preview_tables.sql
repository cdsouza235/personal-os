CREATE TABLE IF NOT EXISTS synthesis_import_previews (
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
    CHECK (status IN ('draft', 'validated', 'rejected', 'failed')),
    CHECK (length(raw_excerpt) <= 2000)
);

CREATE INDEX IF NOT EXISTS idx_synthesis_import_previews_source_type
ON synthesis_import_previews (source_type, created_at);

CREATE INDEX IF NOT EXISTS idx_synthesis_import_previews_status
ON synthesis_import_previews (status, created_at);

CREATE INDEX IF NOT EXISTS idx_synthesis_import_previews_input_hash
ON synthesis_import_previews (input_hash);
