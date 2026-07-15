# DECISIONS.md — Personal OS (durable decisions; Builder-owned; reversals per SPEC §16.9)

## Locked
- **D-PO-001 Re-baseline in place.** Keep the code (291 commits); replace the governance
  shape (doc-sprawl narrative process → harness-standard machine-checked gates); findings
  audit seeds the ROADMAP. Neither blind-continue nor restart. — Chris, 2026-07-07
- **D-PO-002 MVP = the live morning loop.** Cadence engine computes today; routine tasks
  → Todoist; 8am briefing → Gmail; unattended after P-SCHED-02. Calendar + midday/evening
  windows post-MVP. Flexibility-as-routines-change is a first-class design requirement;
  zero bias toward incumbent design. — Chris, 2026-07-07
- **D-PO-003 Docs retire freely.** No legacy doc is personally load-bearing; all ~25
  phase/readiness docs + old STATUS archive out in P-GOV-01. SAFETY_POLICY content folded
  into RISK_REGISTER/SECURITY (its posture-flag vocabulary is retired with the readiness
  machinery). — Chris, 2026-07-07
- **D-PO-004 OpenClaw is cut.** Its operator role is filled by the harness + P-SCHED
  scheduler; model calls (if ever) go through a rails adapter. The fitness CSV workflow it
  served stays untouched and out of product scope. Re-entry requires a new G6. — proposed
  by Phase 0 findings §7; Conductor "best proposal wins" (2026-07-07); **ratified by
  approving P-GOV-01**.
- **D-PO-005 Governance authorship seam.** The rulebook is authored by the Fable
  (architect/phase-end) seat + Conductor, audited cross-family by Codex; the production
  Builder (Opus) never authors governance (D-004 circularity principle). Same-family
  caveat (Fable/Opus both Anthropic) is carried openly; the Codex audit + live-loop
  adversarial audits are the designed backstop. — 2026-07-07
- **D-PO-006 `not_ready` is retired as a concept.** Replaced by the per-rail activation
  ladder (`inert | soaking | live`, HUMAN_GATES) with Conductor-gated transitions. The
  three by-construction not-ready mechanisms (Phase 0 §5, §8.5) are deleted with
  P-CLEAN-02 rather than satisfied. — 2026-07-07

- **D-PO-007 Governance lives in-repo (Model B) + templates adopted.** The rulebook is a
  self-contained overlay in this repo (`governance/**` + manifest) because the agent
  build-sandbox receives a git-free export of THIS repo — in-repo law is visible to the
  governed agent with no extra B-00 mounting; the portable doctrine (SPEC/LOOP_DOCTRINE)
  stays harness-side, so there is no rulebook duplication (SPEC §7 overlay split). The
  Conductor's `_harness_proposal/` bundle (archived at `archive/harness-proposal/`)
  recommended harness-side (Model A) as its lean; its two templates were adopted into
  `governance/templates/` and its principles were already convergent with the pack.
  Revisit at B-00 (recorded there as an explicit onboarding question); reversal would be
  a G-GOV migration packet. Also fixes Codex plan-audit F7/F9: approvals =
  `audits/signoffs/**`, Conductor-only, manifest-protected. — 2026-07-07

- **D-PO-008 R1(a) ratification.** The Conductor ratifies the P-GOV-01 sign-off embedded
  in packet commit `02951b5` as his own authorship ("I ratify the P-GOV-01 sign-off
  embedded in 02951b5 as mine" — Chris, 2026-07-07, transcribed by Builder per D-014).
  Context: the Fable phase-A checkpoint (R1) found the sign-off entered the tree inside
  the packet build commit — unavoidable bootstrap circularity, as the sign-off store was
  created by that same packet. With this ratification the Phase A approval trail is
  complete. — 2026-07-07
- **D-PO-009 HI-11/Q-PO-004: B-00 first (Option B).** Phase B is preceded by **B-00**
  (harness repo: production CLI + project onboarding, hand-built + Codex/Fable audited,
  NOT dogfooded per SPEC §11). Rationale: the manual loop spent three audit rounds on
  approval-provenance issues that B-00's OS-permissioned approval store prevents by
  construction (closes checkpoint carry R1(b)); the upcoming product stretch
  (P-DESIGN-01 → P-CORE, migrations + engine) is exactly what the orchestrator should
  mechanically enforce. P-DESIGN-01 starts after B-00 drives its first personal-os
  packet. — Chris, 2026-07-07
- **D-PO-010 Routine model + cadence engine design.** Replaces the semantics-free
  `settings_json` blob (Phase 0 finding) with first-class columns on the routine record:
  `cadence_type`, `cadence_config_json` (cadence-specific parameters only, not
  general-purpose state), `missed_behavior_default`, `rotation_group`, `weekly_target`.
  Carries forward the PRD §3.1 baseline cadence types (`daily`, `weekdays`,
  `x_times_per_week`, `weekly`, `every_n_days`, `specific_days`, `rotating_sequence`,
  `manual_only`) and baseline missed-behavior types (`combine_with_next`,
  `bump_schedule_by_one_day`, `carry_forward_within_week`, `skip_and_continue`,
  `escalate_to_review`); adds three new cadence types: `weekly_target_count` (N
  completions anywhere in the week, order-independent), `weekly_target_reps` (a
  rep/quantity target per week, not just a completion count), and
  `rotating_weekday_pool` (a pool of tasks rotating across specific weekdays, distinct
  from the existing generic `rotating_sequence`). Fixed ISO week: all
  `weekly`/`weekly_target_*` accounting uses a fixed Monday–Sunday calendar week, not a
  rolling trailing-7-days window; a weekly target resets at the Monday boundary
  regardless of when in the prior week it was completed. Grease-the-Groove is modeled as
  individual routine rows (one per exercise), all sharing `rotation_group = "gtg"`;
  monthly focus is expressed purely via each row's existing `enabled` flag (enabled rows
  are this month's focus set; no new focus/month field). GTG progress reporting is
  reply-based (email or Todoist reply), the same channel used for the cleaning
  missed-behavior mechanism below, not a dashboard/CLI primary path. Cleaning is a pool
  of 15-20 distinct tasks sharing one `rotation_group` (e.g. `"cleaning"`), advancing
  through the pool one task per due occurrence; unlike routines with a static
  `missed_behavior_default`, a missed cleaning occurrence's handling is chosen
  dynamically, per-occurrence, by Chris's reply (email or Todoist reply) at the time it's
  missed — `missed_behavior_default` is the fallback if no reply arrives, the reply when
  given overrides it for that one occurrence only, carried by the engine's
  `occurrence_overrides` parameter. Engine contract (pure function, no I/O, exhaustively
  table-tested): `compute_due_and_owed(routines, completions, *, as_of_date,
  occurrence_overrides={})` — takes routine definitions, completion history, the date to
  compute for, and an optional per-occurrence override map (keyed by routine+due-date);
  returns the due-today set and any "owed" make-up debt from weekly-target shortfalls;
  deterministic. Seed list confirmed unchanged from PRD §3.1: Cleaning (rotating pool,
  1/day weekdays) · Reading (4x/wk, `weekly_target_count`) · Prayer/Meditation (2x/wk,
  `weekly_target_count`) · Grease-the-Groove (per-exercise rows, `rotation_group="gtg"`,
  `weekly_target_reps` for 45 reps/exercise/wk) · Fitness/Strength (tracked externally,
  surfaced only, unchanged, no schema involvement) · Shutdown/Review (daily evening,
  unchanged `daily`). Scope note: the orphaned `src/personalos/fitness.py` module's
  disposition (Q-PO-001, a P-DEBT-03 decision) is explicitly NOT part of this decision —
  GTG and Fitness/Strength above are routine-engine seed data only. Formalizes the
  Conductor design decision ahead of P-CORE. — Chris, 2026-07-08

- **D-PO-011 Production DB location + backup design (HI-09, closes Q-PO-002).** The production
  SQLite database lives at `/Users/coldstake/PersonalOS/personal_os.db` — the existing protected
  external path already reserved in `governance/SECURITY.md`/`RISK_REGISTER.md` ("never inside
  any packet scope"), not a new location. Backup mechanism: SQLite's own Online Backup API
  (`sqlite3 <source> ".backup <dest>"`, or the equivalent `sqlite3.Connection.backup()` call),
  run on a schedule — NOT a raw filesystem copy, which risks capturing a torn/inconsistent
  snapshot if a write is in progress when the copy happens; the Online Backup API guarantees a
  consistent copy regardless of concurrent activity. Time Machine (or equivalent existing Mac
  backup) remains a SECONDARY safety net for catastrophic disk loss, not the primary defense
  against backup corruption. A restore-drill procedure (documented steps a human follows to
  restore from the `.backup` snapshot) is part of P-SCHED-02's own acceptance, not a separate
  decision. Unblocks P-SCHED-02 (background scheduler activation), which requires HI-09 resolved
  per `audits/human-input-manifest.md`. — Chris, 2026-07-10

- **D-PO-012 P-DEBT-03 orphan disposition (closes Q-PO-001, HI-03).** `fitness.py` (1207 LOC),
  `reports.py` (1252 LOC), `completion.py` (155 LOC) — all "dev/test-only foundation" modules with
  zero non-test imports anywhere in the product code, and no roadmap packet ever planned to wire
  any of them in (unlike `routines.py`/`todoist.py`, which both had real follow-up packets).
  Delete all three. `runtime_bootstrap.py` (1086 LOC) is explicitly OUT of this decision — unlike
  the other three, it IS actively used, by multiple test files' own bootstrap/setup path
  (`test_briefings.py`, `test_synthesis_import.py`, `test_today_dashboard.py`, `test_scheduler.py`,
  `test_cli.py`) — it stays, already correctly disposed as dev/test infrastructure, not a product
  orphan. — Chris, 2026-07-10

- **D-PO-013 Calendar rail OAuth identity + target calendar (closes HI-12).** The OAuth
  credentials (`PERSONALOS_RAIL_CALENDAR_CLIENT_ID`/`_CLIENT_SECRET`/`_REFRESH_TOKEN`) authenticate
  as the sandboxed account (`cdsouza.bot@gmail.com`), not Chris's personal Google account — the
  bot identity holds the credentials, keeping blast radius contained to whatever's been explicitly
  shared with it. `PERSONALOS_RAIL_CALENDAR_CONTROLLED_CALENDAR_ID` is set to Chris's real personal
  calendar (`cdsouza235@gmail.com`), not the bot's own — writable because that calendar has been
  explicitly shared with the bot account with edit permission. Chris chose to point at the real
  calendar from the first live test rather than soak on a throwaway calendar first (the
  lower-risk option offered), given the bot-identity/personal-calendar split already contains most
  of the risk a fully personal-account setup would carry. Unblocks P-RAIL-CAL-02. — Chris,
  2026-07-13

## Reversals

- **R-PO-001 (2026-07-14) partially reverses D-PO-010's Grease-the-Groove disposition.**
  D-PO-010 modeled GTG as individual routine rows sharing `rotation_group = "gtg"`, cadence
  type `weekly_target_reps` (45 reps/exercise/wk), in-schema like Cleaning/Reading. When
  actually working through how rep progress would get logged day to day (given R-PO-001's
  same-day context: the 4x/day check-in loop dropped reply-based state updates in favor of
  Todoist-completion-as-state), no clean fit emerged — GTG is fundamentally incremental/
  rep-accumulating, not a single completable unit, and modeling it as many small discrete
  "round" tasks was offered but Chris declined it. Chris's call: GTG moves OUT of the
  routine-model schema entirely and gets folded into a separate, more comprehensive fitness-
  tracking system he'll design on his own timeline — the SAME disposition D-PO-010 already
  gave "Fitness/Strength (tracked externally, surfaced only, unchanged, no schema
  involvement)," just extended to cover GTG too. PersonalOS's own routine engine/schema has
  no GTG involvement going forward; if/when the external fitness system exists, PersonalOS
  may surface a read-only summary of it, matching the existing Fitness/Strength pattern —
  not decided yet, not blocking anything. D-PO-010's OTHER content (cadence types, Cleaning/
  Reading/Stillness/Shutdown-Review modeling, the `compute_due_and_owed` engine contract)
  is UNCHANGED and still in force — only the GTG-specific portion is reversed. — Chris,
  2026-07-14
