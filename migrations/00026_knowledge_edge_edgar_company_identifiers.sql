-- P-KE-3A: SEC EDGAR company identifiers for the D-PO-019 earnings-coverage roster
-- (docs/knowledge_edge/PHASE0_ROSTER.md), feeding
-- src/personalos/rails/knowledge_edge/earnings_calendar.py's per-company submissions
-- polling. Purely additive per PHASE0_ARCHITECTURE_DECISIONS.md AD-5: one new
-- CREATE TABLE plus reference-data INSERTs only -- no ALTER/DROP on any existing
-- table (ke_companies/ke_company_identifiers, both created by migration 00017,
-- are read here, never altered).
--
-- Provenance (single authority for every row below): the Conductor-verified figures
-- supplied for this packet, sourced from SEC's own `company_tickers.json`
-- (data.sec.gov), fetched 2026-07-17 with the approved
-- `PERSONALOS_RAIL_KE_EDGAR_USER_AGENT` identifying header. Zero network requests
-- were made to produce this migration file itself -- the CIK values below were
-- supplied pre-verified, not fetched by this packet.
--
-- Two data points per company were supplied and are recorded here: CIK (a stable
-- SEC regulatory identifier) and, for exactly two companies, SEC's own registered
-- entity title where it differs from the roster's own display name (Strategy /
-- "Strategy Inc"; Cipher Mining / "Cipher Digital Inc."). Per this packet's own
-- no-training-data-recall discipline (the same discipline PHASE0_ROSTER.md's own
-- header states), `sec_entity_title` is populated ONLY for those two companies --
-- the two the Conductor explicitly supplied verbatim. It is deliberately left NULL
-- for the other 19 confirmed-CIK companies: their SEC-registered titles were not
-- independently supplied to this packet, and guessing a plausible-looking title
-- from training-data recall (e.g. assuming "Apple Inc.") is exactly the failure
-- mode this project's own house discipline forbids. A future supervised smoke
-- (docs/knowledge_edge/PACKET_3A_EARNINGS_SUPERVISED_SMOKE.md) or a dedicated
-- `company_tickers.json` re-confirmation is expected to backfill the remaining 19
-- titles; this migration does not invent them.
--
-- Keel Infrastructure (`ke-company-keel-infrastructure`, wgmi_candidate_pool rank 4)
-- has no ticker and no CIK in the supplied data (PHASE0_ROSTER.md §3.3 already notes
-- no ticker was ever seeded for this row for the same reason). It gets a row here
-- with `identifier_status='tbc'` and every EDGAR-specific column NULL -- present in
-- the table (so a caller iterating "every roster company's EDGAR status" sees it
-- explicitly, not as a silent absence) but not usable by the adapter, which refuses
-- to poll any company whose row is not `identifier_status='confirmed'`.
--
-- `ke_company_identifiers` (migration 00017) already has an `identifier_type='cik'`
-- slot in its CHECK constraint that migration never populated -- amendment §9.3's own
-- generic "CIK or equivalent regulatory identifier" required field. This migration
-- fills that pre-existing slot for the 21 companies with a known CIK (ordinary
-- additive INSERT, no schema change), keeping the *generic* registry in
-- `ke_company_identifiers` and the *EDGAR-adapter-specific* bundle (title, filer form
-- family, confirmed/tbc gate) in the new `ke_company_edgar_identifiers` table below --
-- the two are not redundant: one is the amendment's required generic field, the other
-- is this adapter's own lookup table.

CREATE TABLE IF NOT EXISTS ke_company_edgar_identifiers (
    company_id TEXT PRIMARY KEY,
    cik TEXT,
    sec_entity_title TEXT,
    sec_ticker TEXT,
    filer_form_family TEXT,
    identifier_status TEXT NOT NULL,
    verified_as_of_date TEXT,
    source TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES ke_companies (company_id) ON DELETE RESTRICT,
    CHECK (identifier_status IN ('confirmed', 'tbc')),
    -- A 'confirmed' row must carry a CIK; a 'tbc' row (Keel) carries none. This is the
    -- gate earnings_calendar.py's per-company admission check reads directly.
    CHECK (identifier_status = 'tbc' OR cik IS NOT NULL),
    CHECK (filer_form_family IS NULL OR filer_form_family IN ('us_domestic', 'foreign_private_issuer')),
    CHECK (cik IS NULL OR length(cik) = 10)
);

CREATE INDEX IF NOT EXISTS idx_ke_company_edgar_identifiers_status
ON ke_company_edgar_identifiers (identifier_status);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ke_company_edgar_identifiers_cik
ON ke_company_edgar_identifiers (cik)
WHERE cik IS NOT NULL;

-- ---------------------------------------------------------------------------
-- Seed: SEC company_tickers.json-derived CIKs, Conductor-verified 2026-07-17.
-- Group A (nasdaq100_top10) + Group B (crypto_native_top3): all 13 roster_status=
-- 'confirmed' companies get a confirmed EDGAR identifier row here.
-- Group C (wgmi_candidate_pool): all nine candidate-pool companies ALSO get a
-- confirmed EDGAR identifier row (the Conductor verified CIKs for the full
-- candidate pool, not just a pre-picked final five -- see PHASE0_ROSTER.md §3.3's
-- "final five TBC" framing). identifier_status='confirmed' here describes the EDGAR
-- identifier lookup only; it is independent of, and must not be read as overriding,
-- ke_companies.roster_status='candidate' for these nine rows -- the roster
-- confirmation gate (which five of nine make the final cut) is untouched by this
-- migration and stays a future Conductor decision. Keel Infrastructure is the sole
-- exception: identifier_status='tbc', no CIK supplied.
-- ---------------------------------------------------------------------------

INSERT INTO ke_company_edgar_identifiers (
    company_id, cik, sec_entity_title, sec_ticker, filer_form_family,
    identifier_status, verified_as_of_date, source, notes, created_at, updated_at
)
VALUES
    ('ke-company-nvda', '0001045810', NULL, 'NVDA', 'us_domestic', 'confirmed', '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-company-aapl', '0000320193', NULL, 'AAPL', 'us_domestic', 'confirmed', '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-company-googl', '0001652044', NULL, 'GOOGL', 'us_domestic', 'confirmed', '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-company-msft', '0000789019', NULL, 'MSFT', 'us_domestic', 'confirmed', '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-company-amzn', '0001018724', NULL, 'AMZN', 'us_domestic', 'confirmed', '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-company-avgo', '0001730168', NULL, 'AVGO', 'us_domestic', 'confirmed', '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-company-meta', '0001326801', NULL, 'META', 'us_domestic', 'confirmed', '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-company-tsla', '0001318605', NULL, 'TSLA', 'us_domestic', 'confirmed', '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    (
        'ke-company-asml', '0000937966', NULL, 'ASML', 'foreign_private_issuer', 'confirmed', '2026-07-17',
        'SEC company_tickers.json, Conductor-verified 2026-07-17',
        'Foreign private issuer: files Forms 20-F/6-K, not 10-K/10-Q, per PHASE0_ROSTER.md §3.1 filing-mechanism note. earnings_calendar.py must use the 20-F/6-K form family for this company.',
        '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'
    ),
    ('ke-company-nflx', '0001065280', NULL, 'NFLX', 'us_domestic', 'confirmed', '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-company-coin', '0001679788', NULL, 'COIN', 'us_domestic', 'confirmed', '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    (
        'ke-company-mstr', '0001050446', 'Strategy Inc', 'MSTR', 'us_domestic', 'confirmed', '2026-07-17',
        'SEC company_tickers.json, Conductor-verified 2026-07-17',
        'SEC-registered entity title differs from the roster display name ("Strategy (MicroStrategy)") -- a rename, recorded as data, not corrected. See migration header.',
        '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'
    ),
    ('ke-company-crcl', '0001876042', NULL, 'CRCL', 'us_domestic', 'confirmed', '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    (
        'ke-company-cifr', '0001819989', 'Cipher Digital Inc.', 'CIFR', 'us_domestic', 'confirmed', '2026-07-17',
        'SEC company_tickers.json, Conductor-verified 2026-07-17',
        'SEC-registered entity title differs from the roster display name ("Cipher Mining") -- a rename, recorded as data, not corrected. See migration header.',
        '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'
    ),
    ('ke-company-hut', '0001964789', NULL, 'HUT', 'us_domestic', 'confirmed', '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-company-iren', '0001878848', NULL, 'IREN', 'us_domestic', 'confirmed', '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    (
        'ke-company-keel-infrastructure', NULL, NULL, NULL, NULL, 'tbc', NULL, '',
        'No ticker and no CIK supplied in the Conductor-verified figures for this packet -- consistent with PHASE0_ROSTER.md §3.3, which already notes no ticker was seeded for this WGMI candidate-pool row either. earnings_calendar.py refuses to poll this company until a future Conductor confirmation supplies a CIK.',
        '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'
    ),
    ('ke-company-mara', '0001507605', NULL, 'MARA', 'us_domestic', 'confirmed', '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-company-hive', '0001720424', NULL, 'HIVE', 'us_domestic', 'confirmed', '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-company-clsk', '0000827876', NULL, 'CLSK', 'us_domestic', 'confirmed', '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-company-riot', '0001167419', NULL, 'RIOT', 'us_domestic', 'confirmed', '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-company-btdr', '0001899123', NULL, 'BTDR', 'us_domestic', 'confirmed', '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00');

-- ---------------------------------------------------------------------------
-- Seed: back-fill the generic `ke_company_identifiers` CIK slot (identifier_type=
-- 'cik') migration 00017 left empty for every company, using the same 21 CIKs above.
-- Same provenance, same verified_as_of_date. No row for Keel Infrastructure, same
-- reasoning as its ticker's own absence in migration 00017.
-- ---------------------------------------------------------------------------

INSERT INTO ke_company_identifiers (
    identifier_id, company_id, identifier_type, identifier_value, exchange,
    verified_as_of_date, provenance, created_at, updated_at
)
VALUES
    ('ke-ident-nvda-cik', 'ke-company-nvda', 'cik', '0001045810', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-aapl-cik', 'ke-company-aapl', 'cik', '0000320193', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-googl-cik', 'ke-company-googl', 'cik', '0001652044', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-msft-cik', 'ke-company-msft', 'cik', '0000789019', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-amzn-cik', 'ke-company-amzn', 'cik', '0001018724', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-avgo-cik', 'ke-company-avgo', 'cik', '0001730168', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-meta-cik', 'ke-company-meta', 'cik', '0001326801', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-tsla-cik', 'ke-company-tsla', 'cik', '0001318605', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-asml-cik', 'ke-company-asml', 'cik', '0000937966', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-nflx-cik', 'ke-company-nflx', 'cik', '0001065280', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-coin-cik', 'ke-company-coin', 'cik', '0001679788', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-mstr-cik', 'ke-company-mstr', 'cik', '0001050446', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-crcl-cik', 'ke-company-crcl', 'cik', '0001876042', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-cifr-cik', 'ke-company-cifr', 'cik', '0001819989', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-hut-cik', 'ke-company-hut', 'cik', '0001964789', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-iren-cik', 'ke-company-iren', 'cik', '0001878848', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-mara-cik', 'ke-company-mara', 'cik', '0001507605', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-hive-cik', 'ke-company-hive', 'cik', '0001720424', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-clsk-cik', 'ke-company-clsk', 'cik', '0000827876', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-riot-cik', 'ke-company-riot', 'cik', '0001167419', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'),
    ('ke-ident-btdr-cik', 'ke-company-btdr', 'cik', '0001899123', NULL, '2026-07-17', 'SEC company_tickers.json, Conductor-verified 2026-07-17', '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00');

-- ---------------------------------------------------------------------------
-- Seed: the single ke_sources / ke_source_endpoints row pair representing the
-- roster-wide EDGAR submissions mechanism itself. One source, not one per company
-- -- the per-company CIK targeting lives in ke_company_edgar_identifiers above, not
-- in a per-company source row, mirroring how youtube.py's single search-source row
-- serves every person-search query rather than seeding one row per tracked person.
-- status='trial' and endpoint_verified_at/verified_by stay NULL, exactly like
-- migration 00023's 9 Lane A feeds: seeding the endpoint is not the same as
-- verifying it. See docs/knowledge_edge/PACKET_3A_EARNINGS_SUPERVISED_SMOKE.md.
--
-- source_type='calendar_provider', NOT 'sec_edgar', even though the underlying
-- vendor is EDGAR in both cases: scan_orchestrator.py (P-KE-1B) already routes by
-- ROLE, not vendor -- `_EVENT_SOURCE_TYPES = {'calendar_provider'}` goes to
-- `EarningsEventAdapter.fetch_events` (creates new events, this packet's contract),
-- while `_FILING_SOURCE_TYPES = {'sec_edgar'}` goes to `FilingsAdapter.fetch_filings`
-- (only enriches an already-discovered event, P-KE-3B's future sec_edgar.py). This
-- packet's earnings_calendar.py implements the former, so this row must carry the
-- source_type that role already expects, even though this packet does not itself
-- wire scan_orchestrator.py to a live adapter (see earnings_calendar.py's own
-- module docstring for that "structurally reachable, not actually reached" posture).
-- ---------------------------------------------------------------------------

INSERT INTO ke_sources (
    source_id, source_type, lane, topic_group, name, status,
    cadence_expectation_days, notes, created_at, updated_at
)
VALUES (
    'ke-source-sec-edgar-submissions',
    'calendar_provider',
    'earnings_events',
    'roster_earnings_coverage',
    'SEC EDGAR submissions API (D-PO-019 roster earnings-calendar mechanism)',
    'trial',
    NULL,
    'Single mechanism source for the whole D-PO-019 roster (PHASE0_ROSTER.md) -- per-company CIK targeting is read from ke_company_edgar_identifiers, not from a per-company source row. status=trial until the Packet 3A supervised smoke (PACKET_3A_EARNINGS_SUPERVISED_SMOKE.md) records a verification, exactly like migration 00023''s Lane A feeds.',
    '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'
);

INSERT INTO ke_source_endpoints (
    source_endpoint_id, source_id, endpoint_type, url, is_primary, status,
    created_at, updated_at
)
VALUES (
    'ke-source-sec-edgar-submissions-endpoint',
    'ke-source-sec-edgar-submissions',
    'api_endpoint',
    'https://data.sec.gov/submissions/',
    1,
    'active',
    '2026-07-17T00:00:00+00:00', '2026-07-17T00:00:00+00:00'
);
