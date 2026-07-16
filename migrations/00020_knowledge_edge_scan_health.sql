-- P-KE-1A: Knowledge Edge scan/cursor/source-health/coverage tables (amendment §11.1
-- cursor behavior, §10.5 coverage reporting, §17.3 health surface).
-- Purely additive CREATE TABLE per PHASE0_ARCHITECTURE_DECISIONS.md AD-5. No seed data:
-- these tables are populated by scan runs, which are Packet 1B+ (fixture/live adapters),
-- not this packet.

CREATE TABLE IF NOT EXISTS ke_scan_runs (
    scan_run_id TEXT PRIMARY KEY,
    run_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    triggered_by TEXT NOT NULL DEFAULT 'scheduler',
    started_at TEXT NOT NULL,
    completed_at TEXT,
    summary_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    CHECK (
        run_type IN (
            'full_scan', 'morning_refresh', 'manual_scan_now', 'targeted_link_check'
        )
    ),
    CHECK (status IN ('running', 'completed', 'partially_completed', 'failed')),
    CHECK (completed_at IS NULL OR completed_at >= started_at)
);

-- One row per source: the last successfully committed cursor plus the configurable
-- overlap window used to catch delayed uploads/clock differences (§11.1). A cursor is
-- only ever advanced after its source's batch is persisted -- that invariant is enforced
-- in personalos.knowledge_edge.state.scan, not in SQL.
CREATE TABLE IF NOT EXISTS ke_scan_cursors (
    cursor_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    last_successful_cursor_value TEXT,
    last_successful_at TEXT,
    overlap_window_seconds INTEGER NOT NULL DEFAULT 3600,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES ke_sources (source_id) ON DELETE RESTRICT,
    CHECK (overlap_window_seconds >= 0),
    UNIQUE (source_id)
);

CREATE TABLE IF NOT EXISTS ke_source_health (
    health_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    scan_run_id TEXT,
    status TEXT NOT NULL DEFAULT 'unknown',
    last_success_at TEXT,
    last_failure_at TEXT,
    consecutive_failure_count INTEGER NOT NULL DEFAULT 0,
    last_error_summary TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES ke_sources (source_id) ON DELETE RESTRICT,
    FOREIGN KEY (scan_run_id) REFERENCES ke_scan_runs (scan_run_id) ON DELETE RESTRICT,
    CHECK (status IN ('healthy', 'degraded', 'failed', 'stale', 'unknown')),
    CHECK (consecutive_failure_count >= 0),
    UNIQUE (source_id)
);

CREATE TABLE IF NOT EXISTS ke_coverage_reports (
    coverage_report_id TEXT PRIMARY KEY,
    scan_run_id TEXT NOT NULL,
    report_date TEXT NOT NULL,
    report_json TEXT NOT NULL,
    overall_summary TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (scan_run_id) REFERENCES ke_scan_runs (scan_run_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_ke_scan_runs_type_status
ON ke_scan_runs (run_type, status, started_at);

CREATE INDEX IF NOT EXISTS idx_ke_source_health_status
ON ke_source_health (status);

CREATE INDEX IF NOT EXISTS idx_ke_coverage_reports_date
ON ke_coverage_reports (report_date);
