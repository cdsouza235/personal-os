-- P-KE-1A: Knowledge Edge roster-change proposals and synthesis handoffs (amendment
-- §18.3 deterministic recommendations, §7.6 knowledge handoff).
-- Purely additive CREATE TABLE per PHASE0_ARCHITECTURE_DECISIONS.md AD-5. No seed data:
-- roster_change_proposal rows are produced by Packet 5C's monthly review, and
-- synthesis_handoff rows are produced when a user marks an item Watched -- neither
-- happens in this schema-only packet.

-- Deterministic, human-approved-only roster/threshold recommendations (§18.3). Nothing
-- in this table is ever applied automatically -- `status` only moves to 'applied' after
-- an explicit human decision recorded via `decided_by`.
CREATE TABLE IF NOT EXISTS ke_roster_change_proposals (
    proposal_id TEXT PRIMARY KEY,
    proposal_type TEXT NOT NULL,
    target_entity_type TEXT NOT NULL,
    target_entity_id TEXT,
    proposed_change_json TEXT NOT NULL,
    rationale TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    decided_at TEXT,
    decided_by TEXT,
    CHECK (
        proposal_type IN (
            'retire_source',
            'demote_person',
            'promote_company',
            'demote_company',
            'adjust_expiry',
            'add_alias',
            'repair_source',
            'other'
        )
    ),
    CHECK (target_entity_type IN ('source', 'person', 'company', 'role', 'topic')),
    CHECK (status IN ('proposed', 'approved', 'rejected', 'applied')),
    CHECK (status = 'proposed' OR (decided_at IS NOT NULL AND decided_by IS NOT NULL))
);

-- Bounded, copyable handoff into the manual ChatGPT/Obsidian loop (§7.6). Creating a row
-- here is itself a no-network, no-Obsidian-write, local-state-only action; the actual
-- Obsidian draft write is a Packet 5B concern gated at Session 3.
CREATE TABLE IF NOT EXISTS ke_synthesis_handoffs (
    handoff_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    handoff_type TEXT NOT NULL,
    packet_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'staged',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (entity_type IN ('media_item', 'scheduled_event')),
    CHECK (
        handoff_type IN (
            'copy_synthesis_packet',
            'create_obsidian_draft',
            'no_thesis_impact',
            'promote_to_session_note'
        )
    ),
    CHECK (status IN ('staged', 'completed'))
);

CREATE INDEX IF NOT EXISTS idx_ke_roster_change_proposals_status
ON ke_roster_change_proposals (status, target_entity_type);

CREATE INDEX IF NOT EXISTS idx_ke_synthesis_handoffs_entity
ON ke_synthesis_handoffs (entity_type, entity_id);
