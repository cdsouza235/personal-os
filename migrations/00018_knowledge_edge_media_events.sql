-- P-KE-1A: Knowledge Edge media items and scheduled events (amendment §13.1-13.3,
-- §8.4 event lifecycle, §11.3 directness, §11.4 dedup/canonical grouping).
-- Purely additive CREATE TABLE per PHASE0_ARCHITECTURE_DECISIONS.md AD-5. No seed data:
-- these are discovery-pipeline tables with no reference rows in either seed authority.
--
-- Every row of both ke_media_items and ke_scheduled_events carries three independent
-- state-track columns, matching the amendment's explicit three-track model (§8.4):
--   content_status        -- the pipeline's own processing/lifecycle status
--   decision_state         -- the user's Watch/Save/Skip/Watched-shaped decision
--   queue_visibility_state -- candidate -> queued | suppressed | expired -> archived
-- `watched`, `skipped`, and `expired` never appear in the content-status track; they are
-- decision_state / queue_visibility_state values only. The allowed values and valid
-- transition tables for all three tracks, for both entity types, are published in
-- personalos.knowledge_edge.state.events (MEDIA_CONTENT_TRANSITIONS,
-- EVENT_STATUS_TRANSITIONS, MEDIA_DECISION_TRANSITIONS, EVENT_DECISION_TRANSITIONS,
-- QUEUE_VISIBILITY_TRANSITIONS) and enforced there, not by a DB trigger -- the CHECK
-- constraints below only pin the allowed *value sets*, mirroring the CHECK-for-values /
-- Python-for-transitions split every other module in this repo already uses (e.g.
-- routines/composer status columns).

CREATE TABLE IF NOT EXISTS ke_canonical_groups (
    canonical_group_id TEXT PRIMARY KEY,
    dedupe_rule TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        dedupe_rule IN (
            'shared_feed_guid',
            'same_channel_video_id',
            'same_underlying_id_title_change',
            'live_and_official_replay',
            'manual'
        )
    )
);

CREATE TABLE IF NOT EXISTS ke_media_items (
    media_item_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_specific_id TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    alternate_urls_json TEXT NOT NULL DEFAULT '[]',
    title TEXT NOT NULL,
    description_excerpt TEXT NOT NULL DEFAULT '',
    source_precedence TEXT NOT NULL,
    published_at TEXT,
    discovered_at TEXT NOT NULL,
    media_type TEXT NOT NULL,
    duration_seconds INTEGER,
    directness_class TEXT,
    match_confidence REAL,
    priority_score REAL,
    priority_explanation TEXT NOT NULL DEFAULT '',
    canonical_group_id TEXT,
    is_canonical INTEGER NOT NULL DEFAULT 1,
    dedupe_key TEXT NOT NULL,
    content_status TEXT NOT NULL DEFAULT 'discovered',
    decision_state TEXT NOT NULL DEFAULT 'undecided',
    queue_visibility_state TEXT NOT NULL DEFAULT 'candidate',
    expiry_at TEXT,
    pinned INTEGER NOT NULL DEFAULT 0,
    coverage_notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES ke_sources (source_id) ON DELETE RESTRICT,
    FOREIGN KEY (canonical_group_id) REFERENCES ke_canonical_groups (canonical_group_id) ON DELETE RESTRICT,
    CHECK (
        source_precedence IN (
            'official',
            'regulator_exchange',
            'approved_structured_provider',
            'reputable_secondary',
            'broad_search'
        )
    ),
    CHECK (
        media_type IN (
            'podcast_episode',
            'video_interview',
            'panel',
            'keynote',
            'clip',
            'earnings_call_recording',
            'other'
        )
    ),
    CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
    CHECK (
        directness_class IS NULL OR directness_class IN (
            'direct_primary',
            'direct_secondary_upload',
            'panel_participant',
            'host_or_interviewer',
            'mentioned_only',
            'commentary_about',
            'ambiguous'
        )
    ),
    CHECK (match_confidence IS NULL OR (match_confidence >= 0 AND match_confidence <= 1)),
    CHECK (is_canonical IN (0, 1)),
    CHECK (
        content_status IN (
            'discovered', 'normalized', 'ranked', 'corrected', 'superseded', 'archived'
        )
    ),
    CHECK (
        decision_state IN ('undecided', 'watch', 'save_for_later', 'skip', 'watched')
    ),
    CHECK (
        queue_visibility_state IN ('candidate', 'queued', 'suppressed', 'expired', 'archived')
    ),
    CHECK (pinned IN (0, 1)),
    UNIQUE (source_id, source_specific_id),
    UNIQUE (dedupe_key)
);

CREATE TABLE IF NOT EXISTS ke_discovery_occurrences (
    occurrence_id TEXT PRIMARY KEY,
    media_item_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    scan_run_id TEXT,
    discovered_at TEXT NOT NULL,
    raw_payload_summary_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (media_item_id) REFERENCES ke_media_items (media_item_id) ON DELETE RESTRICT,
    FOREIGN KEY (source_id) REFERENCES ke_sources (source_id) ON DELETE RESTRICT,
    UNIQUE (media_item_id, source_id, scan_run_id)
);

-- Matched people/roles/companies/topics for a media item or scheduled event, with the
-- confidence + reason + user false-positive flag the amendment requires for Lane B/C
-- matches (§8.2, §8.3).
CREATE TABLE IF NOT EXISTS ke_entity_matches (
    entity_match_id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    matched_entity_type TEXT NOT NULL,
    matched_entity_id TEXT NOT NULL,
    match_method TEXT NOT NULL,
    confidence REAL NOT NULL,
    reason TEXT NOT NULL,
    is_false_positive INTEGER NOT NULL DEFAULT 0,
    flagged_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (target_type IN ('media_item', 'scheduled_event')),
    CHECK (matched_entity_type IN ('person', 'role', 'company', 'topic')),
    CHECK (
        match_method IN (
            'exact_alias',
            'spelling_variant',
            'role_occupant_resolution',
            'company_ticker_mention',
            'topic_keyword',
            'manual'
        )
    ),
    CHECK (confidence >= 0 AND confidence <= 1),
    CHECK (is_false_positive IN (0, 1))
);

CREATE TABLE IF NOT EXISTS ke_scheduled_events (
    event_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    fiscal_period TEXT,
    event_type TEXT NOT NULL,
    scheduled_date TEXT NOT NULL,
    start_time_utc TEXT,
    end_time_utc TEXT,
    time_precision TEXT NOT NULL DEFAULT 'date_only',
    source_timezone TEXT NOT NULL DEFAULT 'UTC',
    timing_label TEXT,
    schedule_confidence TEXT NOT NULL DEFAULT 'unknown',
    schedule_source TEXT NOT NULL DEFAULT '',
    official_event_page_url TEXT,
    live_webcast_url TEXT,
    replay_url TEXT,
    earnings_release_url TEXT,
    filing_urls_json TEXT NOT NULL DEFAULT '[]',
    slides_url TEXT,
    shareholder_letter_url TEXT,
    prepared_remarks_url TEXT,
    event_status TEXT NOT NULL DEFAULT 'discovered',
    decision_state TEXT NOT NULL DEFAULT 'undecided',
    queue_visibility_state TEXT NOT NULL DEFAULT 'candidate',
    link_verification_at TEXT,
    priority_explanation TEXT NOT NULL DEFAULT '',
    pinned INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES ke_companies (company_id) ON DELETE RESTRICT,
    CHECK (
        event_type IN (
            'quarterly_earnings',
            'annual_results',
            'investor_day',
            'capital_markets_day',
            'strategy_webcast'
        )
    ),
    CHECK (time_precision IN ('date_only', 'approximate', 'exact')),
    CHECK (
        timing_label IS NULL OR timing_label IN ('before_open', 'after_close', 'during_market')
    ),
    CHECK (
        schedule_confidence IN (
            'confirmed_official', 'confirmed_secondary', 'estimated', 'unknown'
        )
    ),
    CHECK (
        event_status IN (
            'discovered', 'tentative', 'confirmed', 'scheduled', 'live', 'ended',
            'replay_pending', 'replay_available', 'archived', 'changed', 'cancelled'
        )
    ),
    CHECK (
        decision_state IN ('undecided', 'watch_live', 'save_replay', 'skip', 'watched')
    ),
    CHECK (
        queue_visibility_state IN ('candidate', 'queued', 'suppressed', 'expired', 'archived')
    ),
    CHECK (pinned IN (0, 1)),
    UNIQUE (company_id, fiscal_period, event_type)
);

CREATE INDEX IF NOT EXISTS idx_ke_media_items_source
ON ke_media_items (source_id, discovered_at);

CREATE INDEX IF NOT EXISTS idx_ke_media_items_canonical_group
ON ke_media_items (canonical_group_id, is_canonical);

CREATE INDEX IF NOT EXISTS idx_ke_media_items_queue_visibility
ON ke_media_items (queue_visibility_state, content_status);

CREATE INDEX IF NOT EXISTS idx_ke_media_items_decision_state
ON ke_media_items (decision_state);

CREATE INDEX IF NOT EXISTS idx_ke_discovery_occurrences_media_item
ON ke_discovery_occurrences (media_item_id);

CREATE INDEX IF NOT EXISTS idx_ke_entity_matches_target
ON ke_entity_matches (target_type, target_id);

CREATE INDEX IF NOT EXISTS idx_ke_entity_matches_matched_entity
ON ke_entity_matches (matched_entity_type, matched_entity_id);

CREATE INDEX IF NOT EXISTS idx_ke_scheduled_events_company
ON ke_scheduled_events (company_id, scheduled_date);

CREATE INDEX IF NOT EXISTS idx_ke_scheduled_events_status
ON ke_scheduled_events (event_status, queue_visibility_state);
