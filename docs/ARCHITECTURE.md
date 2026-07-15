# Personal OS — Architecture v0.5

Status: draft for Conductor approval (adds the Knowledge Edge module shape and invariant
#5 rewording, D-PO-016; no prior revision archived — v0.4's content is unchanged elsewhere)
Updated: 2026-07-15

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

## System shape — Knowledge Edge (target, Phase 0–6; D-PO-016, launch-blocking)

A parallel pipeline, sharing the dashboard shell, the SQLite file, and the `rails/**`
network boundary, but its own domain package and its own scheduler agent (see invariant
#5 below). Full design: `docs/knowledge_edge/PHASE0_ARCHITECTURE_DECISIONS.md`.

```
 due-work dispatcher (Knowledge Edge LaunchAgent, Session 2/3-gated) ──┐
                                                                       ▼
   rails/knowledge_edge/ (podcasts, youtube, earnings_calendar,   scan orchestrator
   sec_edgar, person_search — read-only, credential-gated)  ◀────────┤
                                                                       │
                                        knowledge_edge/engine/ (pure: canonicalize,
                                        directness, dedup, ranking, thesis matching)
                                                                       │
                                                                       ▼
                                        knowledge_edge/state/ (registries, media,
                                        events, decisions, scan health, synthesis)
                                                                       │
                                                                       ▼
                              Dashboard (localhost, new KE routes) ──▶ Chris triages
                                                                       │
                                                        synthesis handoff → ChatGPT/Obsidian
                                                        (staging only until Session 3)
```

## Critical invariants (machine-checkable; RISK_REGISTER triggers reference these)
1. **Single write path:** all state mutation goes through core APIs; schema only via
   `migrations/**`.
2. **Engine purity:** cadence computation is side-effect-free; no I/O, no clock reads
   (date is an argument). Knowledge Edge's own engine (`knowledge_edge/engine/`) carries
   the identical purity rule: canonicalization, directness classification, deduplication,
   ranking, and thesis matching are pure functions over already-fetched records — no
   network or clock access inside `engine/`.
3. **Rail gating order is fixed:** permission → ledger/dedupe → rail-state → credentials;
   a rail write with any check unsatisfied fails closed and ledgers the refusal.
   Knowledge Edge's adapters are read-only discovery, not writes to Chris's accounts, so
   the permission/ledger legs of this gate do not apply to them the same way; the
   credentials-present, fail-closed leg still applies unconditionally (see
   `docs/knowledge_edge/PHASE0_ARCHITECTURE_DECISIONS.md`).
4. **One permission evaluator** (post P-DEBT-01); no module carries a private copy.
5. **No background execution other than the approved P-SCHED LaunchAgent(s):** the
   morning-brief fixed-time agent (`com.personalos.morning`) and, once its own Session
   2/3 gate clears, the Knowledge Edge due-work dispatcher agent — two independently
   unload-proof-verifiable LaunchAgents, never a single shared one (D-PO-016; see
   `docs/knowledge_edge/PHASE0_ARCHITECTURE_DECISIONS.md` for the reconciliation this
   rewording records). No other background/daemon/watcher process is permitted.
6. **Network capability is enumerated:** only `rails/**` (and the manifest-listed legacy
   smoke modules until P-CLEAN-02) may import network primitives. Knowledge Edge's
   adapters live at `src/personalos/rails/knowledge_edge/**`, inside this same glob — no
   manifest/RISK_REGISTER edit is required to grant them network capability.
7. **Localhost-only UI; no credential values in repo, state, logs, or UI.**

## Layering rules
- `state.py` (→ split per P-DEBT-02) knows nothing of rails or briefings.
- Engine knows state shapes, not rails.
- Generators (briefing/task-planning) consume engine output; only rails touch the world.
- Governance/process artifacts live in `governance/` + `audits/`, never imported by product
  code (the Phase 0 today.py↔readiness coupling is dissolved in P-CLEAN-02).
- Knowledge Edge mirrors this exactly at smaller scope: `knowledge_edge/state/` knows
  nothing of `rails/knowledge_edge/`; `knowledge_edge/engine/` knows state shapes, not
  rails; only the scan orchestrator and `rails/knowledge_edge/**` touch the network.

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

**Knowledge Edge (D-PO-016, launch-blocking, Phase 0 of 7 complete as of this edit):**
none of `src/personalos/knowledge_edge/`, `src/personalos/rails/knowledge_edge/`, its
migrations, its dashboard routes, or its LaunchAgent exist yet — Packet 0B is a
documents-and-decisions packet only. See `docs/knowledge_edge/PHASE0_PLAN.md` for the
phase/packet sequence and `docs/knowledge_edge/PHASE0_ARCHITECTURE_DECISIONS.md` for the
module/data design Packet 1A implements against.
