BEGIN;

CREATE TABLE projects_status_constrained (
    project_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    CHECK (status IN ('active', 'paused', 'completed', 'archived'))
);

INSERT INTO projects_status_constrained (
    project_id,
    title,
    status,
    metadata_json,
    notes,
    created_at_utc,
    updated_at_utc
)
SELECT
    project_id,
    title,
    status,
    metadata_json,
    notes,
    created_at_utc,
    updated_at_utc
FROM projects;

DROP TABLE projects;
ALTER TABLE projects_status_constrained RENAME TO projects;

CREATE TABLE followups_status_constrained (
    followup_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    notes TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    CHECK (status IN ('open', 'proposed', 'completed', 'archived', 'blocked'))
);

INSERT INTO followups_status_constrained (
    followup_id,
    title,
    status,
    source,
    metadata_json,
    notes,
    created_at_utc,
    updated_at_utc
)
SELECT
    followup_id,
    title,
    status,
    source,
    metadata_json,
    notes,
    created_at_utc,
    updated_at_utc
FROM followups;

DROP TABLE followups;
ALTER TABLE followups_status_constrained RENAME TO followups;

COMMIT;
