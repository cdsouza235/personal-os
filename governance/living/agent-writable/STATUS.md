# STATUS.md — Personal OS (living state; Builder-owned; git-diff-verified, not trusted)

## Current
- **★★★★ KNOWLEDGE EDGE PHASE 1 HOLD CLOSED BY P-KE-1D (2026-07-16).** Phase 1
  (P-KE-1A state layer + migrations 00017–00021 + D-PO-018/019 seeds; P-KE-1B queue
  engine + fixture adapters; P-KE-1C dashboard + CLI) was Fable-checkpointed
  `hold` with conditions C1–C5 (`audits/ke-phase-1-phase-end-fable-report.md`,
  2026-07-16): C1 (Packet 1C's Watch/Save/Skip/Watched + Watch-live/Save-replay
  decision surface existed only as unreachable state-layer plumbing — zero
  production callers, Tonight/Saved caps and both expiry rules unenforced
  anywhere driveable) was the hold's structural blocker. **P-KE-1D closes it:**
  `personalos knowledge-edge decide {watch,save,skip,watched,watch-live,
  save-replay}` is now the first production caller of `upsert_user_decision`/
  `update_media_decision_state`/`update_event_decision_state`/
  `record_decision_history` (every decision path writes an append-only
  `ke_decision_history` row, §13.4); the Tonight cap (3 items / 90 known-duration
  minutes) and Saved cap (12 items) are enforced at decision-acceptance with
  honest CLI refusal messages (`engine/ranking.TONIGHT_ITEM_CAP`/
  `TONIGHT_KNOWN_DURATION_CAP_SECONDS`, new this packet); `_sweep_expired_decisions`
  is wired into `run_scan` before queue-build, so `is_saved_item_expired`/
  `is_replay_item_expired` (14d/7d) now actually set `queue_visibility_state=
  "expired"` on the production path; `knowledge-edge synthesis {list,export}` is
  the first production caller of `state/synthesis.py`. C2 (same-date rescan
  ranks), C3 (§8.1/8.2/8.3 launch-roster seeds, migration `00022`), C4 (urllib.parse
  gate scoped to `engine/canonicalize.py` only), and the demoted-tier persistence
  fold-in were already closed in-tree when this packet's work began (visible in
  `scan_orchestrator.py`'s `_record_section`/`_sweep_expired_decisions`, migration
  `00022`, and `tests/test_knowledge_edge_migrations.py`'s
  `_ALLOWED_NETWORK_IMPORT_EXCEPTIONS`) — this session verified each still holds
  and added the C1 surface plus its own drive tests. **Declared test delta:
  checkpoint-verified 567 (pre-phase) → 757 (checkpoint, end of 1C) → 781 now**
  (suite green; +24, itemized: 9 new `decide`/`synthesis` CLI tests + 3 new
  `run_scan` expiry-sweep production-path integration tests added this session,
  plus C2/C3/C4 tests already present in the tree before this session started).
  Exact per-iteration/per-commit test-count attribution and merge SHAs are not
  reconstructable in this sandbox (no `.git`/`git` binary present here) — see
  the packet's own handoff for what this session specifically touched.
  **PHASE0_TRACEABILITY.md corrected AND re-vocabularied (iteration 6 rework, this
  packet):** §7.3/§12.1(expiry)/§13.4/§8.1/§8.2/§8.3 first corrected from overstated
  "delivered" to reflect C1's actual closure; then a second, whole-table pass fixed
  the broader class the auditor found on re-review — "delivered" had predated Phase 1
  (0B used it to mean "requirement mapped to a packet," not "packet executed and
  in-tree") and rows citing wholly- or partly-future packets (e.g. §7.1 → P-KE-4A,
  §8.4 → P-KE-3A/3B/3C, and most of §9-§18/§20-§21) still read "delivered." Every row
  in the table now uses one of: `delivered (P-KE-xx)` only for packets actually
  merged in the current tree (Phase 1: P-KE-1A/1B/1C/1D, plus adopted planning
  artifacts), `partial: ... delivered (P-KE-xx); ... planned (Phase N, P-KE-yy)` where
  the requirement spans landed and future work, or `planned (Phase N, P-KE-yy)` for
  wholly future rows. §22's `deferred` rows were already honest and are untouched.
- **★★★★ KNOWLEDGE EDGE PHASE 0 COMPLETE + SESSION 1 IN PROGRESS (2026-07-15).**
  P-KE-00B merged (`57bdff4`, crash-recovered relaunch i4: Codex 0 findings, third-reviewer
  concur, G0/G-GOV/G1 Chris-approved, pushed). Session 1 (the human gate) decisions
  ratified and recorded as **D-PO-018**: allowlist, IR-redirect mechanism, scope limits,
  EDGAR user-agent, 5-seat launch role appendix (Warsh/Bessent/Atkins/Selig/Cook→Ternus
  2026-09-01). **D-PO-019:** FMP rejected at real price ($50/mo earnings tier) —
  replaced by a bounded manual roster (top-10 NDX + top-3 crypto cos + top-5 WGMI, by
  market cap, quarterly refresh) via free SEC EDGAR + IR pages. YouTube key saved
  (search.list-restricted), EDGAR UA set — `.env.local` live. **Open:** YouTube daily-
  quota confirmation; roster seed list (next KE packet, returns to Chris). Then Packet
  0C (bounded probe: EDGAR + YouTube only, no FMP).
- **★★★ P-DESIGN-01 MERGED (`6897253`, `--no-ff`)** — routine model + cadence engine design
  formalized as D-PO-010 in DECISIONS.md + ARCHITECTURE.md v0.4. **First personal-os packet
  driven end-to-end by `harness run --project personal-os`** (the harness's own production
  loop, not hand-built): live Claude builder wrote the decision, live Codex auditor gave
  `accept_with_conditions`/0 issues. Route computed `STOP_TO_HUMAN` (high-stakes, no
  third-reviewer configured) — a real, tracked gap (**Q-PO-005**: the loop has no built
  override path for this yet, verified live). Unblocked by a one-time Conductor sign-off
  (`audits/signoffs/P-DESIGN-01-G0-G1-signoff.md`) + manual `git merge --no-ff`, NOT a
  repeatable path — the next novel-path personal-os packet needs a real fix (harness-side:
  `projects/mis/ROADMAP.md` F1) before it can run unattended through the loop. 421 tests
  green (docs-only change). **NEXT: P-CORE-01** (routine schema migration) per
  `governance/ROADMAP.md` — will hit the SAME third-reviewer gap if run live; either build the
  harness fix first, or take another one-time Conductor override.
- **★ PHASE A CODE-COMPLETE (2026-07-07).** P-GOV-01 (`229f974`) + P-CLEAN-01 (`1772f40`)
  + P-CLEAN-02 (`d5bc829`) all Codex-accepted, Conductor-signed (`audits/signoffs/`),
  merged `--no-ff`, pushed. Repo state: 27 product modules, 421 tests green, zero
  network-capable imports, one rulebook, fail-closed rail-state surface.
- **★★ PHASE A SIGNED OFF** — Fable phase-end checkpoint (fresh session) → `sign_off`
  (`audits/phase-A-phase-end-fable-report.md`, committed `3404ab8`). Drove the product
  end-to-end; rail-state surface held all probes (P1–P7); casualty/survivor fidelity
  clean; whole-phase attestation clean.
- **Carries from the checkpoint (owner in parens):**
  - **R1** sign-off provenance: (a) Conductor ratification of the `02951b5`-embedded
    P-GOV-01 sign-off → DECISIONS.md (**awaiting Chris's one-liner**); (b) distinguishable
    sign-off identity (distinct git identity for sign-off commits, or B-00's
    OS-permissioned store) before Phase B gates rely on the store (**HI-11-adjacent**).
  - **R2** `cli.py:1016` setdefault→unconditional set + `_append_rail_state_lines` shape
    validation (fold into next code packet).
  - **R3** widen network-primitive tripwire wording (`http.server`, `socketserver`, …) +
    consider `execution_rails.py` in the path-trigger table (next G-GOV edit).
  - **R4** `serve_today_dashboard` wire-or-delete (P-CORE-03 acceptance item).
  - **R5** QUALITY_GATES baseline 809→421 + demo vocabulary/banner (next G-GOV edit).
- **R1(a) RATIFIED (D-PO-008) + HI-11 DECIDED (D-PO-009): B-00 first.** Work moves to the harness repo
  (B-00 vs P-DESIGN-01 first; note R1(b) is naturally solved by B-00's approval store).
- *(history below)*
- **Phase:** A (clean state). **P-GOV-01 MERGED** (`229f974`, pushed; sign-off
  `audits/signoffs/P-GOV-01-G1-signoff.md`).
- **P-CLEAN-01** (dead skeletons): built + **Codex accept (zero findings, 1 round)** on
  `packet/P-CLEAN-01` @ `61a3703`. Awaiting Conductor G4/G1 gate.
- **Active packet:** **P-CLEAN-02** (process-layer retirement) on `packet/P-CLEAN-02`
  (stacked on P-CLEAN-01) — BUILT: 32 modules + 27 test files + the phase14c setup script
  deleted; `cli.py` 4,233→1,556 lines (36 handlers + 37 catalog entries + 2 parser blocks
  excised); readiness/operator consumption in `status/today/dashboard/demo/cli` replaced
  by the lean `create_rail_state_report()` surface (RAIL_STATES constants in `status.py`,
  now manifest-protected as activation-ladder state); sanctioned manifest shrink applied
  (six network-capable modules removed; `status.py` added). **Declared test delta:
  809 → 417** (27 files + 66 test_cli methods + assertion-vocabulary updates in 5 files).
  All quality gates green (suite ×2, gitleaks, env, artifacts). **Declared carry:**
  QUALITY_GATES baseline line still reads 809 — governance/** is forbidden here; the
  one-line refresh rides with the next sanctioned G-GOV edit. `.env.example` kept
  (credential-name documentation; re-owned by P-RAIL packets).
- **Iteration 2 (Codex reject r1 → both findings closed by construction):** F1 — rail
  state is now fail-closed mechanically: private literal validated AT IMPORT
  (`RailStateError` refuses module load), public `RAIL_STATES` is a `MappingProxyType`
  (item assignment → TypeError), `create_rail_state_report()` reads privates + re-validates
  (rebinding the public attr is inert; tampering yields RailStateError, never a report);
  dashboard render RAISES on missing/malformed `rail_state_summary` (no "unavailable"
  degradation); `invalid_rail_states` report field removed (validation raises instead of
  labeling). 4 new contract tests prove immutability/validation/rebind-inertness/shape.
  F2 — the two orphaned credential-name env helpers deleted from `cli.py` (os.environ
  reads now ZERO) + 4 dead phase14c helpers deleted from `tests/test_cli.py`; stale
  status-help wording fixed. **Declared test delta now 809 → 421.** All gates green;
  Codex's own r1 hostile probes re-run: TypeError / RailStateError (fail closed).
- **Iteration 3 (Codex r2 reject → B1):** F1/F2 verified CLOSED by Codex; new blocker B1 —
  an over-broad `git add -A` in the r2 commit swept the Conductor's (legitimately authored)
  P-CLEAN-01 signoff into an agent commit, making approval provenance indistinguishable
  from self-attestation. Closed by merging `main` (whose `cc819db` is the authoritative
  Conductor-record commit) into the packet branch — the signoff is no longer in the packet
  diff (`git diff main...HEAD -- audits/signoffs/` = empty). **Standing Builder convention
  from this finding: agent commits never use bare `git add -A`; staging always excludes
  `audits/signoffs/` (`git add -A -- ':!audits/signoffs'`).** Provenance context: the
  Conductor authored the file himself (transcript, 18:12) before the agent commit; content
  was never in question — only commit provenance, which is exactly what the trigger exists
  to catch.
- **Active packet:** P-GOV-01 (this governance pack), iteration 2 — Codex iter-1 `rework`
  (9 findings) all addressed: pack completion executed in working tree (archives, README,
  final PRD/ARCHITECTURE names), doc-phrase test class retired (887→809 declared),
  templates adopted, secret-scan + env-hygiene gates added, signoff store defined
  (`audits/signoffs/**`, Conductor-only), E-002 records SPEC-kit omissions, P-CLEAN-02
  G-GOV fix, P-DEBT-01 reclassified high-stakes/solo, MVP boundary unified
  (TD+GM+SCHED-02). Prompt: `audits/CURRENT-audit-prompt.md`.
- **Baseline:** `main` @ `58fc27e` (PR #123). Quality gates: 809 green (~14s) + gitleaks
  clean + env hygiene clean (sanctioned delta from 887, see QUALITY_GATES).
- **Rail states (activation ladder, HUMAN_GATES):** todoist=inert · gmail=inert ·
  calendar=inert · model-api=inert · scheduler=off. Each has run live exactly once in the
  2026-06-30/07-01 bounded smokes; nothing is live now.
- **Loop mode:** manual (POLICY_EXCEPTIONS E-001) until harness B-00 lands.

- **Audit trail:** iter-1 `rework` (9 findings) → iter-2 **`adopt_with_fixes`** (all 9
  closed; 3 conditions N1 archive-allowlist / N2 stale P-CLEAN-02 wording / N3 count) →
  conditions fixed in-tree → scoped Codex closure pass → **Conductor gate HI-01**.

## Next
P-GOV-01 merge → P-CLEAN-01 (skeletons) → P-CLEAN-02 (process-layer retirement) →
Fable phase-A checkpoint → P-DESIGN-01 (routine model, G6). See `governance/ROADMAP.md`.

## Log
- 2026-07-07 — Phase 0 findings audit delivered (`audits/PHASE0_FINDINGS.md` +
  `audits/PHASE0_CODEX_AUDIT.md`): product brain (cadence engine) never built; readiness
  not_ready by construction; process layer ~30 files/15.9k LOC; live-gates are
  flag+string-constant. Conductor set MVP = live morning loop; docs retire freely;
  OpenClaw cut.
- 2026-07-07 — Governance overlay v1 authored (this pack) by the Fable seat (production
  Builder excluded from governance authorship); pending Codex audit + Conductor gate.
