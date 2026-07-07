# ROADMAP.md — Personal OS re-baseline

Decomposition per SPEC §16.2, from `PHASE0_FINDINGS.md` (2026-07-07). Packet = branch =
one audited unit. Tiers are floors; RISK_REGISTER triggers raise them. Branch names:
`packet/<id>`.

**MVP (the done-definition, Conductor-anchored):** every morning, unattended: the system
computes today's routines/priorities via a real cadence engine, writes the day's routine
tasks to Todoist (ledger-deduped), and emails the 8am briefing via Gmail. Chris edits
routines via dashboard/CLI/synthesis-import; the next cycle reflects it. Calendar + the
12/4/8pm windows are post-MVP. OpenClaw is **cut** (D-PO-004).

---

## Phase A — clean state (governance + deletion)

### P-GOV-01 — land the governance overlay `[G-GOV, G0]`
Adds: `GOVERNANCE_MANIFEST.yaml`, `governance/**` (kit + templates), rewritten `AGENTS.md`,
lean living STATUS/DECISIONS/OPEN_QUESTIONS, `docs/PRD.md` v0.3 + `docs/ARCHITECTURE.md`
v0.3 (v0.2 to `docs/archive/`), auditor briefs, test strategy, human-input manifest,
`.gitleaks.toml`, rewritten `README.md`.
Archives (nothing destroyed): the ~26 phase/readiness docs + old STATUS.md →
`docs/archive/`; the 32 loose `PR##_AUDIT.md` (PR93–PR124) + `HARNESS_KICKOFF_PROMPT.md` →
`archive/pr-audits/`; the `_harness_proposal/` bundle → `archive/harness-proposal/`.
**Retires the doc-phrase test class** (sanctioned test-weakening, declared delta
887 → 809): the 10 `test_*_docs.py` files + 19 embedded doc-phrase methods (17 `test_docs_*` + 2 README-link) that
pinned prose of the archived docs. No product code or product tests are touched.
- allowed_paths: `governance/**`, `GOVERNANCE_MANIFEST.yaml`, `AGENTS.md`, `README.md`,
  `.gitleaks.toml`, `docs/**`, `audits/**`, `archive/**`, `STATUS.md` (archive),
  root loose-artifact moves, `tests/**` (doc-phrase removals ONLY, per the enumerated list)
- forbidden_paths: `src/**`, `migrations/**`
- acceptance: manifest parses + closure (all listed files exist); QUALITY_GATES all green
  incl. secret scan + env hygiene at the declared 809; every retired artifact present in
  archive; README points only at the new kit; deleted tests match the enumerated
  doc-phrase list exactly (audit diffs the list).
- audit: Codex plan+pack audit (this packet carries the Phase-0 §16.2 artifacts).

### P-CLEAN-01 — dead skeletons `[G4: deletion]`
Deletes top-level `personalos/` (8 `.gitkeep` dirs) and `app/` (2 `.gitkeep` dirs).
- allowed_paths: `personalos/**`, `app/**`
- acceptance: both gone; suite green; no source references either path (grep-proof in audit).

### P-CLEAN-02 — retire the process layer from code `[G4: deletion; G-GOV: manifest edit; high-stakes: test-count change]`
Deletes the sanctioned module list (all `phase14c_*`, `mvp_readiness`, `nonhuman_closure`,
`weekend_test_readiness`, `dry_run_evidence`, `final_nonhuman_handoff`,
`openclaw_model_strategy`, `openrouter_model_smoke_client`, `phase14_*`) + their CLI
subcommands + their remaining tests (the doc-phrase test class was already retired by
P-GOV-01 — this packet's declared test delta covers process-module tests only). Replaces
`pre_live_readiness` /
`operator_status` consumption in `today.py` / `cli.py` / `dashboard.py` with a lean
`status.py` rail-state surface (`inert|soaking|live` per rail, from config — HUMAN_GATES
activation ladder). **Keeps**: `permissions.py`, `side_effects.py`, `idempotency.py`,
`path_safety.py`, `scheduler.py` (sim tables feed P-SCHED-01), `state.py`.
- allowed_paths: `src/personalos/**`, `tests/**`, `docs/**` (references),
  `GOVERNANCE_MANIFEST.yaml` (the sanctioned protected-path shrink ONLY — this is why the
  packet carries G-GOV)
- forbidden_paths: `migrations/**`, `governance/**` (the kit itself stays untouched)
- acceptance: sanctioned deletion list matched exactly (audit diffs the list); product
  tests untouched and green; expected test-count delta declared up front and matched;
  CLI help shows only product commands; no module imports a deleted name.
- note: the six network-capable smoke modules die here → the manifest's protected-path
  list shrinks to `rails/**` (that manifest edit rides along as sanctioned G-GOV).

## Phase B — the product brain

### P-DESIGN-01 — routine model + cadence engine design `[G6]`
The one real design decision. Inputs: PRD v0.3 §routine-model (carries forward old PRD §14,
which was good), Phase 0 finding that `settings_json` carries no semantics. Output: schema
(first-class cadence/missed-behavior/rotation/windows columns), engine contract
(`(routine defs, completions, date) → due set` as pure functions), editability story.
Lands in DECISIONS.md + ARCHITECTURE.md **before** P-CORE work starts.

### P-CORE-01 — routine schema migration `[high-stakes: migrations; G4 if destructive]`
Migrate `routines` from settings-blob to the D-PO-designed schema, with data carry-over
for existing rows.
- forbidden_paths: everything except `migrations/**`, `src/personalos/state.py`, tests.

### P-CORE-02 — cadence engine
Pure due-today computation + missed-behavior + rotation, per the G6 contract; exhaustive
table-driven tests (this is the correctness heart of the product).
- allowed_paths: `src/personalos/routines*.py`, `src/personalos/state.py`, `tests/**`

### P-CORE-03 — wire the product surfaces
`routines.py`/`priorities.py` gain CLI + dashboard routes (routine editor, priority
registry — the PRD §28 criteria Phase 0 found orphaned). Dashboard stays localhost.
- acceptance: create/edit/disable a routine end-to-end via CLI and dashboard; due-today
  visible in Today View from the real engine.

## Phase C — the loop (still inert)

### P-BRIEF-01 — template briefing generator
Deterministic 8am briefing from real state (due routines, priorities, carryovers) through
the existing pipeline (plan → window → preview → export). Model-optional by design; the
PRD §composer upgrade is post-MVP.

### P-SCHED-01 — real scheduler, manual trigger
`personalos run morning` executes the full morning cycle end-to-end in no-send mode,
producing would-have-sent artifacts + ledger rows (the soak evidence for G5). Background
activation (launchd) is NOT this packet — it is G4+G5 later.

## Phase D — rails (each rail: adapter packet, then activation packet)

### P-RAIL-TD-01 — Todoist adapter (inert) `[G5-flagged reachability, high-stakes]`
Thin client in `src/personalos/rails/todoist.py` (~smoke-client-sized), consuming
permission model + ledgers + dedupe keys; fake-client tested; live path checks rail state
`live` + credentials, fails closed on either.
### P-RAIL-TD-02 — Todoist activation `[G5]`
Config flip + bounded live period + kill-procedure drill (RUNBOOK) + review.

### P-RAIL-GM-01 / P-RAIL-GM-02 — Gmail adapter / activation `[G5]`
Same ladder; longest soak (email is irreversible).

### P-RAIL-CAL-01 / P-RAIL-CAL-02 — Calendar `[G5]` *(post-MVP)*

### P-SCHED-02 — background activation `[G4+G5]`
launchd LaunchAgent + unload-proof + kill drill; consumes HI-09 (production DB) + HI-10.

**The MVP boundary is TD-02 + GM-02 + SCHED-02 closed** — "unattended" is part of the
PRD §2 definition, so scheduler activation is inside MVP, not after it (single
authoritative boundary; matches `audits/test-strategy.md`).

## Phase E — debt
- **P-DEBT-01 — one shared permission evaluator** `[HIGH-STAKES, solo audit — NOT
  batchable]` (retires the 12-fold duplication; permission-model changes are always
  high-stakes per RISK_REGISTER/HUMAN_GATES). Expected tests: behavioral-equivalence
  decision matrix old-vs-new before any copy is deleted (test-strategy Phase E).
- **P-DEBT-02** — split `state.py` / `cli.py` by domain (mechanical; batchable, low-stakes).
- **P-DEBT-03** — wire-or-delete: `fitness.py`, `reports.py`, `runtime_bootstrap.py`,
  `completion.py` (orphans; per-module Chris call; batchable, low-stakes).

## Sequencing
A strictly first (A→B); B strictly before C; D per-rail after C; E interleaves anywhere
after A as batch-filler **except P-DEBT-01 (solo, high-stakes)**. Fable checkpoints: end
of A (clean state), end of B (the engine), MVP boundary (TD-02 + GM-02 + SCHED-02).

## Future enhancements (recorded, not planned)
Composer/live-model briefings (PRD §18) · Calendar availability-aware scheduling ·
12/4/8pm windows · fitness integration v1.5 · reports/chart-pack jobs. OpenClaw: cut
(D-PO-004) — re-enters only as a new G6 design decision if a need appears.
