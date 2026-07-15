# Phase-B Checkpoint Prompt — Fable (phase-end seat)

Date posted: 2026-07-14 · Builder seat: Claude Sonnet 5, driving the harness orchestrator
throughout · **Independence: run this in a FRESH session that did not build Phase B.**
Read `audits/PHASE-END-AUDITOR-BRIEF-fable.md` first — your standing rules, including the
correlated-blind-spot lens (§9): Builder and you are both Anthropic; your seat exists to
catch what an Anthropic reasoner and the cross-family per-packet auditor might both miss.
The class to hunt: doctrine-as-implementation.

**Provenance note, stated plainly:** this checkpoint should have run immediately after
Phase B merged. It did not — the practice lapsed on the Builder seat, discovered and
surfaced only once Phase B, C, and part of D were already built, merged, and (per D-PO-016)
about to be built further upon by a new PRD amendment (Knowledge Edge). You are reviewing
real, already-merged, already-in-production-path code, not a proposal. If you find a real
defect, it is a real defect in shipped work, not a design-stage catch — treat the severity
accordingly, and note in your report that later phases (C, D, E, and the not-yet-started
Knowledge Edge amendment) may already depend on whatever you find.

## The phase under review

Phase B (the product brain — routine model, schema, cadence engine, product surfaces),
four packets, all merged into `main`:

- **P-DESIGN-01** (`6897253`): routine model + cadence engine design (G6). Recorded as
  **D-PO-010** in `governance/living/agent-writable/DECISIONS.md` (read the full entry —
  it is long and specific: cadence types, missed-behavior types, the
  `compute_due_and_owed(routines, completions, *, as_of_date, occurrence_overrides={})`
  engine contract, the GTG-as-individual-rows-sharing-a-rotation_group design, the
  cleaning-pool-with-dynamic-per-occurrence-override design). This is the SPEC every
  other Phase B packet must have actually implemented faithfully — your primary job is
  verifying the code matches this spec, not re-deriving the spec yourself.
- **P-CORE-01** (`075e2c9`): routine schema migration — `settings_json` blob replaced with
  first-class columns (`cadence_type`, `cadence_config_json`, `missed_behavior_default`,
  `rotation_group`, `weekly_target`) per D-PO-010, with data carry-over for existing rows.
  High-stakes tag: migrations, G4 if destructive.
- **P-CORE-02** (`e47b9cb`): the cadence engine itself — pure due-today computation +
  missed-behavior + rotation, per the G6 contract. The PRD/ROADMAP calls this "the
  correctness heart of the product" and mandates exhaustive table-driven tests.
  **Known finding from this session's own history**: the third-reviewer caught a real
  defect on this packet during its original build — "weekly-target undercounting"
  (referenced in `governance/living/agent-writable/OPEN_QUESTIONS.md`'s Q-PO-005 closure
  note). Confirm the actual fix landed correctly in the merged code, not just that a fix
  was claimed.
- **P-CORE-03** (`96451fb`): wire the product surfaces — `routines.py`/`priorities.py`
  gain CLI + dashboard routes (routine editor, priority registry). Acceptance criterion
  per ROADMAP.md: "create/edit/disable a routine end-to-end via CLI and dashboard;
  due-today visible in Today View from the real engine."

**Important scope note on later drift:** D-PO-010's own content was later PARTIALLY
REVERSED by **R-PO-001** (2026-07-14, in `DECISIONS.md`) — GTG was pulled OUT of the
routine-model schema entirely after Phase B shipped, once it became clear during a later
conversation that rep-accumulation didn't fit the (also later-decided) Todoist-as-state
design for daily check-ins. This reversal happened AFTER Phase B merged and is NOT
something Phase B's own code needs to have anticipated — but you should verify: does any
GTG-shaped code/schema/test still exist in the current `main` that should have been
cleaned up by R-PO-001 and wasn't? That is exactly the kind of "survivor" this checkpoint
should hunt for (see charge 3 below), even though it originates from a later decision, not
a Phase B defect per se.

## Phase-boundary definition (audits/test-strategy.md → Phase B, and D-PO-010 itself)

The cadence engine is a pure function (`compute_due_and_owed`), no I/O, exhaustively
table-tested. Schema carries real semantics (no more `settings_json` blob). Product
surfaces (CLI + dashboard) let Chris actually create/edit/disable routines and see
due-today reflect the real engine, not a placeholder.

## Your checkpoint charge (beyond re-running what the per-packet auditor ran)

1. **Attack the cadence engine directly.** Derive your OWN adversarial test cases —
   cadence × missed-behavior × rotation × date-boundary combinations — and run them
   against the real `compute_due_and_owed` function (not the existing test suite; write
   NEW probes). Specifically stress: ISO week boundary handling (D-PO-010 mandates a fixed
   Monday-Sunday week for `weekly`/`weekly_target_*` accounting, not a rolling 7-day
   window — confirm this is actually how the code behaves, not just documented), the
   cleaning pool's per-occurrence override mechanism (`occurrence_overrides` parameter),
   and the weekly-target undercounting class of bug the third-reviewer previously caught
   on this exact packet (confirm the class of bug is actually closed, not just the one
   instance that was reported).
2. **Verify engine purity (invariant 1 in `docs/ARCHITECTURE.md`) and the single write
   path.** Does `compute_due_and_owed` perform any I/O, mutate any shared state, or have
   any non-deterministic behavior (wall-clock reads, random, etc.) anywhere on its real
   call path? Does all routine-state mutation actually go through `state/` package APIs,
   or is there a path that writes around it?
3. **Hunt survivors and drift.** Any GTG-shaped schema/code/tests that R-PO-001 should
   have removed but didn't (see scope note above)? Any place the schema still references
   the old `settings_json` blob pattern? Any doctrine-as-implementation gap — a
   guarded-looking validation that's actually bypassed on some real call path, a
   fail-open error branch, a safety helper that's defined but never actually called from
   the real code path?
4. **Drive the real product surfaces.** Create, edit, and disable a routine end-to-end via
   CLI against a scratch DB; confirm due-today in Today View reflects the real engine's
   output, not a cached/stale/placeholder value.
5. **Attestation:** confirm no `GOVERNANCE_MANIFEST.yaml`-listed file changed beyond each
   Phase-B packet's sanctioned targets (`git diff 1772f40..96451fb` — Phase A's end through
   Phase B's end — is in scope).

## Output

Write ONLY `audits/phase-B-phase-end-fable-report.md`. Resolve to **sign_off / hold**
(hold = named, located conditions). Mandatory `WAYS_THIS_REVIEW_COULD_BE_WRONG` including
the same-family caveat. Do not touch STATUS.md, DECISIONS.md, ROADMAP.md, or any
per-packet auditor's own files. You never run git commands that mutate state (read-only
`git show`/`git diff`/`git log` are fine for citation purposes).
