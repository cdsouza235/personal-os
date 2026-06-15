CREATE TABLE IF NOT EXISTS report_jobs (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    cadence TEXT NOT NULL,
    config_json TEXT NOT NULL,
    status TEXT NOT NULL,
    last_run_at TEXT,
    next_due_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        job_type IN (
            'weekly_chart_pack_index',
            'tradingview_alert_digest',
            'macro_calendar',
            'earnings_calendar',
            'priority_status_report',
            'routine_adherence_report',
            'todoist_completion_report',
            'calendar_utilization_report'
        )
    ),
    CHECK (cadence IN ('manual', 'daily', 'weekly', 'monthly')),
    CHECK (status IN ('draft', 'active', 'paused', 'disabled'))
);

CREATE TABLE IF NOT EXISTS report_runs (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES report_jobs(id),
    run_type TEXT NOT NULL,
    dry_run INTEGER NOT NULL,
    status TEXT NOT NULL,
    input_json TEXT NOT NULL,
    output_json TEXT NOT NULL,
    error_message TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    CHECK (run_type IN ('preview', 'dry_run', 'simulated')),
    CHECK (dry_run IN (0, 1)),
    CHECK (status IN ('started', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS chart_pack_reviews (
    id TEXT PRIMARY KEY,
    review_date TEXT NOT NULL,
    week_start TEXT NOT NULL,
    week_end TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT,
    title TEXT NOT NULL,
    thesis_context TEXT,
    chart_pack_json TEXT NOT NULL,
    tradingview_alerts_json TEXT NOT NULL,
    synthesis_markdown TEXT NOT NULL,
    structured_summary_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        source_type IN (
            'chatgpt_synthesis',
            'manual_entry',
            'imported_markdown',
            'fake_fixture'
        )
    ),
    CHECK (status IN ('draft', 'validated', 'stored', 'rejected'))
);

CREATE INDEX IF NOT EXISTS idx_report_jobs_type_status
ON report_jobs (job_type, status);

CREATE INDEX IF NOT EXISTS idx_report_jobs_next_due
ON report_jobs (next_due_at);

CREATE INDEX IF NOT EXISTS idx_report_runs_job
ON report_runs (job_id, created_at);

CREATE INDEX IF NOT EXISTS idx_report_runs_status
ON report_runs (status);

CREATE INDEX IF NOT EXISTS idx_chart_pack_reviews_week
ON chart_pack_reviews (week_start, week_end);

CREATE INDEX IF NOT EXISTS idx_chart_pack_reviews_status
ON chart_pack_reviews (status);
