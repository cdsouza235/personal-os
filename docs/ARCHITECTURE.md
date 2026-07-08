# Personal OS — Architecture v0.4

Status: draft for Conductor approval (replaces v0.3; v0.3 → `docs/archive/`)
Updated: 2026-07-08

## System shape (target, post Phase B–D)

```
                 ┌─ CLI (operator; personalos …)
 Chris edits ────┤
                 └─ Dashboard (localhost) ──┐
                                            ▼
   synthesis import ──▶ preview ──▶ apply ─▶ SQLite state (migrations, FK, core APIs)
                                            │
                              cadence engine (pure fns: defs+history+date → due set)
                                            │
                                     morning cycle (scheduler)
                                            │
                    briefing generator ─────┼───── task planner
                            │               │           │
                            ▼               ▼           ▼
                     permission model → ledgers/dedupe → rails/  (state: inert|soaking|live)
                            │                              ├─ todoist (MVP)
                            │                              ├─ gmail   (MVP)
                            └── high-stakes → blocked      └─ calendar (post-MVP)
```

## Critical invariants (machine-checkable; RISK_REGISTER triggers reference these)
1. **Single write path:** all state mutation goes through core APIs; schema only via
   `migrations/**`.
2. **Engine purity:** cadence computation is side-effect-free; no I/O, no clock reads
   (date is an argument).
3. **Rail gating order is fixed:** permission → ledger/dedupe → rail-state → credentials;
   a rail write with any check unsatisfied fails closed and ledgers the refusal.
4. **One permission evaluator** (post P-DEBT-01); no module carries a private copy.
5. **No background execution** other than the one P-SCHED LaunchAgent.
6. **Network capability is enumerated:** only `rails/**` (and the manifest-listed legacy
   smoke modules until P-CLEAN-02) may import network primitives.
7. **Localhost-only UI; no credential values in repo, state, logs, or UI.**

## Layering rules
- `state.py` (→ split per P-DEBT-02) knows nothing of rails or briefings.
- Engine knows state shapes, not rails.
- Generators (briefing/task-planning) consume engine output; only rails touch the world.
- Governance/process artifacts live in `governance/` + `audits/`, never imported by product
  code (the Phase 0 today.py↔readiness coupling is dissolved in P-CLEAN-02).

## Routine model (target design — D-PO-010; ships in P-CORE-01/02)
Replaces the semantics-free `settings_json` blob with first-class columns on the routine
record: `cadence_type`, `cadence_config_json` (cadence-specific parameters only, not
general-purpose state), `missed_behavior_default`, `rotation_group`, `weekly_target`.

- **Cadence types:** baseline `daily`, `weekdays`, `x_times_per_week`, `weekly`,
  `every_n_days`, `specific_days`, `rotating_sequence`, `manual_only` (PRD §3.1), plus
  `weekly_target_count` (N completions anywhere in the week, order-independent),
  `weekly_target_reps` (a rep/quantity target per week, not just a completion count),
  and `rotating_weekday_pool` (a pool rotating across specific weekdays, distinct from
  the generic `rotating_sequence`).
- **Missed behavior:** `combine_with_next`, `bump_schedule_by_one_day`,
  `carry_forward_within_week`, `skip_and_continue`, `escalate_to_review` — set per
  routine via `missed_behavior_default`; a single occurrence may be overridden
  dynamically at compute time (see `occurrence_overrides` below).
- **Fixed ISO week:** all `weekly`/`weekly_target_*` accounting uses a fixed Monday–
  Sunday calendar week, not a rolling trailing-7-days window; a weekly target resets at
  the Monday boundary regardless of when in the prior week it was completed.
- **Grease-the-Groove:** modeled as individual routine rows (one per exercise), all
  sharing `rotation_group = "gtg"`. Monthly focus is expressed purely via each row's
  existing `enabled` flag (enabled rows are the current month's focus set; disabled rows
  sit dormant until their month comes up) — no new focus/month field. Progress reporting
  is reply-based (email or Todoist reply), the same channel as the cleaning
  missed-behavior mechanism below, not a dashboard/CLI primary path.
- **Cleaning:** a rotating pool of 15-20 distinct tasks sharing one `rotation_group`
  (e.g. `"cleaning"`), advancing through the pool one task per due occurrence. Unlike
  routines with a static `missed_behavior_default`, a missed cleaning occurrence's
  handling is chosen dynamically, per-occurrence, by Chris's reply (email or Todoist
  reply) at the time it's missed; `missed_behavior_default` is the fallback if no reply
  arrives, and the reply, when given, overrides it for that one occurrence only.
- **Engine contract** (pure function, no I/O, exhaustively table-tested):
  `compute_due_and_owed(routines, completions, *, as_of_date, occurrence_overrides={})`
  — takes the full routine definitions and completion history, the date to compute for,
  and an optional per-occurrence override map (keyed by routine + due-date, carrying a
  one-off missed-behavior choice such as the cleaning reply above); returns the
  due-today set and any "owed" make-up debt from weekly-target shortfalls.
  Deterministic: same inputs always produce the same output. This is the concrete shape
  of critical invariant #2 (engine purity) above.

Out of scope for this design: the orphaned `src/personalos/fitness.py` module's
disposition (Q-PO-001, a P-DEBT-03 decision) — Grease-the-Groove and Fitness/Strength
seed data reference the routine engine only and do not depend on that module.

## Current-state delta (what exists today vs the diagram)
Exists: state layer, migrations, synthesis import/apply, ledgers, no-send briefing
pipeline, Today View, dashboard shell, permission tables. Missing: cadence engine
(P-CORE), routine/priority user surfaces (P-CORE-03), template generator (P-BRIEF-01),
rails/ (Phase D), scheduler (P-SCHED). Being deleted: phase-14C process layer, readiness
machinery, dead skeletons (P-CLEAN). See `governance/ROADMAP.md`.
