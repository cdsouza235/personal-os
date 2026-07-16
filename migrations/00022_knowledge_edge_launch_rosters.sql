-- P-KE-1D: Knowledge Edge launch-roster seeds (amendment §8.1/§8.2/§8.3) + a
-- persisted home for the demoted/ambiguous queue tier (amendment §8.3, §7.2).
-- Purely additive: new seed INSERTs into existing 00017 tables, and one new
-- CREATE TABLE. No ALTER/DROP on any existing table (PHASE0_ARCHITECTURE_DECISIONS
-- AD-5) -- see the closing section's note on why the persisted demoted tier is a
-- new table rather than a seventh value added to ke_queue_snapshots' existing
-- CHECK(section IN (...)) constraint.
--
-- Closes C3 of audits/ke-phase-1-phase-end-fable-report.md (2026-07-16 phase-end
-- checkpoint, hold condition): 00017 seeded only the two ratified authorities named
-- in its own header (D-PO-018 role appendix, D-PO-019 company roster) and left the
-- §8.1/8.2/8.3 named-source/named-person rosters as empty, schema-validated tables.
-- This migration seeds those rosters from the ratified sources named below. Every
-- name, alias, and grouping below is copied verbatim from those sources; nothing is
-- invented. Where a source is named without a live endpoint, the row is seeded with
-- its name only and an explicit "Endpoint: TBC" marker in `notes` -- no
-- `ke_source_endpoints` row is created for it (that table's `url` column is
-- NOT NULL; a placeholder/guessed URL would misrepresent an unverified endpoint as
-- a real one). Status is seeded as `trial`, not `active`, for the same reason:
-- `scan_orchestrator.run_scan` iterates `ke.list_sources(status="active")` and
-- fetches every one of them through whatever adapter the caller supplies, so an
-- `active` row with no real endpoint would be silently polled by any future live
-- rail and would inflate `sources_healthy` counts in every fixture scan today
-- (verified against this packet's own test suite: it does, and several tests
-- assert exact healthy-source counts). `trial` is one of `ke_sources`' own
-- documented statuses (amendment §8.1 Requirements: "support active, trial,
-- paused, and retired sources") and is the correct one for a ratified-but-not-
-- yet-endpoint-verified source; flip to `active` once Packet 2A verifies and adds
-- the real feed endpoint.
--
-- Provenance:
--   1. Lane A (9 podcast feeds) -- amendment §8.1 "Launch roster" (AI/Crypto/Markets
--      groups) + governance/living/agent-writable/DECISIONS.md D-PO-018 item 1
--      ("source/channel allowlist approved as listed" -- the Lane A roster is
--      already a ratified allowlist, not merely named in prose).
--      docs/knowledge_edge/PHASE0_PROVIDERS_AND_ACCESS.md §6 (the external-access
--      bundle Session 1 approved) names this same 9-feed roster but records no RSS/
--      feed URLs for any of the nine -- confirmed by grep, nothing to seed as an
--      endpoint. §6's own "IR/webcast vendor-domain list" item documents the
--      identical pattern (mechanism approved, concrete list TBC at a later packet)
--      for a different surface; this migration applies the same discipline here.
--   2. Lane B (8 market voices + the one alias the amendment itself names) --
--      amendment §8.2 "Launch roster" and its Requirements bullet "spelling
--      variants such as Mohamed/Mohammed El-Erian" -- the only variant pair the
--      amendment's prose actually gives; no other aliases are invented for the
--      other seven.
--   3. Lane C (15 named individuals) -- amendment §8.3 "Launch people and roles",
--      the Frontier AI / Compute-and-technology-platforms / Enterprise-AI-capital-
--      allocation-and-crypto groups, EXCLUDING "Apple CEO role" and the
--      "configured heads of frontier AI labs" / "configured AI accelerator..."
--      role placeholders -- those are role-based watches, already seeded as
--      ke_roles/ke_role_occupancies in 00017 (ke-role-apple-ceo etc.), not named
--      individuals to seed again here as ke_people rows.
--
-- Person-ID namespacing note: Lane B/C people are seeded as `ke-person-mv-*` /
-- `ke-person-cl-*` (not the bare `ke-person-<name>` pattern 00017 used for role
-- occupants) because the existing Packet 1B/1C test suite already creates its own
-- ad hoc fixture people at the bare IDs `ke-person-tom-lee` and
-- `ke-person-jensen-huang` (test_knowledge_edge_scan_orchestrator.py,
-- test_knowledge_edge_dashboard.py) -- colliding with those on the primary key
-- would break every test built on that fixture helper. The `mv`/`cl` segment keeps
-- this migration's real launch-roster rows and the test suite's synthetic fixture
-- rows in disjoint ID spaces.

INSERT INTO ke_sources (
    source_id, source_type, lane, topic_group, name, status, notes, created_at, updated_at
)
VALUES
    ('ke-source-dwarkesh-podcast', 'podcast_feed', 'curated_podcasts', 'ai', 'Dwarkesh Podcast', 'trial', 'Amendment §8.1 launch roster (Lane A, AI). D-PO-018 item 1 ratified allowlist. Endpoint: TBC -- no RSS/feed URL given by the ratified source data; verify before the P-KE-2A live adapter.', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-source-latent-space', 'podcast_feed', 'curated_podcasts', 'ai', 'Latent Space', 'trial', 'Amendment §8.1 launch roster (Lane A, AI). D-PO-018 item 1 ratified allowlist. Endpoint: TBC -- no RSS/feed URL given by the ratified source data; verify before the P-KE-2A live adapter.', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-source-no-priors', 'podcast_feed', 'curated_podcasts', 'ai', 'No Priors', 'trial', 'Amendment §8.1 launch roster (Lane A, AI). D-PO-018 item 1 ratified allowlist. Endpoint: TBC -- no RSS/feed URL given by the ratified source data; verify before the P-KE-2A live adapter.', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-source-unchained', 'podcast_feed', 'curated_podcasts', 'crypto', 'Unchained', 'trial', 'Amendment §8.1 launch roster (Lane A, Crypto). D-PO-018 item 1 ratified allowlist. Endpoint: TBC -- no RSS/feed URL given by the ratified source data; verify before the P-KE-2A live adapter.', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-source-bankless', 'podcast_feed', 'curated_podcasts', 'crypto', 'Bankless', 'trial', 'Amendment §8.1 launch roster (Lane A, Crypto). D-PO-018 item 1 ratified allowlist. Endpoint: TBC -- no RSS/feed URL given by the ratified source data; verify before the P-KE-2A live adapter.', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-source-forward-guidance', 'podcast_feed', 'curated_podcasts', 'crypto', 'Forward Guidance', 'trial', 'Amendment §8.1 launch roster (Lane A, Crypto). D-PO-018 item 1 ratified allowlist. Endpoint: TBC -- no RSS/feed URL given by the ratified source data; verify before the P-KE-2A live adapter.', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-source-odd-lots', 'podcast_feed', 'curated_podcasts', 'markets', 'Odd Lots', 'trial', 'Amendment §8.1 launch roster (Lane A, Markets). D-PO-018 item 1 ratified allowlist. Endpoint: TBC -- no RSS/feed URL given by the ratified source data; verify before the P-KE-2A live adapter.', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-source-macro-voices', 'podcast_feed', 'curated_podcasts', 'markets', 'Macro Voices', 'trial', 'Amendment §8.1 launch roster (Lane A, Markets). D-PO-018 item 1 ratified allowlist. Endpoint: TBC -- no RSS/feed URL given by the ratified source data; verify before the P-KE-2A live adapter.', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-source-compound-and-friends', 'podcast_feed', 'curated_podcasts', 'markets', 'The Compound and Friends', 'trial', 'Amendment §8.1 launch roster (Lane A, Markets). D-PO-018 item 1 ratified allowlist. Endpoint: TBC -- no RSS/feed URL given by the ratified source data; verify before the P-KE-2A live adapter.', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00');

INSERT INTO ke_people (person_id, display_name, category, status, notes, created_at, updated_at)
VALUES
    ('ke-person-mv-tom-lee', 'Tom Lee', 'market_voice', 'active', 'Amendment §8.2 launch roster (Lane B).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-mv-dan-ives', 'Dan Ives', 'market_voice', 'active', 'Amendment §8.2 launch roster (Lane B).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-mv-mohamed-el-erian', 'Mohamed El-Erian', 'market_voice', 'active', 'Amendment §8.2 launch roster (Lane B). Requirements bullet names the spelling variant Mohamed/Mohammed El-Erian explicitly -- seeded as a ke_person_aliases row below.', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-mv-liz-ann-sonders', 'Liz Ann Sonders', 'market_voice', 'active', 'Amendment §8.2 launch roster (Lane B).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-mv-mike-wilson', 'Mike Wilson', 'market_voice', 'active', 'Amendment §8.2 launch roster (Lane B).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-mv-gene-munster', 'Gene Munster', 'market_voice', 'active', 'Amendment §8.2 launch roster (Lane B).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-mv-mike-novogratz', 'Mike Novogratz', 'market_voice', 'active', 'Amendment §8.2 launch roster (Lane B).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-mv-stephanie-link', 'Stephanie Link', 'market_voice', 'active', 'Amendment §8.2 launch roster (Lane B).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-cl-sam-altman', 'Sam Altman', 'consequential_leader', 'active', 'Amendment §8.3 launch roster (Lane C, Frontier AI).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-cl-dario-amodei', 'Dario Amodei', 'consequential_leader', 'active', 'Amendment §8.3 launch roster (Lane C, Frontier AI).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-cl-demis-hassabis', 'Demis Hassabis', 'consequential_leader', 'active', 'Amendment §8.3 launch roster (Lane C, Frontier AI).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-cl-jensen-huang', 'Jensen Huang', 'consequential_leader', 'active', 'Amendment §8.3 launch roster (Lane C, Compute and technology platforms).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-cl-lisa-su', 'Lisa Su', 'consequential_leader', 'active', 'Amendment §8.3 launch roster (Lane C, Compute and technology platforms).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-cl-satya-nadella', 'Satya Nadella', 'consequential_leader', 'active', 'Amendment §8.3 launch roster (Lane C, Compute and technology platforms).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-cl-sundar-pichai', 'Sundar Pichai', 'consequential_leader', 'active', 'Amendment §8.3 launch roster (Lane C, Compute and technology platforms).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-cl-mark-zuckerberg', 'Mark Zuckerberg', 'consequential_leader', 'active', 'Amendment §8.3 launch roster (Lane C, Compute and technology platforms).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-cl-andy-jassy', 'Andy Jassy', 'consequential_leader', 'active', 'Amendment §8.3 launch roster (Lane C, Compute and technology platforms).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-cl-elon-musk', 'Elon Musk', 'consequential_leader', 'active', 'Amendment §8.3 launch roster (Lane C, Compute and technology platforms).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-cl-alex-karp', 'Alex Karp', 'consequential_leader', 'active', 'Amendment §8.3 launch roster (Lane C, Enterprise AI, capital allocation, and crypto).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-cl-gavin-baker', 'Gavin Baker', 'consequential_leader', 'active', 'Amendment §8.3 launch roster (Lane C, Enterprise AI, capital allocation, and crypto).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-cl-brad-gerstner', 'Brad Gerstner', 'consequential_leader', 'active', 'Amendment §8.3 launch roster (Lane C, Enterprise AI, capital allocation, and crypto).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-cl-brian-armstrong', 'Brian Armstrong', 'consequential_leader', 'active', 'Amendment §8.3 launch roster (Lane C, Enterprise AI, capital allocation, and crypto).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-person-cl-vitalik-buterin', 'Vitalik Buterin', 'consequential_leader', 'active', 'Amendment §8.3 launch roster (Lane C, Enterprise AI, capital allocation, and crypto).', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00');

INSERT INTO ke_person_aliases (alias_id, person_id, alias, alias_type, created_at)
VALUES
    ('ke-alias-mohammed-el-erian', 'ke-person-mv-mohamed-el-erian', 'Mohammed El-Erian', 'spelling_variant', '2026-07-16T00:00:00+00:00');

-- ---------------------------------------------------------------------------
-- Persisted demoted/ambiguous queue tier (report's fold-in item 5).
--
-- ke_queue_snapshots.section has a fixed CHECK(section IN (...)) enumerating six
-- values; SQLite cannot add a value to an existing CHECK constraint without
-- recreating the table, which would not be an additive change (AD-5 permits only
-- CREATE TABLE/INDEX IF NOT EXISTS + seed INSERTs). A parallel table keyed the same
-- way as ke_queue_snapshots (queue_date + entity) avoids that recreation while
-- still giving the demoted/ambiguous tier a persisted per-scan record: scan_run
-- writes here what it showed, recompute-and-superseded per queue_date on every
-- scan, the same C2 semantics as the six existing sections. No rank_position
-- column: §8.3 defines this tier as uncapped and unranked (sorted by entity_id for
-- display, per scan_orchestrator.py's existing read-time composition), so there is
-- no ranking fact to persist.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ke_queue_snapshot_demoted (
    snapshot_id TEXT PRIMARY KEY,
    queue_date TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    explanation TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    CHECK (entity_type IN ('media_item', 'scheduled_event')),
    UNIQUE (queue_date, entity_type, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_ke_queue_snapshot_demoted_date
ON ke_queue_snapshot_demoted (queue_date);
