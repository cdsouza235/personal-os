-- P-KE-2B iteration 2 (Conductor scope amendment, 2026-07-17): SQLite-backed TTL
-- cache for youtube.py's search.list person-search display metadata (amendment
-- Sec10.4/Sec13.4's "TTL-controlled refreshable cache with expiry, refresh, and
-- deletion tests" requirement, closing this packet's own iteration-2 audit finding
-- F1). Purely additive CREATE TABLE per PHASE0_ARCHITECTURE_DECISIONS.md AD-5; no
-- ALTER/DROP on any existing table.
--
-- P-KE-2B's original brief forbade migrations, and this packet's own iteration-1
-- build (see rails/knowledge_edge/youtube.py's module docstring history) verified in
-- full that no earlier migration (00017-00024) ever defined a provider-metadata
-- cache table, despite the amendment's text describing that structure as something
-- "1A's schema provides" -- iteration 1 shipped a pure-Python injectable store
-- instead and flagged the gap rather than inventing undocumented persistence. This
-- migration exists because the packet's iteration-2 scope amendment explicitly named
-- closing that exact gap as in-scope state-layer work, mirroring exactly how P-KE-2A's
-- own iteration-2 scope amendment added migration 00024 to close its own
-- Conductor-surfaced finding after its original brief likewise forbade migrations.
--
-- No FK to ke_people(person_id): a person-search cache entry is keyed by whatever
-- person_id the caller passes (a Lane B/C roster person, in production), but this
-- table's own correctness (expiry/refresh/deletion) never depends on that row
-- existing, and the rail's own gate-isolation tests exercise this table without
-- necessarily seeding a ke_people row first -- an FK here would couple a pure cache
-- to roster membership for no correctness benefit.
CREATE TABLE IF NOT EXISTS ke_person_search_cache (
    person_id TEXT NOT NULL,
    query TEXT NOT NULL,
    results_json TEXT NOT NULL DEFAULT '[]',
    fetched_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (person_id, query)
);

CREATE INDEX IF NOT EXISTS idx_ke_person_search_cache_expires_at
ON ke_person_search_cache (expires_at);
