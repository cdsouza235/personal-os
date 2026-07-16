-- P-KE-2A: Knowledge Edge Lane A (curated podcasts) endpoint data (amendment §8.1,
-- §10.2/10.3). Purely additive: two nullable ADD COLUMNs on ke_source_endpoints plus
-- 9 new endpoint rows for the 9 Lane A sources 00022 seeded with "Endpoint: TBC" (that
-- migration created no ke_source_endpoints row for any of them, since url is NOT NULL
-- and no endpoint was known at the time). No ALTER/DROP on any other table, no changes
-- to ke_sources -- every one of the 9 sources stays status='trial', exactly as 00022
-- left it (PHASE0_ARCHITECTURE_DECISIONS AD-5).
--
-- Endpoints below were resolved 2026-07-16 via the Apple podcast directory and are
-- copied verbatim from this packet's own work packet -- nothing invented, no endpoint
-- beyond these 9. Explicit Conductor acknowledgment of this resolution is still
-- PENDING at this packet's own gate (see docs/knowledge_edge/
-- PACKET_2A_PODCAST_SUPERVISED_SMOKE.md), which is exactly why status stays 'trial'
-- here rather than flipping to 'active': seeding a URL is not the same as verifying
-- it. endpoint_verified_at/verified_by are new, nullable columns on
-- ke_source_endpoints -- both start NULL for every row (existing rows via the ALTER,
-- and these 9 new rows via their own INSERT) and are populated only by the
-- Conductor-supervised smoke procedure that document describes, one feed at a time.
--
-- Why this is safe to merge with live network code already present in this same
-- packet (src/personalos/rails/knowledge_edge/podcasts.py): that adapter's own gating
-- refuses to fetch from any source whose ke_sources.status is not 'active' or whose
-- endpoint has no endpoint_verified_at recorded, independent of feature mode. Seeding
-- the URL here does not, by itself, make anything reachable.

ALTER TABLE ke_source_endpoints ADD COLUMN endpoint_verified_at TEXT;
ALTER TABLE ke_source_endpoints ADD COLUMN verified_by TEXT;

INSERT INTO ke_source_endpoints (
    source_endpoint_id, source_id, endpoint_type, url, is_primary, status,
    endpoint_verified_at, verified_by, created_at, updated_at
)
VALUES
    ('ke-endpoint-dwarkesh-podcast', 'ke-source-dwarkesh-podcast', 'rss', 'https://apple.dwarkesh-podcast.workers.dev/feed.rss', 1, 'active', NULL, NULL, '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-endpoint-latent-space', 'ke-source-latent-space', 'rss', 'https://api.substack.com/feed/podcast/1084089.rss', 1, 'active', NULL, NULL, '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-endpoint-no-priors', 'ke-source-no-priors', 'rss', 'https://feeds.megaphone.fm/nopriors', 1, 'active', NULL, NULL, '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-endpoint-unchained', 'ke-source-unchained', 'rss', 'https://feeds.megaphone.fm/LSHML4761942757', 1, 'active', NULL, NULL, '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-endpoint-bankless', 'ke-source-bankless', 'rss', 'https://feeds.flightcast.com/p83fuj0y0u58o82l41xei7zo.xml', 1, 'active', NULL, NULL, '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-endpoint-forward-guidance', 'ke-source-forward-guidance', 'rss', 'https://feeds.megaphone.fm/forwardguidance', 1, 'active', NULL, NULL, '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-endpoint-odd-lots', 'ke-source-odd-lots', 'rss', 'https://www.omnycontent.com/d/playlist/e73c998e-6e60-432f-8610-ae210140c5b1/8a94442e-5a74-4fa2-8b8d-ae27003a8d6b/982f5071-765c-403d-969d-ae27003a8d83/podcast.rss', 1, 'active', NULL, NULL, '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-endpoint-macro-voices', 'ke-source-macro-voices', 'rss', 'https://feed.podbean.com/macrovoices/feed.xml', 1, 'active', NULL, NULL, '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-endpoint-compound-and-friends', 'ke-source-compound-and-friends', 'rss', 'https://feeds.megaphone.fm/TCP4771071679', 1, 'active', NULL, NULL, '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00');
