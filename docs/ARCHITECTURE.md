# Personal OS — Architecture v0.3

Status: draft for Conductor approval (replaces v0.2; v0.2 → `docs/archive/`)
Updated: 2026-07-07

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

## Current-state delta (what exists today vs the diagram)
Exists: state layer, migrations, synthesis import/apply, ledgers, no-send briefing
pipeline, Today View, dashboard shell, permission tables. Missing: cadence engine
(P-CORE), routine/priority user surfaces (P-CORE-03), template generator (P-BRIEF-01),
rails/ (Phase D), scheduler (P-SCHED). Being deleted: phase-14C process layer, readiness
machinery, dead skeletons (P-CLEAN). See `governance/ROADMAP.md`.
