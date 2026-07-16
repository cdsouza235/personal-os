# Personal OS — PRD v0.4

Status: draft for Conductor approval (adds §7 Knowledge Edge Daily Intelligence Queue,
D-PO-016; no prior revision archived — v0.3's content is unchanged elsewhere)
Owner: Chris · Updated: 2026-07-15
Development model: MIS harness (Builder=Opus, Auditor=Codex, Phase-End=Fable, Conductor=Chris)
Runtime host: Mac Mini · State: SQLite · Repo: `cdsouza235/personal-os` (private)

This document is the product spec only. Process/history live elsewhere: current state in
`governance/living/agent-writable/STATUS.md`, plan in `governance/ROADMAP.md`, safety in
`governance/` + `GOVERNANCE_MANIFEST.yaml`, history in git. This PRD does not carry a
changelog, PR lists, or per-phase boundary language — that is what killed v0.2.

## 1. Vision

A disciplined personal assistant, not a pile of automations. Personal OS keeps Chris's
routines, priorities, and follow-ups as editable local state; computes what matters today;
and — through deliberately activated rails — puts today's tasks in Todoist and today's
briefing in Gmail every morning without being touched.

Core division of labor: **Chris owns judgment, values, and approvals. The system owns
memory and cadence.** Routines change as life changes; the system adapts through state
edits, never code edits.

## 2. MVP (the shipping definition — D-PO-002)

Every morning, unattended:
1. The cadence engine computes today's due routines and surfaces current priorities.
2. Routine tasks for today are written to Todoist (permission-checked, ledger-deduped).
3. The 8am briefing is emailed via Gmail (template-generated from real state).
4. Chris edits routines/priorities via CLI, dashboard, or synthesis import; the next
   morning reflects it.

Acceptance = seven consecutive unattended mornings with correct tasks + briefing and zero
manual repair. Everything else in this PRD is post-MVP.

**Go-live gate (D-PO-016):** Personal OS may not be declared live on this MVP alone. Chris
has made the Knowledge Edge Daily Intelligence Queue (§7) launch-blocking — the routine/
Todoist/Gmail loop above and Knowledge Edge's own Phase 6 activation gate must both clear
before any rail goes live in production.

**Explicitly post-MVP:** Calendar writes · 12pm/4pm/8pm windows · model-generated briefing
prose (composer upgrade) · reports/chart-pack jobs · fitness v1.5.
**Cut:** OpenClaw (D-PO-004). **Untouchable:** the existing fitness CSV workflow.

## 3. Product surfaces

### 3.1 Routine engine (the brain — P-DESIGN-01/P-CORE)
State-driven, first-class schema (not a settings blob). Carried forward from v0.2 §14 as
the design input for G6 packet P-DESIGN-01:
- Cadence types: `daily`, `weekdays`, `x_times_per_week`, `weekly`, `every_n_days`,
  `specific_days`, `rotating_sequence`, `manual_only`.
- Missed behavior: `combine_with_next`, `bump_schedule_by_one_day`,
  `carry_forward_within_week`, `skip_and_continue`, `escalate_to_review`.
- Rotation groups, preferred windows, weekly targets, priority, `next_due`.
- Engine contract: pure functions — `(routine defs, completion history, date) → due set`.
  Deterministic, exhaustively table-tested, no I/O.
- Everything editable at runtime; adding a new routine or changing a cadence is a state
  edit through the editor surfaces, never a migration or code change.

Initial routines (seed data, not code): Cleaning (1/day weekdays) · Reading (4x/wk) ·
Prayer/Meditation (2x/wk) · Grease-the-Groove (rotating, 45 reps/exercise/wk) ·
Fitness/Strength (tracked externally, surfaced only) · Shutdown/Review (daily evening).

### 3.2 Priorities, projects, follow-ups
Registry with status, review cadence, next-review date, notes, source references (exists —
`priorities.py`/`state.py` — gains its user surfaces in P-CORE-03). High-value follow-ups
can become Todoist tasks through the same permission + ledger path as routines.

### 3.3 Briefing (P-BRIEF-01)
8am Morning Brief, America/Chicago. Content: today's due routines, priorities, carryovers,
follow-ups, warnings. MVP generator is a deterministic template over real state through
the existing pipeline (plan → window → preview → export/send). The v0.2 §18 composer
(narrow state packets in, structured JSON out, high-stakes filtered) returns post-MVP as
an upgrade behind the same contract.

### 3.4 Rails (`src/personalos/rails/` — Phase D)
Thin raw-HTTPS adapters (the proven smoke-client pattern, ~300 LOC each), each gated by:
permission model → idempotency/dedupe ledger → rail state (`inert|soaking|live`) →
credentials present (fail closed on missing). Activation is per-rail, Conductor-gated (G5),
with kill procedures (RUNBOOK). Order: Todoist → Gmail (longest soak; email is
irreversible) → Calendar (post-MVP).

### 3.5 Synthesis import (exists — keep)
Markdown/JSON/structured-text in → preview → Chris approves → apply into state (priorities,
projects, follow-ups; routine changes join in P-CORE). High-stakes candidates stay blocked
at the permission layer.

### 3.6 Dashboard + CLI (exists — extended in P-CORE-03)
Localhost-only dashboard: Today View, routine editor, priority editor, rail/system status.
No public exposure; no credential UI ever. CLI is the operator surface for everything the
dashboard does, plus `personalos run morning` (P-SCHED-01).

### 3.7 Scheduler (P-SCHED)
One LaunchAgent running the morning cycle. Manual-trigger first (soak), background
activation as its own G4+G5 gate with unload-proof. No other background execution exists.

## 4. Permissions (simplified from v0.2 §19)
- `routine_todoist_tasks`: auto-write **when todoist rail is live**
- `high_value_review_tasks`: auto-write when live
- `self_calendar_blocks`: post-MVP, auto-write when live
- Anything touching other people, money, legal/tax/medical, investments, relationships:
  **approval_required, always** (high-stakes domains, RISK_REGISTER §2)
One shared evaluator (P-DEBT-01). Fail closed; unknown category = approval_required.

## 5. Non-goals (standing)
Public internet exposure · multi-user · autonomous investment/legal/tax execution ·
reply parsing · local AI inference · OpenClaw (cut) · rebuilding the fitness CSV tracker ·
any rail auto-activating itself · Knowledge Edge placing trades, brokerage access, or
autonomous thesis/forecast changes (§7.2).

## 6. Data
SQLite via migrations (FK-enforced). All writes through core APIs. Personal content never
leaves the machine except through activated rails; committed artifacts (evidence, fixtures)
carry synthetic or redacted data only (SECURITY.md data classes). Production DB path +
backup/restore design lands with P-SCHED-02 (Q-PO-002). Knowledge Edge (§7) adds its own
tables to the same per-environment database via additive migrations, plus one isolated
shadow database for its pre-production soak — see `docs/knowledge_edge/
PHASE0_ARCHITECTURE_DECISIONS.md` for exact paths.

## 7. Knowledge Edge Daily Intelligence Queue (D-PO-016 — launch-blocking)

Full requirements: `docs/knowledge_edge/PRD_AMENDMENT_KNOWLEDGE_EDGE.md` (the durable
full record — this section is a distillation, not a replacement, mirroring how the
routine model's detail lives in D-PO-010 while PRD §3.1 carries the summary). Phase 0
planning: `docs/knowledge_edge/PHASE0_*.md`.

### 7.1 Product
A local-first Daily Intelligence Queue: the Mac mini discovers, normalizes, deduplicates,
and ranks high-signal content across four lanes — Curated Podcasts, Market Voices,
Consequential Leaders, Earnings & Corporate Events — and presents a finite, explainable
evening queue. Default full scan 4:30pm America/Chicago (queue ready ~4:45pm); 6:15am
refresh for same-day earnings changes; targeted T-60/T-15 link checks for watched live
events; manual scan-now always available. The system automates discovery, ranking,
deduplication, and reminders; Chris retains all judgment — watching, interpretation,
synthesis (ChatGPT), and promotion into Obsidian.

### 7.2 Scope boundaries (launch)
No trades, brokerage access, or financial advice; no autonomous thesis/forecast changes;
no full media/transcript downloads; no paywall/CAPTCHA/robots-directive bypass; no
live-model inference for discovery or ranking; no email, Calendar, or Todoist writes from
this module; no scheduler, notification, or Obsidian-write activation before its gated
session (below). Full non-goals: amendment §5.

### 7.3 Rollout gates (Sessions 1–3, layered on the standing HUMAN_GATES table)
Human involvement batches into three sessions on top of the existing G0–G-RECOVERY gates
(exact mapping: `docs/knowledge_edge/PHASE0_PLAN.md`). **Session 1** approves the Phase 0
plan, the D-YT YouTube-sourcing decision, and the full external-access bundle
(credentials, allowlists, entitlement artifacts) — pre-authorizing Packet 0C onward
against an isolated shadow database only, never production. **Session 2** approves final
empirical quality thresholds and shadow-configuration scheduler activation (the soak).
**Session 3** approves a bounded production smoke test, reviews pre-activation acceptance,
and approves production activation and Personal OS go-live. Packets 0C–5 run as one
autonomous stretch between Session 1 and Session 2, each major phase carrying a Codex
packet audit and a Fable phase-end audit reconciled before merge.

### 7.4 Providers
Earnings calendar: **Financial Modeling Prep rejected at real price (D-PO-019, Session 1,
2026-07-15) — replaced by a bounded, rule-defined company roster** (top 10 Nasdaq-100 +
top 3 publicly listed crypto-native companies + top 5 WGMI-ETF constituents, all ranked
by market cap, deduped, refreshed quarterly by the Conductor), sourced via SEC EDGAR
(free, no key) and the companies' official IR pages (already in the §10.3 allowlist).
Roster definition and seed list: `docs/knowledge_edge/PHASE0_ROSTER.md`. Broad
person-search provider and the D-YT YouTube-sourcing option are evaluated in
`docs/knowledge_edge/PHASE0_PROVIDERS_AND_ACCESS.md` and ratified at Session 1.

### 7.5 Module and data ownership
New domain package `src/personalos/knowledge_edge/` (state + deterministic engine,
network-blind, mirroring the cadence-engine purity invariant) and
`src/personalos/rails/knowledge_edge/` (read-only source adapters, inside the existing
network-capable `rails/**` boundary — invariant #6, no new network-capability grant
needed). One production database (the D-PO-011 file, additive migrations only) plus one
isolated shadow database for Session-1-authorized pre-production runs. Full design:
`docs/knowledge_edge/PHASE0_ARCHITECTURE_DECISIONS.md`.
