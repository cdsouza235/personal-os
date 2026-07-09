-- Adds first-class cadence columns to routines (D-PO-010), purely additive.
-- settings_json is left untouched; new columns are nullable and existing rows
-- are backfilled only for cadence_type, using settings_json as the source.
ALTER TABLE routines ADD COLUMN cadence_type TEXT;
ALTER TABLE routines ADD COLUMN cadence_config_json TEXT;
ALTER TABLE routines ADD COLUMN missed_behavior_default TEXT;
ALTER TABLE routines ADD COLUMN rotation_group TEXT;
ALTER TABLE routines ADD COLUMN weekly_target INTEGER;

UPDATE routines
SET cadence_type = CASE
    WHEN json_valid(settings_json) AND json_type(settings_json, '$.cadence') = 'text'
        THEN json_extract(settings_json, '$.cadence')
    ELSE 'manual_only'
END
WHERE cadence_type IS NULL;
