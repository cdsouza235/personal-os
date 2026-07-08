# STATUS.md — Personal OS (living state; Builder-owned; git-diff-verified, not trusted)

## Current
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
