-- P-KE-1A: Knowledge Edge registries -- source, person, role, role_occupancy,
-- affiliation, company, company_identifier, topic (amendment §13.1, §8.1-8.3, §9.3).
-- Purely additive CREATE TABLE per PHASE0_ARCHITECTURE_DECISIONS.md AD-5; no ALTER/DROP
-- on any existing table. Seed INSERTs below are reference data only, drawn from exactly
-- two ratified authorities:
--   1. governance/living/agent-writable/DECISIONS.md D-PO-018 item 5 (launch role
--      appendix: 5 role seats, occupants, effective dates).
--   2. docs/knowledge_edge/PHASE0_ROSTER.md (D-PO-019 earnings-coverage company roster).
-- No podcast/channel/person-roster seed rows land in this migration: the PRD's §8.1/8.2/
-- 8.3 named rosters (podcasts, Market Voices, Consequential Leaders individuals) are not
-- among the two seed authorities named for this packet, so those registries are created
-- here as empty, schema-validated tables only (see HANDOFF.md for the disposition note).

CREATE TABLE IF NOT EXISTS ke_sources (
    source_id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    lane TEXT NOT NULL,
    topic_group TEXT,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    cadence_expectation_days INTEGER,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        source_type IN (
            'podcast_feed',
            'youtube_channel',
            'network_program',
            'ir_page',
            'calendar_provider',
            'sec_edgar',
            'person_search_provider',
            'manual_link'
        )
    ),
    CHECK (
        lane IN (
            'curated_podcasts',
            'market_voices',
            'consequential_leaders',
            'earnings_events'
        )
    ),
    CHECK (status IN ('active', 'trial', 'paused', 'retired')),
    CHECK (cadence_expectation_days IS NULL OR cadence_expectation_days > 0)
);

CREATE TABLE IF NOT EXISTS ke_source_endpoints (
    source_endpoint_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    endpoint_type TEXT NOT NULL,
    url TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES ke_sources (source_id) ON DELETE RESTRICT,
    CHECK (endpoint_type IN ('rss', 'atom', 'channel_id', 'api_endpoint', 'page_url')),
    CHECK (is_primary IN (0, 1)),
    CHECK (status IN ('active', 'retired')),
    UNIQUE (source_id, url)
);

CREATE TABLE IF NOT EXISTS ke_people (
    person_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (category IN ('market_voice', 'consequential_leader', 'role_occupant')),
    CHECK (status IN ('active', 'retired'))
);

CREATE TABLE IF NOT EXISTS ke_person_aliases (
    alias_id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    alias_type TEXT NOT NULL DEFAULT 'exact',
    created_at TEXT NOT NULL,
    FOREIGN KEY (person_id) REFERENCES ke_people (person_id) ON DELETE RESTRICT,
    CHECK (alias_type IN ('exact', 'spelling_variant')),
    UNIQUE (person_id, alias)
);

CREATE TABLE IF NOT EXISTS ke_roles (
    role_id TEXT PRIMARY KEY,
    role_name TEXT NOT NULL UNIQUE,
    role_category TEXT NOT NULL,
    roster_cap INTEGER NOT NULL DEFAULT 1,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        role_category IN (
            'government',
            'frontier_ai_lab',
            'semiconductor_platform',
            'corporate'
        )
    ),
    CHECK (roster_cap > 0)
);

-- Effective-dated role occupancy (amendment §8.3: "preserve historical occupants and
-- effective dates... not hard-code current political or corporate officeholders in
-- logic"). effective_start_date is nullable and means "occupant since before this
-- registry began tracking" (e.g. Tim Cook's own appointment date is not given by the
-- seed authority) -- it is NOT a stand-in for an unknown-but-real date. Query logic
-- (personalos.knowledge_edge.state.registries.get_role_occupant_as_of) treats a NULL
-- start as always-earliest, so a later dated occupancy correctly supersedes it.
CREATE TABLE IF NOT EXISTS ke_role_occupancies (
    occupancy_id TEXT PRIMARY KEY,
    role_id TEXT NOT NULL,
    person_id TEXT NOT NULL,
    effective_start_date TEXT,
    effective_end_date TEXT,
    date_precision TEXT NOT NULL DEFAULT 'exact',
    occupancy_source TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (role_id) REFERENCES ke_roles (role_id) ON DELETE RESTRICT,
    FOREIGN KEY (person_id) REFERENCES ke_people (person_id) ON DELETE RESTRICT,
    CHECK (date_precision IN ('exact', 'month', 'estimated', 'unknown_predates_tracking')),
    CHECK (
        effective_end_date IS NULL
        OR effective_start_date IS NULL
        OR effective_end_date > effective_start_date
    ),
    UNIQUE (role_id, person_id, effective_start_date)
);

-- Relationship to a network/outlet is an effective-dated, nullable attribute of the
-- person, not a hard-coded label (amendment §8.2).
CREATE TABLE IF NOT EXISTS ke_affiliations (
    affiliation_id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL,
    organization TEXT NOT NULL,
    title TEXT,
    effective_start_date TEXT,
    effective_end_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (person_id) REFERENCES ke_people (person_id) ON DELETE RESTRICT,
    CHECK (
        effective_end_date IS NULL
        OR effective_start_date IS NULL
        OR effective_end_date > effective_start_date
    )
);

-- Company roster (amendment §9.3 required fields + D-PO-019 roster-group provenance
-- fields from PHASE0_ROSTER.md). roster_status distinguishes a Conductor-confirmed row
-- from a candidate-pool row that has NOT been promoted -- the WGMI group (§3.3 of the
-- roster doc) is seeded as nine 'candidate' rows; nothing here silently picks the final
-- five. priority_tier (the amendment's original §9.1/§9.2 Tier A/Tier B concept) is left
-- NULL for every seeded row: the D-PO-019 roster is a separate, later-ratified universe
-- that supersedes the §9 list for launch earnings coverage (see HANDOFF.md).
CREATE TABLE IF NOT EXISTS ke_companies (
    company_id TEXT PRIMARY KEY,
    legal_name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    roster_group TEXT NOT NULL,
    roster_group_rank INTEGER,
    roster_group_rank_basis TEXT,
    roster_status TEXT NOT NULL,
    market_cap_display TEXT,
    market_cap_as_of_date TEXT,
    market_cap_source TEXT,
    fund_weight_percent REAL,
    priority_tier TEXT,
    domain_topic_tags_json TEXT NOT NULL DEFAULT '[]',
    ir_root_url TEXT,
    events_page_url TEXT,
    filings_page_url TEXT,
    fiscal_year_end TEXT,
    reporting_cadence TEXT,
    primary_reporting_timezone TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    manual_pin INTEGER NOT NULL DEFAULT 0,
    linked_theses_json TEXT NOT NULL DEFAULT '[]',
    source_verification_date TEXT,
    added_effective_date TEXT,
    removed_effective_date TEXT,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (roster_group IN ('nasdaq100_top10', 'crypto_native_top3', 'wgmi_candidate_pool')),
    CHECK (roster_group_rank IS NULL OR roster_group_rank > 0),
    CHECK (roster_group_rank_basis IS NULL OR roster_group_rank_basis IN ('market_cap', 'fund_weight')),
    CHECK (roster_status IN ('confirmed', 'candidate')),
    CHECK (priority_tier IS NULL OR priority_tier IN ('tier_a', 'tier_b')),
    CHECK (status IN ('active', 'paused', 'retired')),
    CHECK (manual_pin IN (0, 1)),
    CHECK (
        removed_effective_date IS NULL
        OR added_effective_date IS NULL
        OR removed_effective_date > added_effective_date
    )
);

CREATE TABLE IF NOT EXISTS ke_company_identifiers (
    identifier_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    identifier_type TEXT NOT NULL,
    identifier_value TEXT NOT NULL,
    exchange TEXT,
    verified_as_of_date TEXT,
    effective_end_date TEXT,
    provenance TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES ke_companies (company_id) ON DELETE RESTRICT,
    CHECK (identifier_type IN ('ticker', 'cik', 'isin')),
    UNIQUE (company_id, identifier_type, identifier_value)
);

CREATE TABLE IF NOT EXISTS ke_topics (
    topic_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    category TEXT,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ke_source_endpoints_source
ON ke_source_endpoints (source_id, status);

CREATE INDEX IF NOT EXISTS idx_ke_person_aliases_person
ON ke_person_aliases (person_id);

CREATE INDEX IF NOT EXISTS idx_ke_role_occupancies_role
ON ke_role_occupancies (role_id, effective_start_date);

CREATE INDEX IF NOT EXISTS idx_ke_affiliations_person
ON ke_affiliations (person_id, effective_start_date);

CREATE INDEX IF NOT EXISTS idx_ke_companies_roster_group
ON ke_companies (roster_group, roster_status, roster_group_rank);

CREATE INDEX IF NOT EXISTS idx_ke_company_identifiers_company
ON ke_company_identifiers (company_id, identifier_type);

-- ---------------------------------------------------------------------------
-- Seed: launch role appendix (D-PO-018 item 5, ratified 2026-07-15)
-- ---------------------------------------------------------------------------

INSERT INTO ke_roles (role_id, role_name, role_category, roster_cap, notes, created_at, updated_at)
VALUES
    ('ke-role-fed-chair', 'Federal Reserve Chair', 'government', 1, 'D-PO-018 item 5.', '2026-07-15T00:00:00+00:00', '2026-07-15T00:00:00+00:00'),
    ('ke-role-treasury-secretary', 'U.S. Treasury Secretary', 'government', 1, 'D-PO-018 item 5.', '2026-07-15T00:00:00+00:00', '2026-07-15T00:00:00+00:00'),
    ('ke-role-sec-chair', 'SEC Chair', 'government', 1, 'D-PO-018 item 5.', '2026-07-15T00:00:00+00:00', '2026-07-15T00:00:00+00:00'),
    ('ke-role-cftc-chair', 'CFTC Chair', 'government', 1, 'D-PO-018 item 5.', '2026-07-15T00:00:00+00:00', '2026-07-15T00:00:00+00:00'),
    (
        'ke-role-apple-ceo',
        'Apple CEO',
        'corporate',
        1,
        'D-PO-018 item 5. Company-head seats for OpenAI/Anthropic/DeepMind/NVIDIA/AMD were deliberately NOT created -- current holders are tracked as named Lane B/C individuals per that decision, not role seats.',
        '2026-07-15T00:00:00+00:00',
        '2026-07-15T00:00:00+00:00'
    );

INSERT INTO ke_people (person_id, display_name, category, status, notes, created_at, updated_at)
VALUES
    ('ke-person-kevin-warsh', 'Kevin Warsh', 'role_occupant', 'active', 'D-PO-018 item 5.', '2026-07-15T00:00:00+00:00', '2026-07-15T00:00:00+00:00'),
    ('ke-person-scott-bessent', 'Scott Bessent', 'role_occupant', 'active', 'D-PO-018 item 5.', '2026-07-15T00:00:00+00:00', '2026-07-15T00:00:00+00:00'),
    ('ke-person-paul-atkins', 'Paul Atkins', 'role_occupant', 'active', 'D-PO-018 item 5.', '2026-07-15T00:00:00+00:00', '2026-07-15T00:00:00+00:00'),
    ('ke-person-michael-selig', 'Michael Selig', 'role_occupant', 'active', 'D-PO-018 item 5.', '2026-07-15T00:00:00+00:00', '2026-07-15T00:00:00+00:00'),
    ('ke-person-tim-cook', 'Tim Cook', 'role_occupant', 'active', 'D-PO-018 item 5.', '2026-07-15T00:00:00+00:00', '2026-07-15T00:00:00+00:00'),
    ('ke-person-john-ternus', 'John Ternus', 'role_occupant', 'active', 'D-PO-018 item 5.', '2026-07-15T00:00:00+00:00', '2026-07-15T00:00:00+00:00');

INSERT INTO ke_role_occupancies (
    occupancy_id, role_id, person_id, effective_start_date, effective_end_date,
    date_precision, occupancy_source, notes, created_at, updated_at
)
VALUES
    (
        'ke-occ-fed-chair-warsh',
        'ke-role-fed-chair',
        'ke-person-kevin-warsh',
        '2026-05-22',
        NULL,
        'exact',
        'D-PO-018 item 5',
        'Succeeded Jerome Powell. Powell''s own occupancy is not seeded: the seed authority does not give his effective start date, and this packet does not invent one.',
        '2026-07-15T00:00:00+00:00',
        '2026-07-15T00:00:00+00:00'
    ),
    (
        'ke-occ-treasury-secretary-bessent',
        'ke-role-treasury-secretary',
        'ke-person-scott-bessent',
        '2025-01-01',
        NULL,
        'month',
        'D-PO-018 item 5',
        'D-PO-018 gives month precision only ("eff. 2025-01"); day defaulted to the 1st for storage. date_precision=month records the imprecision honestly.',
        '2026-07-15T00:00:00+00:00',
        '2026-07-15T00:00:00+00:00'
    ),
    (
        'ke-occ-sec-chair-atkins',
        'ke-role-sec-chair',
        'ke-person-paul-atkins',
        '2025-04-21',
        NULL,
        'exact',
        'D-PO-018 item 5',
        '',
        '2026-07-15T00:00:00+00:00',
        '2026-07-15T00:00:00+00:00'
    ),
    (
        'ke-occ-cftc-chair-selig',
        'ke-role-cftc-chair',
        'ke-person-michael-selig',
        '2025-12-18',
        NULL,
        'estimated',
        'D-PO-018 item 5',
        'D-PO-018 gives Senate confirmation date 2025-12-18 and states "sworn in early 2026" without an exact date. The stored value is the confirmation date, not the swearing-in date -- date_precision=estimated flags this for any as-of query landing near the turn of the year.',
        '2026-07-15T00:00:00+00:00',
        '2026-07-15T00:00:00+00:00'
    ),
    (
        'ke-occ-apple-ceo-cook',
        'ke-role-apple-ceo',
        'ke-person-tim-cook',
        NULL,
        '2026-09-01',
        'unknown_predates_tracking',
        'D-PO-018 item 5',
        'Cook''s own appointment date is not given by the seed authority (he has held the role long before this registry existed); effective_start_date is left NULL rather than an invented date. effective_end_date is the day the Ternus occupancy begins.',
        '2026-07-15T00:00:00+00:00',
        '2026-07-15T00:00:00+00:00'
    ),
    (
        'ke-occ-apple-ceo-ternus',
        'ke-role-apple-ceo',
        'ke-person-john-ternus',
        '2026-09-01',
        NULL,
        'exact',
        'D-PO-018 item 5',
        'Transition announced 2026-04-20; effective 2026-09-01 per D-PO-018 item 5 -- "model the scheduled succession, it is the whole point of effective-dating."',
        '2026-07-15T00:00:00+00:00',
        '2026-07-15T00:00:00+00:00'
    );

-- ---------------------------------------------------------------------------
-- Seed: D-PO-019 earnings-coverage company roster (PHASE0_ROSTER.md)
-- Group A (nasdaq100_top10) and Group B (crypto_native_top3): roster_status='confirmed'.
-- Group C (wgmi_candidate_pool): nine-company candidate pool, roster_status='candidate'
-- for every row -- the final five are market-cap-ranked at a future Conductor gate
-- (PHASE0_ROSTER.md §3.3); this packet does not pick them.
-- added_effective_date / removed_effective_date are left NULL for every row: neither
-- seed authority records a dated ratification event for roster membership itself (only
-- the underlying market-cap figures carry an as-of date), so no date is invented here.
-- ---------------------------------------------------------------------------

INSERT INTO ke_companies (
    company_id, legal_name, display_name, roster_group, roster_group_rank,
    roster_group_rank_basis, roster_status, market_cap_display, market_cap_as_of_date,
    market_cap_source, fund_weight_percent, notes, created_at, updated_at
)
VALUES
    ('ke-company-nvda', 'NVIDIA', 'NVIDIA', 'nasdaq100_top10', 1, 'market_cap', 'confirmed', '$4.60T', '2026-07', 'marketcap.company NDX ranking, PHASE0_ROSTER.md §3.1', NULL, '', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-company-aapl', 'Apple', 'Apple', 'nasdaq100_top10', 2, 'market_cap', 'confirmed', '$4.02T', '2026-07', 'marketcap.company NDX ranking, PHASE0_ROSTER.md §3.1', NULL, '', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-company-googl', 'Alphabet', 'Alphabet', 'nasdaq100_top10', 3, 'market_cap', 'confirmed', '$3.81T', '2026-07', 'marketcap.company NDX ranking, PHASE0_ROSTER.md §3.1', NULL, '', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-company-msft', 'Microsoft', 'Microsoft', 'nasdaq100_top10', 4, 'market_cap', 'confirmed', '$3.52T', '2026-07', 'marketcap.company NDX ranking, PHASE0_ROSTER.md §3.1', NULL, '', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-company-amzn', 'Amazon', 'Amazon', 'nasdaq100_top10', 5, 'market_cap', 'confirmed', '$2.42T', '2026-07', 'marketcap.company NDX ranking, PHASE0_ROSTER.md §3.1', NULL, '', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-company-avgo', 'Broadcom', 'Broadcom', 'nasdaq100_top10', 6, 'market_cap', 'confirmed', '$1.65T', '2026-07', 'marketcap.company NDX ranking, PHASE0_ROSTER.md §3.1', NULL, '', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-company-meta', 'Meta Platforms', 'Meta Platforms', 'nasdaq100_top10', 7, 'market_cap', 'confirmed', '$1.64T', '2026-07', 'marketcap.company NDX ranking, PHASE0_ROSTER.md §3.1', NULL, '', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-company-tsla', 'Tesla', 'Tesla', 'nasdaq100_top10', 8, 'market_cap', 'confirmed', '$1.46T', '2026-07', 'marketcap.company NDX ranking, PHASE0_ROSTER.md §3.1', NULL, '', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    (
        'ke-company-asml', 'ASML Holding', 'ASML', 'nasdaq100_top10', 9, 'market_cap', 'confirmed', '$450B', '2026-07',
        'marketcap.company NDX ranking, PHASE0_ROSTER.md §3.1', NULL,
        'Files with the SEC as a foreign private issuer (Forms 20-F/6-K, not 10-K/10-Q) per PHASE0_ROSTER.md §3.1 filing-mechanism note.',
        '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'
    ),
    ('ke-company-nflx', 'Netflix', 'Netflix', 'nasdaq100_top10', 10, 'market_cap', 'confirmed', '$386B', '2026-07', 'marketcap.company NDX ranking, PHASE0_ROSTER.md §3.1', NULL, '', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    (
        'ke-company-coin', 'Coinbase', 'Coinbase', 'crypto_native_top3', 1, 'market_cap', 'confirmed', '~$41.5B', '2026-07',
        'companiesmarketcap.com + The Block, PHASE0_ROSTER.md §3.2', NULL, '', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'
    ),
    (
        'ke-company-mstr', 'Strategy (MicroStrategy)', 'Strategy (MicroStrategy)', 'crypto_native_top3', 2, 'market_cap', 'confirmed', '~$34.8B', '2026-07',
        'companiesmarketcap.com + The Block, PHASE0_ROSTER.md §3.2', NULL, '', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'
    ),
    (
        'ke-company-crcl', 'Circle', 'Circle', 'crypto_native_top3', 3, 'market_cap', 'confirmed', '~$25.7B', '2026-07',
        'companiesmarketcap.com + The Block, PHASE0_ROSTER.md §3.2', NULL, '', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'
    ),
    (
        'ke-company-cifr', 'Cipher Mining', 'Cipher Mining', 'wgmi_candidate_pool', 1, 'fund_weight', 'candidate', NULL, '2026-07-13',
        'stockanalysis.com/etf/wgmi/holdings, PHASE0_ROSTER.md §3.3', 17.88,
        'Candidate pool row: ranked here by WGMI fund weight (the source''s own publication order), which PHASE0_ROSTER.md §3.3 explicitly notes is NOT the same as market-cap rank. The final five members are determined by market-cap ranking at a future Conductor gate.',
        '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'
    ),
    (
        'ke-company-hut', 'Hut 8', 'Hut 8', 'wgmi_candidate_pool', 2, 'fund_weight', 'candidate', NULL, '2026-07-13',
        'stockanalysis.com/etf/wgmi/holdings, PHASE0_ROSTER.md §3.3', 11.15,
        'Candidate pool row -- see ke-company-cifr notes on fund-weight-vs-market-cap ranking basis.',
        '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'
    ),
    (
        'ke-company-iren', 'IREN', 'IREN', 'wgmi_candidate_pool', 3, 'fund_weight', 'candidate', NULL, '2026-07-13',
        'stockanalysis.com/etf/wgmi/holdings, PHASE0_ROSTER.md §3.3', 10.33,
        'Candidate pool row -- see ke-company-cifr notes on fund-weight-vs-market-cap ranking basis.',
        '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'
    ),
    (
        'ke-company-keel-infrastructure', 'Keel Infrastructure', 'Keel Infrastructure', 'wgmi_candidate_pool', 4, 'fund_weight', 'candidate', NULL, '2026-07-13',
        'stockanalysis.com/etf/wgmi/holdings, PHASE0_ROSTER.md §3.3', 9.79,
        'Candidate pool row; no ticker given by the source table, so no ke_company_identifiers row is seeded for this company. See ke-company-cifr notes on fund-weight-vs-market-cap ranking basis.',
        '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'
    ),
    (
        'ke-company-mara', 'MARA Holdings', 'MARA Holdings', 'wgmi_candidate_pool', 5, 'fund_weight', 'candidate', NULL, '2026-07-13',
        'stockanalysis.com/etf/wgmi/holdings, PHASE0_ROSTER.md §3.3', 5.03,
        'Candidate pool row -- see ke-company-cifr notes on fund-weight-vs-market-cap ranking basis.',
        '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'
    ),
    (
        'ke-company-hive', 'HIVE Digital Technologies', 'HIVE Digital Technologies', 'wgmi_candidate_pool', 6, 'fund_weight', 'candidate', NULL, '2026-07-13',
        'stockanalysis.com/etf/wgmi/holdings, PHASE0_ROSTER.md §3.3', 4.72,
        'Candidate pool row -- see ke-company-cifr notes on fund-weight-vs-market-cap ranking basis.',
        '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'
    ),
    (
        'ke-company-clsk', 'CleanSpark', 'CleanSpark', 'wgmi_candidate_pool', 7, 'fund_weight', 'candidate', NULL, '2026-07-13',
        'stockanalysis.com/etf/wgmi/holdings, PHASE0_ROSTER.md §3.3', 4.69,
        'Candidate pool row -- see ke-company-cifr notes on fund-weight-vs-market-cap ranking basis.',
        '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'
    ),
    (
        'ke-company-riot', 'Riot Platforms', 'Riot Platforms', 'wgmi_candidate_pool', 8, 'fund_weight', 'candidate', NULL, '2026-07-13',
        'stockanalysis.com/etf/wgmi/holdings, PHASE0_ROSTER.md §3.3', 4.36,
        'Candidate pool row -- see ke-company-cifr notes on fund-weight-vs-market-cap ranking basis.',
        '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'
    ),
    (
        'ke-company-btdr', 'Bitdeer Technologies', 'Bitdeer Technologies', 'wgmi_candidate_pool', 9, 'fund_weight', 'candidate', NULL, '2026-07-13',
        'stockanalysis.com/etf/wgmi/holdings, PHASE0_ROSTER.md §3.3', 4.31,
        'Candidate pool row -- see ke-company-cifr notes on fund-weight-vs-market-cap ranking basis.',
        '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'
    );

INSERT INTO ke_company_identifiers (
    identifier_id, company_id, identifier_type, identifier_value, exchange,
    verified_as_of_date, provenance, created_at, updated_at
)
VALUES
    ('ke-ident-nvda-ticker', 'ke-company-nvda', 'ticker', 'NVDA', 'NASDAQ', '2026-07-15', 'PHASE0_ROSTER.md §3.1', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-aapl-ticker', 'ke-company-aapl', 'ticker', 'AAPL', 'NASDAQ', '2026-07-15', 'PHASE0_ROSTER.md §3.1', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-googl-ticker', 'ke-company-googl', 'ticker', 'GOOGL', 'NASDAQ', '2026-07-15', 'PHASE0_ROSTER.md §3.1', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-msft-ticker', 'ke-company-msft', 'ticker', 'MSFT', 'NASDAQ', '2026-07-15', 'PHASE0_ROSTER.md §3.1', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-amzn-ticker', 'ke-company-amzn', 'ticker', 'AMZN', 'NASDAQ', '2026-07-15', 'PHASE0_ROSTER.md §3.1', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-avgo-ticker', 'ke-company-avgo', 'ticker', 'AVGO', 'NASDAQ', '2026-07-15', 'PHASE0_ROSTER.md §3.1', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-meta-ticker', 'ke-company-meta', 'ticker', 'META', 'NASDAQ', '2026-07-15', 'PHASE0_ROSTER.md §3.1', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-tsla-ticker', 'ke-company-tsla', 'ticker', 'TSLA', 'NASDAQ', '2026-07-15', 'PHASE0_ROSTER.md §3.1', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-asml-ticker', 'ke-company-asml', 'ticker', 'ASML', 'NASDAQ', '2026-07-15', 'PHASE0_ROSTER.md §3.1', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-nflx-ticker', 'ke-company-nflx', 'ticker', 'NFLX', 'NASDAQ', '2026-07-15', 'PHASE0_ROSTER.md §3.1', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-coin-ticker', 'ke-company-coin', 'ticker', 'COIN', NULL, '2026-07-15', 'PHASE0_ROSTER.md §3.2', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-mstr-ticker', 'ke-company-mstr', 'ticker', 'MSTR', NULL, '2026-07-15', 'PHASE0_ROSTER.md §3.2', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-crcl-ticker', 'ke-company-crcl', 'ticker', 'CRCL', NULL, '2026-07-15', 'PHASE0_ROSTER.md §3.2', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-cifr-ticker', 'ke-company-cifr', 'ticker', 'CIFR', NULL, '2026-07-13', 'PHASE0_ROSTER.md §3.3', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-hut-ticker', 'ke-company-hut', 'ticker', 'HUT', NULL, '2026-07-13', 'PHASE0_ROSTER.md §3.3', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-iren-ticker', 'ke-company-iren', 'ticker', 'IREN', NULL, '2026-07-13', 'PHASE0_ROSTER.md §3.3', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-mara-ticker', 'ke-company-mara', 'ticker', 'MARA', NULL, '2026-07-13', 'PHASE0_ROSTER.md §3.3', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-hive-ticker', 'ke-company-hive', 'ticker', 'HIVE', NULL, '2026-07-13', 'PHASE0_ROSTER.md §3.3', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-clsk-ticker', 'ke-company-clsk', 'ticker', 'CLSK', NULL, '2026-07-13', 'PHASE0_ROSTER.md §3.3', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-riot-ticker', 'ke-company-riot', 'ticker', 'RIOT', NULL, '2026-07-13', 'PHASE0_ROSTER.md §3.3', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00'),
    ('ke-ident-btdr-ticker', 'ke-company-btdr', 'ticker', 'BTDR', NULL, '2026-07-13', 'PHASE0_ROSTER.md §3.3', '2026-07-16T00:00:00+00:00', '2026-07-16T00:00:00+00:00');
