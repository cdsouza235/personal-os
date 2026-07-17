-- P-KE-2F: Lane B/C source seeding -- the §10.3 launch video/network channel class
-- ("CNBC Television and the selected tracked-show feeds; Bloomberg Television and
-- Bloomberg Technology official uploads; Yahoo Finance official uploads") plus the
-- `youtube.py` person-search mechanism's own `ke_sources` row
-- (`DEFAULT_PERSON_SEARCH_SOURCE_ID`, `ke-source-youtube-person-search`). Purely
-- additive INSERTs per PHASE0_ARCHITECTURE_DECISIONS.md AD-5: no ALTER/DROP on any
-- existing table, and nothing beyond the five rows this packet's own brief scopes
-- (four youtube_channel sources + their channel_id endpoints, one
-- person_search_provider source + its api_endpoint). This is exactly the two
-- deliberate gaps `rails/knowledge_edge/youtube.py`'s own module docstring names as
-- "no channel-ID seeding in this packet" and
-- `docs/knowledge_edge/PACKET_2B_YOUTUBE_SUPERVISED_SMOKE.md` Sec0 names as its own
-- unsatisfiable prerequisite -- both close here.
--
-- Channel identities below (handle, channel_id, subscriber count used only to
-- confirm identity) were supplied Conductor-verified 2026-07-17 via YouTube
-- `channels.list` `forHandle` lookups (1-unit calls each) for exactly the four §10.3
-- channels this packet's own scope names -- CNBC Television, Bloomberg Television
-- (`@markets`, not `@BloombergTelevision` -- the handle the Conductor's lookup
-- actually resolved), Bloomberg Technology, Yahoo Finance. Nothing invented, no
-- channel beyond these four: §10.3's other classes (company/IR/executive channels,
-- conference-organizer channels, government/central-bank channels for the
-- role-based watches) are explicitly named FUTURE additions in this packet's own
-- brief, each requiring its own verify+acknowledge cycle before it is seeded --
-- exactly the same "additional networks or channels require source verification and
-- roster approval" rule §10.3 itself states.
--
-- Explicit Conductor ACKNOWLEDGMENT of these four channel identities (as distinct
-- from the verification lookup that resolved them) is still PENDING at this
-- packet's own gate -- the same posture migration 00023's 9 Lane A feed URLs shipped
-- under (see that migration's own header) and the same posture
-- `PHASE0_PROVIDERS_AND_ACCESS.md` §6 requires ("any addition later ... requires an
-- explicit Conductor acknowledgment of the specific added source before it is
-- fetched from"). That is exactly why every `ke_sources` row below stays
-- `status='trial'` rather than `'active'`, and every `ke_source_endpoints` row's
-- `endpoint_verified_at`/`verified_by` stays `NULL`: seeding an endpoint is not the
-- same as verifying it, and verifying a channel's identity (this migration) is not
-- the same as the Conductor acknowledgment that admits it to live fetching (a later,
-- separate supervised-smoke step -- see
-- docs/knowledge_edge/PACKET_2F_YOUTUBE_LANE_BC_SUPERVISED_SMOKE.md).
--
-- Endpoint shape, matching `youtube.py`'s own gating exactly (module docstring +
-- `LiveYoutubeChannelAdapter._evaluate_gates`'s comment on `channel_id`-type
-- endpoints, SOURCE_ENDPOINT_TYPES' pre-existing 'channel_id' type from migration
-- 00017): each channel's `ke_source_endpoints.url` holds the RAW channel_id string
-- (e.g. `UCrp_UI8XtuYfpiqluWLD7Lw`), NOT the full RSS URL -- the adapter always
-- constructs `https://www.youtube.com/feeds/videos.xml?channel_id=<ID>` itself
-- against YouTube's own host from that raw identifier, never trusting an
-- arbitrary stored URL the way `podcasts.py` trusts a stored feed URL. Storing the
-- full RSS URL as `url` here (matching a Lane A `rss`-type endpoint's shape) would
-- silently defeat `_resolve_primary_channel_endpoint`'s `endpoint_type == 'channel_id'`
-- filter -- no active endpoint would ever be found, and the adapter would refuse
-- every fetch with `STATUS_CHANNEL_BLOCKED_NO_ENDPOINT` even after a future
-- Conductor flip to `status='active'`. The full RSS URL each row's `notes` documents
-- is exactly `https://www.youtube.com/feeds/videos.xml?channel_id=<that row's own
-- channel_id>` -- restated in prose only, never a second stored column, so there is
-- only ever one place (`url`) a future reader or the adapter itself needs to trust.
--
-- source_type='youtube_channel' for the four channels (existing CHECK-constrained
-- value, migration 00017); source_type='person_search_provider' for the search row
-- (also pre-existing), matching `DEFAULT_PERSON_SEARCH_SOURCE_ID` exactly so
-- `LiveYoutubePersonSearchClient`'s default `source_id` constructor argument
-- resolves this row with no adapter change.
--
-- lane='market_voices' for all five rows (four channels + the search source): §10.3's
-- three general financial-media/network channels (CNBC, Bloomberg TV, Bloomberg
-- Technology, Yahoo Finance) are precisely the "official network uploads" class
-- §8.2's own Market Voices requirements list names, while §8.3's Consequential
-- Leaders P0 sourcing draws on the classes this packet does NOT seed yet --
-- official government/central-bank channels and official company/IR/executive
-- channels, both explicitly deferred as future additions above. The person-search
-- source gets the same lane for the same reason `tests/test_rails_knowledge_edge_
-- youtube.py`'s own `_seed_search_source` test fixture already defaults to
-- (`lane="market_voices"`): `scan_orchestrator.py` reads `source["lane"]` once per
-- source to assign a discovered item's queue section
-- (`engine.ranking.assign_queue_section`), independent of which specific tracked
-- person a person-search result names -- and neither `LiveYoutubeChannelAdapter` nor
-- `LiveYoutubePersonSearchClient` is wired into `scan_orchestrator.py` by any packet
-- yet (`youtube.py`'s own module docstring: "structurally reachable, not actually
-- reached"), so this lane value is dormant configuration today, not a live routing
-- decision this migration is making irreversibly. A future packet that wires either
-- mechanism into the live orchestrator and finds a single fixed lane per source too
-- coarse for a Consequential-Leaders appearance surfacing on one of these four
-- general-news channels should revisit this as a named design gap, not something
-- this migration silently resolves by picking a lane per discovered item.
--
-- topic_group is left NULL for all five rows: unlike Lane A's topic-scoped podcasts
-- ('ai'/'crypto'/'markets', migration 00022), these four networks and the
-- cross-cutting search mechanism are not bound to one topic -- inventing a
-- topic_group value here would be a guess, not a fact any seed authority supplied.

INSERT INTO ke_sources (
    source_id, source_type, lane, topic_group, name, status,
    cadence_expectation_days, notes, created_at, updated_at
)
VALUES
    (
        'ke-source-cnbc-television', 'youtube_channel', 'market_voices', NULL,
        'CNBC Television', 'trial', NULL,
        'Amendment §10.3 launch video/network allowlist. Channel identity Conductor-verified 2026-07-17 via YouTube channels.list forHandle=@CNBCtelevision (channel_id UCrp_UI8XtuYfpiqluWLD7Lw, 3.38M subscribers at verification time, used only to confirm identity). status=trial, endpoint unverified: explicit Conductor acknowledgment of this specific addition is still PENDING at this packet''s own gate (PHASE0_PROVIDERS_AND_ACCESS.md §6) -- see docs/knowledge_edge/PACKET_2F_YOUTUBE_LANE_BC_SUPERVISED_SMOKE.md.',
        '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'
    ),
    (
        'ke-source-bloomberg-television', 'youtube_channel', 'market_voices', NULL,
        'Bloomberg Television', 'trial', NULL,
        'Amendment §10.3 launch video/network allowlist. Channel identity Conductor-verified 2026-07-17 via YouTube channels.list forHandle=@markets (channel_id UCIALMKvObZNtJ6AmdCLP7Lg, 3.21M subscribers at verification time, used only to confirm identity) -- Bloomberg Television''s current handle is @markets, not @BloombergTelevision; recorded as the Conductor supplied it, not corrected against a guessed handle. status=trial, endpoint unverified: explicit Conductor acknowledgment of this specific addition is still PENDING at this packet''s own gate (PHASE0_PROVIDERS_AND_ACCESS.md §6) -- see docs/knowledge_edge/PACKET_2F_YOUTUBE_LANE_BC_SUPERVISED_SMOKE.md.',
        '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'
    ),
    (
        'ke-source-bloomberg-technology', 'youtube_channel', 'market_voices', NULL,
        'Bloomberg Technology', 'trial', NULL,
        'Amendment §10.3 launch video/network allowlist. Channel identity Conductor-verified 2026-07-17 via YouTube channels.list forHandle=@BloombergTechnology (channel_id UCrM7B7SL_g1edFOnmj-SDKg, 731K subscribers at verification time, used only to confirm identity). status=trial, endpoint unverified: explicit Conductor acknowledgment of this specific addition is still PENDING at this packet''s own gate (PHASE0_PROVIDERS_AND_ACCESS.md §6) -- see docs/knowledge_edge/PACKET_2F_YOUTUBE_LANE_BC_SUPERVISED_SMOKE.md.',
        '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'
    ),
    (
        'ke-source-yahoo-finance', 'youtube_channel', 'market_voices', NULL,
        'Yahoo Finance', 'trial', NULL,
        'Amendment §10.3 launch video/network allowlist. Channel identity Conductor-verified 2026-07-17 via YouTube channels.list forHandle=@YahooFinance (channel_id UCEAZeUIeJs0IjQiqTCdVSIg, 1.51M subscribers at verification time, used only to confirm identity). status=trial, endpoint unverified: explicit Conductor acknowledgment of this specific addition is still PENDING at this packet''s own gate (PHASE0_PROVIDERS_AND_ACCESS.md §6) -- see docs/knowledge_edge/PACKET_2F_YOUTUBE_LANE_BC_SUPERVISED_SMOKE.md.',
        '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'
    ),
    (
        'ke-source-youtube-person-search', 'person_search_provider', 'market_voices', NULL,
        'YouTube Data API search.list (Lane B/C person search, D-YT option 1)', 'trial', NULL,
        'D-YT option 1 (amendment §10.4, PHASE0_PROVIDERS_AND_ACCESS.md §4). Single mechanism source shared by every Lane B/C tracked person''s search -- matches rails/knowledge_edge/youtube.py''s DEFAULT_PERSON_SEARCH_SOURCE_ID exactly, so LiveYoutubePersonSearchClient resolves this row with no adapter change. status=trial, endpoint unverified: the search.list mechanism itself was already live-fire verified (one call, q=Mohamed El-Erian, HTTP 200, 5 on-target items -- see audits/knowledge-edge/2026-07-16-packet-2a-podcast-smoke-transcript.md, "YouTube verification" section), but that call predates this row''s own existence and is not a substitute for the Conductor acknowledgment this specific source row still needs before status flips to active -- see docs/knowledge_edge/PACKET_2F_YOUTUBE_LANE_BC_SUPERVISED_SMOKE.md.',
        '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'
    );

INSERT INTO ke_source_endpoints (
    source_endpoint_id, source_id, endpoint_type, url, is_primary, status,
    endpoint_verified_at, verified_by, created_at, updated_at
)
VALUES
    (
        'ke-endpoint-cnbc-television-channel', 'ke-source-cnbc-television', 'channel_id',
        'UCrp_UI8XtuYfpiqluWLD7Lw', 1, 'active', NULL, NULL,
        '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'
    ),
    (
        'ke-endpoint-bloomberg-television-channel', 'ke-source-bloomberg-television', 'channel_id',
        'UCIALMKvObZNtJ6AmdCLP7Lg', 1, 'active', NULL, NULL,
        '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'
    ),
    (
        'ke-endpoint-bloomberg-technology-channel', 'ke-source-bloomberg-technology', 'channel_id',
        'UCrM7B7SL_g1edFOnmj-SDKg', 1, 'active', NULL, NULL,
        '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'
    ),
    (
        'ke-endpoint-yahoo-finance-channel', 'ke-source-yahoo-finance', 'channel_id',
        'UCEAZeUIeJs0IjQiqTCdVSIg', 1, 'active', NULL, NULL,
        '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'
    ),
    (
        'ke-endpoint-youtube-person-search', 'ke-source-youtube-person-search', 'api_endpoint',
        'https://www.googleapis.com/youtube/v3/search', 1, 'active', NULL, NULL,
        '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'
    );
