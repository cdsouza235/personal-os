# Knowledge Edge Phase 1 — Phase-End Checkpoint Report (Fable)

- **Seat:** Phase-End Auditor (Fable), fresh session (did not build or operate any Phase 1 packet)
- **Date:** 2026-07-16
- **Scope:** P-KE-1A (state layer + migrations 00017–00021 + seeds), P-KE-1B (queue engine + fixture adapter contracts), P-KE-1C (dashboard + CLI)
- **Diff range:** `84200b0` (first parent of the P-KE-1A merge `585e165`) → `d57d51d` (P-KE-1C merge)
- **Authorities:** PRD amendment §8/§10.5/§11/§14.4/§19; PHASE0_ARCHITECTURE_DECISIONS AD-1/AD-4/AD-5; PHASE0_TRACEABILITY Phase-1 rows; PHASE0_ROSTER.md; DECISIONS.md D-PO-018/D-PO-019; PHASE0_PLAN §2
- **Method:** everything below was reproduced in-session by driving the real code (fresh migrated DBs, my own fixture datasets, my own boundary cases, positive-control discipline). The Builder's and packets' own test evidence was treated as untrusted.

## RESOLUTION: **hold** — with located conditions C1–C5 below

The phase's core guarantee — the fixture-rung daily loop — is genuinely delivered and
survived adversarial probing on every axis this checkpoint was scoped to attack (§8.3
both directions on all three surfaces, idempotency two ways, candidate caps, byte-level
determinism, seed fidelity, additive migrations, disabled-mode byte-identity, engine
purity, single write path, network containment). Nothing found is a safety regression
and nothing touches a live boundary.

The hold rests on one structural finding (C1): **Packet 1C's "decisions" half exists
only as unreachable plumbing.** The decision APIs, decision-history audit trail,
Tonight/Saved caps, and both expiry rules have zero production callers and no operator
surface — the exact "wired-nowhere" class this checkpoint's brief instructs me to
assume exists. Amendment §19 Phase 1 acceptance ("State transitions and caps are
enforced") is therefore only partially met, and the traceability table's "delivered"
claims overstate the tree. One bounded remediation packet closes C1–C4; a scoped
re-verification (exact probes listed at the end) then converts this resolution to
sign_off without re-running the whole checkpoint.

---

## 1. What was verified and held (all reproduced in-session)

### 1.1 The phase guarantee: fixture-rung daily loop (amendment §19 Phase 1, PHASE0_PLAN §2)

Drove `run_scan` → `build_queue_snapshot_view` → dashboard HTML → CLI human report on a
fresh migrated DB with my own five sources (all four lanes) and 21 media items + 1 event
+ 1 EDGAR filing of my own construction (41/41 probes passed; probe script preserved in
the session scratchpad, not the repo):

- **Four lanes populated end-to-end** — P0/P1/P2 sections, earnings section, saved
  section, demoted section, coverage report, all from fixture adapters only.
- **Idempotency, both directions (§11.1):** (a) re-running the same window against
  advanced cursors → 0 media, 0 events, 0 queue rows created; composed view identical.
  (b) overlap re-delivery of all 21 items under a later cursor → 0 created, 21
  reprocessed (audit-trail `discovery_occurrence` rows only), 0 duplicate queue rows.
  Also reproduced through the real CLI (`knowledge-edge scan` twice, same `--now`).
- **Candidate caps (§12.1):** P2 per-lane cap enforced at 5 under pressure from 7
  eligible items; **P0 never capped** (7 interviews > cap 5, all promoted); saved
  resurfacing capped at 2/day.
- **Determinism:** two fresh DBs, identical inputs, fixed `now` → dashboard HTML
  byte-identical, CLI human output byte-identical, queue composition identical.
- **Earnings lifecycle (§8.4):** event created from the calendar adapter with the EDGAR
  filing merged into `filing_urls`; status advanced deterministically across scans
  `confirmed → scheduled → live → ended → replay_pending → replay_available` with `now`
  as the only time input. Webcast URL on a non-approved vendor domain correctly
  quarantined as `Link pending (unknown vendor)` (empty approved-vendor set until the
  named Packet 3A gate — correct fail-closed default).
- **Three-track separation:** positive controls — `watched` rejected as an event-status
  value; `archived→live` and `watched→undecided` raise `InvalidTransitionError`.

### 1.2 The §8.3 ambiguous rule — both directions, every surface (this phase's #1 soft spot)

My own boundary matrix, in every lane: unknown-duration approved-source
`financial_media_segment` in lanes A, B, and C; threshold-exact (300s);
threshold-minus-one (299s); zero duration; mentioned-only; plus 6 substantive segments
to put the P2 cap under pressure. Results:

- **Never P0, never P2:** ambiguous items excluded per-candidate from both priority
  sections (lane-independent gate in `_build_and_record_queue`, not trusted to lane
  membership — the iteration-3 failure mode is dead).
- **Never absent:** lane-B and lane-C ambiguous items surface in the `demoted_ambiguous`
  tier **with the ambiguity reason** (`ambiguous_unknown_duration_demoted`) in all three
  surfaces — composed queue view, dashboard HTML (dedicated "Demoted / Ambiguous"
  section with reason column; P0/P2 blocks verified clean), and CLI human output
  (items listed individually with title + directness + reason — not summarized into a
  count; the 1C rework held). Lane-A ambiguous items surface in P1 (their lane's
  natural non-priority section) carrying the same reason in their explanation.
- **Boundaries:** 300s (threshold-exact) promoted to P2; 299s and 0s (known duration —
  correctly distinct from unknown) suppressed via the not-substantive path, never the
  ambiguous path; ambiguous items survive cap pressure (demoted tier is uncapped).

### 1.3 urllib.parse containment (G-GOV carve-out, 2026-07-16) — positive controls run

Planted a violation file in `knowledge_edge/state/` in-session, confirmed, reverted
(working tree verified clean after):

- `import urllib` → **guard fires.** `import urllib.request` → **fires.**
- `from urllib import parse as p` and `from urllib import request as r` → **both fire**
  (the alias smuggle is caught; the gate's letter is stricter than its semantic minimum
  — fail-closed, matches intent).
- **Gap (C4):** `import urllib.parse` / `from urllib.parse import …` planted in a
  **state/** file → guard silent, suite passes. The exception in
  `tests/test_knowledge_edge_migrations.py:74` (`_ALLOWED_NETWORK_ROOT_EXCEPTIONS`) is
  package-wide, not scoped to `engine/canonicalize.py`. The authorized carve-out is
  "exactly one file"; the gate does not enforce the one-file part. Today the intent
  holds (verified: `canonicalize.py` is the only KE file importing it, and
  `knowledge_edge/dashboard.py` deliberately hand-rolls host parsing to honor the
  scope), but nothing mechanical keeps it that way. Not network-capable, so no live
  risk — containment drift risk only.
- Scanner scope note: AST import scanning cannot see `importlib`/`__import__`/
  `subprocess` evasions; the suite-wide network-unreachable rule (QUALITY_GATES) is the
  backstop. Recorded, not a condition.

### 1.4 Seed fidelity as data (queried, not diffed)

Fresh migrated DB, queried through the state API:

- **Exactly 5 role seats**, roster_cap 1 each; exactly the 6 D-PO-018 people; nothing
  beyond the two ratified authorities.
- **Warsh** flips in on 2026-05-22 (None on 05-21; Powell honestly unseeded — no
  invented date). **Bessent** 2025-01-01 at `month` precision (imprecision recorded, not
  invented). **Atkins** 2025-04-21. **Selig** flips exactly on **2025-12-22** (None on
  12-18 and 12-21 — the confirmation-date error class is dead).
- **Cook → Ternus:** 2026-08-31 → Tim Cook; 2026-09-01 → John Ternus; no
  double-occupancy at the boundary.
- **Companies:** 10 `nasdaq100_top10` + 3 `crypto_native_top3` all `confirmed`; all 9
  WGMI rows `candidate` with `fund_weight` rank basis — the pool is correctly **not**
  resolved to a final five (that is the future Conductor gate, PHASE0_ROSTER §3.3).
  `added/removed_effective_date` NULL everywhere (no invented ratification dates).

### 1.5 Engine purity + single write path + network purity

- **Purity:** no wall-clock/random anywhere in `engine/` or the orchestrator (grep +
  imports sweep: `re`, `string`, `zoneinfo`, `urllib.parse` in the one blessed file,
  constants-only imports from state); `now` is a parameter end-to-end; proven
  behaviorally by the byte-identical fixed-`now` double runs. Wall-clock exists only in
  state-layer `created_at/updated_at` bookkeeping (same convention as core `state.py`).
- **Single write path:** zero `.execute` calls outside `state/` in the production
  package and CLI; zero raw `ke_` SQL outside the state layer. Every raw `ke_` INSERT
  in tests (6 files) is a **negative control inside `assertRaises(IntegrityError)`** —
  hostile rows proving DB constraints hold where the API refuses. No survivor of the
  1B raw-SQL-bypass class on any production path.
- **Network purity:** the recursive scanner covers the whole package (verified by
  planting in `state/`, the deepest point); guard fires (§1.3).

### 1.6 Migrations 00017–00021 (high-stakes scope)

Proven as data, not by reading comments: applied 00001–00016 to an empty DB, snapshotted
every pre-phase object's SQL and rowcounts, then applied 00017–00021 → **pre-phase
schema byte-identical; only `schema_migrations` changed (+5 checksummed rows); 47 new
`ke_*` objects.** Fresh-apply/re-apply idempotent (21 then 0); checksum drift on a KE
migration raises `MigrationChecksumMismatch` (packet test verified in suite);
delete-and-remigrate clean. Only additive `CREATE TABLE/INDEX IF NOT EXISTS` + seed
INSERTs into new `ke_` tables.

### 1.7 Disabled-mode byte-identity (proven independently)

Rendered the Today dashboard from the **pre-phase worktree (`84200b0`)** and from the
current tree (KE mode defaulted `disabled`) against the **same DB containing populated
`ke_*` rows**: byte-identical except the pre-existing wall-clock "Generated at UTC"
field (byte-identical after normalizing that one value); zero "knowledge" strings in
the disabled output. `--knowledge-edge-mode fixture` renders the section;
`shadow_live` is refused at the parser and by
`validate_knowledge_edge_feature_mode` (fail-closed; later-phase modes unreachable).

### 1.8 Quality gates and suite delta

All six QUALITY_GATES commands green in-session: **757 tests OK** (canonical + the
ResourceWarning pass), artifact hygiene clean, gitleaks clean, env hygiene clean. I
reproduced **both endpoints myself**: 567 green at `84200b0` (pre-phase worktree),
757 green at `d57d51d` → **+190**. There is, however, **no committed declaration** to
match this against — see C5.

### 1.9 Manifest attestation

**No manifest-listed rulebook file changed anywhere in the phase range** (verified:
`git diff --name-only 84200b0..d57d51d` over every `governance_files` entry and
protected path — empty). The only protected-path touch is `migrations/**`: the five
new KE files, exactly P-KE-1A's sanctioned high-stakes scope per PHASE0_PLAN's packet
table. All other changes sit inside the 1A/1B/1C `allowed_paths` sketches
(`src/personalos/knowledge_edge/**`, `src/personalos/cli/**`,
`src/personalos/dashboard.py`, `tests/**`). No signoff-store writes, no `.env*`
touches, no `rails/**` files created (network capability is not yet reachable — correct
for Phase 1).

---

## 2. Located conditions

### C1 — Packet 1C's decision half is unreachable plumbing (drives the hold)

Amendment §19 Packet 1C: *"Watch/Save/Skip/Watched and Watch live/Save replay states.
Caps, expiry, resurfacing, source health, audit history, and synthesis handoff
staging."* Delivered surfaces: queue view, scan, flag-false-positive — and nothing that
can make a decision. Verified with zero production callers (grep over the package +
CLI + dashboard; state-layer exports only, tests aside):

- `upsert_user_decision`, `update_media_decision_state`, `update_event_decision_state`
  (`state/decisions.py:72`, `state/media.py:295`, `state/events.py`) — **no operator
  surface, no caller.** The queue *respects* decision states (skip/watched exclusion
  and saved-resurfacing verified in §1.1), but nothing on any driveable path can set
  one.
- `record_decision_history` — **never written** on any production path: §13.4's
  append-only decision audit trail is schema-only.
- **Tonight cap (3 items / 90 min) and Saved cap (12)** (§12.1) — enforced nowhere.
  `engine/ranking.py`'s own docstring (lines 9–15) assigns them to "decision-acceptance
  time — that is Packet 1C's dashboard/CLI surface"; 1C then shipped no
  decision-acceptance surface.
- `is_saved_item_expired` / `is_replay_item_expired` (`engine/ranking.py:260-271`) —
  unit-tested, **wired nowhere**: the 14-day saved expiry and 7-day replay expiry never
  run; nothing on the production path ever sets `queue_visibility_state="expired"`.
  A saved or replay item currently lives forever.
- **Synthesis handoff staging** — `state/synthesis.py` has no production caller.

This is the §9 correlated-blind-spot class (guarded-looking primitives with no real
path) applied to product policy rather than safety — found in exactly the place the
brief predicted one would exist. Consequence: amendment §19 Phase 1 acceptance bullet
"State transitions and caps are enforced" is only partially true (candidate caps and
resurfacing: yes; decision-time caps and expiry: vacuously unenforced), and
PHASE0_TRACEABILITY's Phase-1 "delivered" marks for §7.3/§12.1(expiry)/§13.4(decision
audit) overstate.

**Close by:** one bounded remediation packet (suggest `P-KE-1D`) adding the decision
surface (CLI at minimum, mirroring `flag-false-positive`'s shape), Tonight/Saved cap
enforcement at decision-acceptance, expiry sweep wired into the scan (or queue-build)
path, decision-history writes on every decision, and a synthesis-handoff staging
surface — plus the §1.1-style drive tests for each. This must land **before any Phase 2
packet is declared complete**, since Phase 2's shadow reporting and every later phase
assume a working triage loop.

### C2 — Same-date incremental scan corrupts snapshot ordering (reproduced defect)

`_record_section` (`scan_orchestrator.py:798-830`) renumbers `rank_position` from 1 on
every scan while skipping already-recorded entity_ids. Reproduced: scan 1 records P1
ranks 1,2; a same-`queue_date` second scan (the §14.2 "scan-now" flow) discovering one
new higher-ranked item inserts it at rank 1 → **two rank-1 rows for the same
date/section**. `list_queue_snapshot` orders by bare `rank_position`
(`state/decisions.py:272-293`) with no tiebreak, so display order for ties is not
contractually deterministic; per-lane caps can also leak across same-date scans (a
section can accumulate more rows than the cap as rankings shift between scans).
No crash (the schema's UNIQUE is on `(queue_date, section, entity_type, entity_id)`,
not rank), and single-scan-per-date behavior — everything in §1.1 — is fully correct.

**Close by:** same remediation packet — either rank continuation for late additions, or
recompute-and-supersede semantics for the day's snapshot, plus a deterministic tiebreak
in `list_queue_snapshot`, with a same-date-rescan test.

### C3 — Launch rosters (§8.1/§8.2/§8.3 people and sources) are not seeded

Amendment §19 Packet 1A: *"Seed the launch rosters in this PRD."* Seeded: role appendix
(5 seats, 6 people) + D-PO-019 company roster — faithful (§1.4). **Not seeded anywhere**
(verified by grep over migrations + src): the 9 Lane-A podcast feeds, the 8 Lane-B
market voices (with aliases/spelling variants, e.g. Mohamed/Mohammed El-Erian), and the
Lane-C named individuals (Altman, Amodei, Hassabis, Huang, Su, Nadella, Pichai,
Zuckerberg, Jassy, Musk, Karp, Baker, Gerstner, Armstrong, Buterin). The CLI's
`ke-cli-*` builtin registry is a synthetic demo set, not the launch roster. The packet
brief's "exactly two ratified authorities" scoping (per
`tests/test_knowledge_edge_registries.py`'s header) explains the choice, but the
Lane-A source allowlist **is** ratified (D-PO-018 item 1) and the Lane-B/C people are in
the Conductor-accepted amendment itself — so this is ratified-data work left undone,
while PHASE0_TRACEABILITY rows for §8.1/§8.2/§8.3 claim "P-KE-1A (schema/seed) …
delivered."

**Close by:** seed the three lane rosters (+ aliases, + source endpoints from
`PHASE0_PROVIDERS_AND_ACCESS.md` §6/§8.1) in the remediation packet or as an explicit
early Phase-2 pre-requisite — it must exist before P-KE-2A can monitor anything real —
and correct the traceability rows either way.

### C4 — Scope the urllib.parse exception to the one authorized file

Per §1.3: change `_ALLOWED_NETWORK_ROOT_EXCEPTIONS` handling in
`tests/test_knowledge_edge_migrations.py` to accept `urllib.parse` only in
`engine/canonicalize.py` (path-conditional exception), so the gate's letter matches the
Conductor's "exactly one file" authorization. Small test-only edit; rides with the
remediation packet.

### C5 — The phase's audit trail and declared deltas are not in the repo (process)

For all three packets: `STATUS.md` was never updated (its newest entry predates the
phase; AGENTS.md Definition of Done requires it), no Codex audit report/`AUDIT-LOG.md`
entries were committed (the log's last entry is Phase-A, 2026-07-07), and no declared
test-count delta exists anywhere in-repo — the entire per-packet trail (12 audit rounds
per the checkpoint prompt) lives only harness-side. I could verify the +190 delta's
endpoints empirically but not against any committed declaration, and I had to take the
Codex-trail summary in the checkpoint prompt on trust. This weakens exactly the
audit-reconstructability this project's governance exists to provide.

**Close by:** Conductor/Builder decision on the durable home for harness-run packet
records (commit the per-packet audit reports + declared deltas back to `audits/`, or
record a pointer convention in AGENTS.md), plus a one-time STATUS.md catch-up entry for
Phase 1. Not remediation-packet work; should not silently persist into Phase 2.

### Recorded, not conditions (documented/deliberate — carried forward)

- **Orchestrator gap 1** (module docstring): events/media cannot be updated after
  creation → T-0 link/schedule refresh undeliverable until P-KE-3B/3C adds the update
  path; the replay lifecycle works only when `replay_url` is known at creation.
  Documented, deferred with a named owner — acceptable for a fixture phase; will bite
  in Phase 3 if forgotten.
- **Orchestrator gap 2:** deterministic dedup evidence evaluated within a single scan
  batch only (no cross-run `feed_guid`/`underlying_id` lookup) — a stale repost weeks
  later is caught only by the same-`dedupe_key` path. Documented; §11.4 explicitly
  permits measured-not-assumed duplicate leakage.
- **Demoted-ambiguous tier is composed at read time**, not persisted in
  `ke_queue_snapshots` (no seventh `QUEUE_SECTIONS` value; adding one needs a
  migration, excluded from 1B/1C scope). The §8.3 visibility guarantee holds on every
  surface (verified), but the *persisted* snapshot is not a complete record of what the
  queue showed — the demoted tier's audit trail lives in `priority_explanation` on the
  media rows. Fold a persisted section (or documented decision not to) into the next
  migration-bearing KE packet.
- **Provisional candidate caps** (`PROVISIONAL_PER_LANE_CANDIDATE_CAP = 5`, total 12)
  are Builder-invented placeholders, honestly flagged in `ranking.py`'s docstring as a
  Phase-0 planning gap (no Phase 0 doc records the promised default). Needs a
  Conductor/Session-2 number before those caps carry product weight.

---

## 3. Re-verification recipe (converts hold → sign_off when C1–C4 close)

Scoped re-check, no full checkpoint re-run needed: (1) drive a decision end-to-end per
lane — Watch/Save/Skip on media, Watch-live/Save-replay on an event — through the new
surface; confirm decision-history rows written, Tonight cap refuses a 4th/91st-minute
accept, Saved cap refuses a 13th, expiry sweeps a 15-day-old saved item and an 8-day-old
replay; (2) re-run my same-date two-scan probe — no duplicate ranks, caps hold across
scans; (3) confirm lane-roster seeds present as data (9 sources, 8+15 people, aliases
resolve); (4) re-plant `import urllib.parse` in `state/` — guard must now fire; confirm
it stays silent for `engine/canonicalize.py`; (5) suite green with the remediation
packet's declared delta matched.

## 4. WAYS_THIS_REVIEW_COULD_BE_WRONG

1. **Same-family caveat (standing):** the Builder and this reviewer are both Anthropic
   models; a shared blind spot would be invisible to me by construction. The Codex
   per-packet audits are the designed cross-family check — but per C5 their reports are
   not in this repo, so I built on a one-paragraph summary of them rather than the
   reports themselves. If that summary mischaracterized what Codex cleared, my
   "build on, don't repeat" allocation of attention was miscalibrated.
2. **The hold's scope reading could be wrong.** C1 rests on reading amendment §19
   Packet 1C's text as requiring a driveable decision surface in Phase 1. If a
   harness-side Conductor decision I cannot see re-scoped decisions/caps/expiry to a
   later packet, C1 downgrades to a recorded deferral and this resolution converts to
   sign_off with C2–C5 standing.
3. **I drove fixtures I constructed.** My adapter data is synthetic and well-formed;
   provider-quirk-shaped inputs (Packet 0C's golden fixtures: missing fields, weird
   durations, title conventions) were exercised only by the packets' own tests, which I
   did not independently re-derive.
4. **Determinism and purity were sampled, not proven.** Fixed-`now` double runs at the
   values I chose; DST/timezone boundary behavior in `canonicalize` conversions and
   recency tiers was not exhaustively attacked. The AST scanner's blind spots
   (`importlib`, `__import__`, subprocess) were noted but not exhaustively hunted
   across the tree.
5. **Byte-identity normalized one field** (the pre-existing wall-clock stamp); a
   regression hiding exclusively inside that field's bytes would be invisible.
   The comparison also used one DB shape; other DB states could theoretically diverge.
6. **Suite-green is necessary, not sufficient** — 757 passing tests bound what I did
   not re-derive; my independent probes covered the checkpoint's named soft spots plus
   what adversarial reading surfaced, within one session's budget.

## 5. Attestation

No `GOVERNANCE_MANIFEST.yaml`-listed file changed in the phase range beyond sanction
(none changed at all); the sole protected-path change is the five sanctioned additive
`migrations/**` files (P-KE-1A, high-stakes, per plan). This report is the only file
this session wrote to the repo; the positive-control probe file was created and deleted
in-session with `git status` verified clean afterward. All probe artifacts live in the
session scratchpad, outside the repo.

— Fable, Phase-End Auditor seat, 2026-07-16
