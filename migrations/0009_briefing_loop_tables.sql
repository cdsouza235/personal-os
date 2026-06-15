CREATE TABLE IF NOT EXISTS daily_plans (
    id TEXT PRIMARY KEY,
    source_date TEXT NOT NULL,
    timezone TEXT NOT NULL,
    plan_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (status IN ('draft', 'generated', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS briefing_outputs (
    id TEXT PRIMARY KEY,
    daily_plan_id TEXT REFERENCES daily_plans(id),
    briefing_window_id TEXT,
    briefing_window_name TEXT NOT NULL,
    source_date TEXT NOT NULL,
    timezone TEXT NOT NULL,
    composer_packet_id TEXT REFERENCES composer_packets(id),
    composer_output_id TEXT REFERENCES composer_outputs(id),
    readable_text TEXT NOT NULL,
    output_json TEXT NOT NULL,
    manual_export_markdown TEXT NOT NULL,
    completion_report_json TEXT NOT NULL,
    delivery_mode TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (briefing_window_name IN ('morning', 'midday', 'afternoon', 'evening')),
    CHECK (delivery_mode IN ('no_send', 'manual_export')),
    CHECK (status IN ('preview', 'generated', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_daily_plans_source_date
ON daily_plans (source_date, timezone);

CREATE INDEX IF NOT EXISTS idx_daily_plans_status
ON daily_plans (status);

CREATE INDEX IF NOT EXISTS idx_briefing_outputs_daily_plan
ON briefing_outputs (daily_plan_id);

CREATE INDEX IF NOT EXISTS idx_briefing_outputs_source_window
ON briefing_outputs (source_date, briefing_window_name);

CREATE INDEX IF NOT EXISTS idx_briefing_outputs_status
ON briefing_outputs (status, created_at);
