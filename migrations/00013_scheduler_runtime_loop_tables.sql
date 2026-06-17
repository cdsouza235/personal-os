CREATE TABLE IF NOT EXISTS scheduler_jobs (
    scheduler_job_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    job_type TEXT NOT NULL,
    cadence_type TEXT NOT NULL,
    schedule_json TEXT NOT NULL DEFAULT '{}',
    timezone TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 0,
    no_send_mode INTEGER NOT NULL DEFAULT 1,
    no_external_writes INTEGER NOT NULL DEFAULT 1,
    fake_model_only INTEGER NOT NULL DEFAULT 1,
    target_window TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        job_type IN (
            'today_view',
            'briefing_preview',
            'status_summary',
            'synthesis_apply_summary',
            'side_effect_summary',
            'dashboard_render_preview',
            'other'
        )
    ),
    CHECK (
        cadence_type IN (
            'manual',
            'daily',
            'weekdays',
            'specific_times',
            'interval_minutes'
        )
    ),
    CHECK (enabled IN (0, 1)),
    CHECK (no_send_mode = 1),
    CHECK (no_external_writes = 1),
    CHECK (fake_model_only = 1),
    CHECK (
        target_window IS NULL
        OR target_window IN ('morning', 'midday', 'afternoon', 'evening')
    ),
    CHECK (status IN ('draft', 'enabled_dev_test', 'disabled', 'blocked')),
    CHECK (status != 'enabled_dev_test' OR enabled = 1)
);

CREATE TABLE IF NOT EXISTS scheduler_runs (
    scheduler_run_id TEXT PRIMARY KEY,
    scheduler_job_id TEXT,
    job_type TEXT NOT NULL,
    run_type TEXT NOT NULL,
    scheduled_for TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    status TEXT NOT NULL,
    completion_report_json TEXT NOT NULL,
    no_send_mode INTEGER NOT NULL DEFAULT 1,
    no_external_writes INTEGER NOT NULL DEFAULT 1,
    live_write INTEGER NOT NULL DEFAULT 0,
    external_mutation INTEGER NOT NULL DEFAULT 0,
    scheduler_activation INTEGER NOT NULL DEFAULT 0,
    launch_agent_installed INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (scheduler_job_id)
        REFERENCES scheduler_jobs (scheduler_job_id)
        ON DELETE RESTRICT,
    CHECK (
        job_type IN (
            'today_view',
            'briefing_preview',
            'status_summary',
            'synthesis_apply_summary',
            'side_effect_summary',
            'dashboard_render_preview',
            'other'
        )
    ),
    CHECK (
        run_type IN (
            'manual_simulated',
            'due_check_simulated',
            'no_send_preview'
        )
    ),
    CHECK (status IN ('completed', 'blocked', 'failed', 'skipped')),
    CHECK (no_send_mode = 1),
    CHECK (no_external_writes = 1),
    CHECK (live_write = 0),
    CHECK (external_mutation = 0),
    CHECK (scheduler_activation = 0),
    CHECK (launch_agent_installed = 0)
);

CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_type_status
ON scheduler_jobs (job_type, status);

CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_enabled
ON scheduler_jobs (enabled, status);

CREATE INDEX IF NOT EXISTS idx_scheduler_runs_job
ON scheduler_runs (scheduler_job_id, started_at);

CREATE INDEX IF NOT EXISTS idx_scheduler_runs_type_status
ON scheduler_runs (job_type, status, started_at);
