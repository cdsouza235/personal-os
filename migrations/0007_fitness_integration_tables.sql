CREATE TABLE IF NOT EXISTS fitness_integration_state (
    id TEXT PRIMARY KEY,
    integration_name TEXT NOT NULL,
    integration_type TEXT NOT NULL,
    status TEXT NOT NULL,
    data_root_label TEXT NOT NULL,
    expected_files_json TEXT NOT NULL,
    last_validation_at TEXT,
    last_summary_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (integration_type IN ('local_csv_tracker')),
    CHECK (status IN ('draft', 'configured', 'validated', 'warning', 'disabled'))
);

CREATE TABLE IF NOT EXISTS fitness_validation_runs (
    id TEXT PRIMARY KEY,
    integration_state_id TEXT NOT NULL REFERENCES fitness_integration_state(id),
    run_type TEXT NOT NULL,
    dry_run INTEGER NOT NULL,
    status TEXT NOT NULL,
    input_json TEXT NOT NULL,
    output_json TEXT NOT NULL,
    error_message TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    CHECK (run_type IN ('fixture_validation', 'schema_preview', 'dry_run')),
    CHECK (dry_run IN (0, 1)),
    CHECK (status IN ('started', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS fitness_file_contracts (
    id TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_role TEXT NOT NULL,
    required_columns_json TEXT NOT NULL,
    optional_columns_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        file_role IN (
            'workout_sessions',
            'workout_exercises',
            'weekly_recovery',
            'exercise_library'
        )
    ),
    CHECK (status IN ('draft', 'active', 'deprecated'))
);

CREATE INDEX IF NOT EXISTS idx_fitness_integration_state_type_status
ON fitness_integration_state (integration_type, status);

CREATE INDEX IF NOT EXISTS idx_fitness_validation_runs_state
ON fitness_validation_runs (integration_state_id, created_at);

CREATE INDEX IF NOT EXISTS idx_fitness_validation_runs_status
ON fitness_validation_runs (status);

CREATE INDEX IF NOT EXISTS idx_fitness_file_contracts_role_status
ON fitness_file_contracts (file_role, status);
