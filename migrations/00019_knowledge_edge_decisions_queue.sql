-- P-KE-1A: Knowledge Edge decision/queue audit trail (amendment §13.1, §13.4).
-- Purely additive CREATE TABLE per PHASE0_ARCHITECTURE_DECISIONS.md AD-5. No seed data.
--
-- ke_user_decisions holds the current, per-entity decision record (1:1 with a media item
-- or scheduled event) with decision-specific metadata that doesn't fit on the entity row
-- itself (e.g. the opt-in live reminder for a watch_live commitment, §7.4).
-- ke_decision_history is the append-only audit trail required by §13.4: every transition
-- on any of the three tracks (content_status / decision_state / queue_visibility_state),
-- for either entity type, is one row here and rows are never updated or deleted.
-- ke_queue_snapshots records which entities appeared in which section of which evening's
-- queue, so a past queue can be reconstructed even after caps/expiry later change the
-- entities' current state (§7.2 six-section layout).

CREATE TABLE IF NOT EXISTS ke_user_decisions (
    decision_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    decision_state TEXT NOT NULL,
    live_reminder_opt_in INTEGER NOT NULL DEFAULT 0,
    decided_at TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (entity_type IN ('media_item', 'scheduled_event')),
    CHECK (
        decision_state IN (
            'undecided', 'watch', 'save_for_later', 'skip', 'watched',
            'watch_live', 'save_replay'
        )
    ),
    CHECK (live_reminder_opt_in IN (0, 1)),
    UNIQUE (entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS ke_decision_history (
    history_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    track TEXT NOT NULL,
    from_value TEXT,
    to_value TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    changed_by TEXT NOT NULL DEFAULT 'system',
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    CHECK (entity_type IN ('media_item', 'scheduled_event')),
    CHECK (track IN ('content_status', 'decision_state', 'queue_visibility_state'))
);

CREATE TABLE IF NOT EXISTS ke_queue_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    queue_date TEXT NOT NULL,
    section TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    rank_position INTEGER NOT NULL,
    explanation TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    CHECK (
        section IN (
            'tomorrow_earnings_events',
            'p0_consequential_leaders',
            'p1_core_podcasts',
            'p2_market_voices',
            'saved_to_reconsider',
            'coverage_and_source_health'
        )
    ),
    CHECK (entity_type IN ('media_item', 'scheduled_event')),
    CHECK (rank_position > 0),
    UNIQUE (queue_date, section, entity_type, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_ke_decision_history_entity
ON ke_decision_history (entity_type, entity_id, changed_at);

CREATE INDEX IF NOT EXISTS idx_ke_decision_history_track
ON ke_decision_history (track, changed_at);

CREATE INDEX IF NOT EXISTS idx_ke_queue_snapshots_date_section
ON ke_queue_snapshots (queue_date, section, rank_position);
