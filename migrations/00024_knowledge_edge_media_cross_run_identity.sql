-- P-KE-2A iteration 2 (Conductor scope amendment, 2026-07-16): cross-run
-- corrected-episode identity for ke_media_items (amendment §8.1 "recognize
-- corrected/reissued episodes without producing duplicates", §11.4). Purely
-- additive: two nullable ADD COLUMNs plus a lookup index, per
-- PHASE0_ARCHITECTURE_DECISIONS AD-5. No table is created or dropped, no
-- existing column is altered or removed.
--
-- Phase 1 (P-KE-1B, orchestrator gap 2) deliberately deferred persisting these
-- two adapter-declared identifiers, so deterministic dedup evidence
-- (engine/dedup.py's shared_feed_guid / same_underlying_id_title_change rules)
-- could only be evaluated within one scan run's freshly-fetched batch, never
-- against a media item persisted by an earlier run. A live feed correcting an
-- episode's GUID days or weeks after original publication -- the case §8.1
-- explicitly calls out -- would previously read as a brand-new episode on the
-- next scan and produce a duplicate row instead of correcting the original one.
--
-- feed_guid and underlying_id mirror the identically-named fields already on
-- DiscoveredMediaItem (adapters/contracts.py) and the keys engine/dedup.py's
-- find_duplicate_evidence already expects on a "candidate" mapping; persisting
-- them lets scan_orchestrator._persist_media_batch look an incoming item's
-- underlying_id up against every previously-persisted row for its source, not
-- just the current batch, per the Conductor's iteration-2 scope amendment.
ALTER TABLE ke_media_items ADD COLUMN feed_guid TEXT;
ALTER TABLE ke_media_items ADD COLUMN underlying_id TEXT;

CREATE INDEX IF NOT EXISTS idx_ke_media_items_source_underlying
ON ke_media_items (source_id, underlying_id);
