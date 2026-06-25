# Personal OS - Master PRD / Architecture Brief v0.2

Status: Updated working draft for review
Owner: Chris
Updated: 2026-06-25
Development model: ChatGPT + Codex/Fable + OpenClaw
Product: Personal OS
Runtime host: Mac Mini
Code source of truth: private GitHub repo `cdsouza235/personal-os`
Local repo: `/Users/coldstake/dev/personal-os`
Structured runtime state: SQLite
Durable notes / memory: PersonalOS / Obsidian / Markdown
Runtime/operator layer: OpenClaw, only after approved runtime workflows exist

## 0. v0.2 Revision Summary

This v0.2 revision updates the original Master PRD / Architecture Brief so it
matches the current repo state instead of the older Phase 0-era roadmap wording.

Key changes from v0.1:

- Clarifies that the project is not starting from scratch.
- Records the current repo baseline by pointing to `../STATUS.md` as the
  canonical snapshot:
  - last validated main baseline after PR #61:
    `16a71bc6c8f500d5c21c9329586698f3156b9f92`
  - latest merged PR: PR #61, Phase 14-C decision-support strict readiness
    status validation
  - current post-merge validation is recorded in `../STATUS.md`
  - readiness remains `not_ready`
  - `inert_report_only=true`
  - `live_rails_activated=false`
- Clarifies that Codex/Fable owns repo implementation, tests, docs,
  migrations, PRs, and validation.
- Clarifies that OpenClaw is not the repo implementation layer and should not
  perform repo work unless explicitly authorized later for a narrow
  runtime/operator smoke test.
- Reframes future V1 live rails as product targets, not current permission to
  activate Gmail, Todoist, Calendar, PersonalOS Markdown writes, OpenClaw
  runtime integration, production DB, scheduler, or model/API calls.
- Records Phase 14-A/B preparation as proposed-only first-live pilot design
  plus inert fail-closed scaffolding. It does not authorize or run a live
  pilot.
- Records pre-Phase-14-C candidate-selection preparation as inert
  process/template/validator scaffolding. It records Clean Kitchen Countertops
  and Stovetop for candidate-review tracking only and does not approve,
  authorize, or activate live execution.
- Records the Phase 14-C candidate decision gate as inert docs/test-only
  future approval criteria. It does not approve Phase 14-C, approve the
  candidate, authorize execution, authorize live service access, implement
  dynamic cleaning, adopt Watch Tower, add `.agent/`, add `CLAUDE.md`, or add
  runtime/operator scaffolding.
- Records the Phase 14-C candidate decision-support bundle as an inert
  docs/test-only review aid with an unfilled false-default template. It does
  not select approve, reject, or defer.
- Records the Phase 14-C candidate decision-support validator as an inert
  source/test report layer for that unfilled template. It blocks filled
  decision records, approval flags, authorization flags, activation flags, live
  service fields, credential/secret fields, live IDs, unknown schema fields,
  nested payloads under known fillable fields, dynamic cleaning flags,
  Watch Tower flags, `.agent/`, `CLAUDE.md`, and runtime/operator scaffolding
  flags. It does not record a decision or authorize live work.
- Adds a repository documentation standard: keep the canonical PRD as Markdown
  inside `docs/`, keep a concise `AGENTS.md` in the repo root for Codex/Fable
  operating instructions, and use DOCX as a review/export artifact rather than
  the machine-readable source of truth.

## 1. Product Vision

Personal OS is a modular, local-first productivity, routine, priority, and
execution operating system.

It helps Chris think clearly, capture and maintain priorities, execute daily
routines, track high-value projects, generate useful briefings, create Todoist
tasks, schedule Calendar blocks, preserve durable notes without bloat, run
reports and dashboards, and operate approved runtime workflows on the Mac Mini.

The system should feel like a disciplined personal assistant, not a pile of
automations.

Core concept:

- Chris owns judgment, values, approvals, and final decisions.
- ChatGPT synthesizes raw input into clean priorities, state, requirements,
  review artifacts, and implementation instructions.
- Codex/Fable builds and validates the repo software.
- OpenClaw operates approved runtime workflows after the repo is ready and
  Chris approves.
- SQLite stores structured runtime state.
- PersonalOS / Obsidian / Markdown stores durable notes, logs, protocols,
  reviews, and long-term context.
- Todoist, Google Calendar, Gmail, and other rails stay behind permission gates
  and validation.

## 2. Problem Statement

Chris has the pieces of a personal operating system, but the long-term value
depends on keeping them cleanly layered:

- ChatGPT for synthesis and analysis.
- Codex/Fable for repo implementation.
- SQLite for structured runtime state.
- OpenClaw on the Mac Mini for approved runtime operation.
- Todoist for concrete actions.
- Google Calendar for real time commitments.
- Gmail for briefings and communication rails.
- PersonalOS / Obsidian / Markdown for durable notes and long-term memory.
- TradingView and market inputs for chart-pack workflows.

Current risks include inconsistent routine execution, scattered priorities,
Todoist/Calendar drift, incomplete briefing integration, manual relay between
tools, note bloat, and accidental live activation before the system is ready.

The repo has now advanced beyond the original early roadmap. The next problem is
not foundation creation. The next problem is proving the existing inert
foundations compose safely in one deterministic no-send workflow before any live
rail work begins.

## 3. Core Roles And Boundaries

### Chris

Chris is the owner, final approver, and source of values, priorities, and
judgment.

Chris approves:

- Product direction.
- Phase scope.
- PR merges.
- Live rail activation.
- High-stakes decisions.
- Runtime/operator use.

### ChatGPT

ChatGPT is the strategy, synthesis, PRD, architecture, acceptance criteria,
audit, review, and instruction-writing layer.

ChatGPT should:

- Synthesize messy input before execution.
- Separate raw notes, durable insights, emotional spikes, recurring patterns,
  action candidates, PersonalOS updates, Todoist-ready tasks, and questions for
  review.
- Produce clean Codex/Fable prompts for repo implementation.
- Produce OpenClaw instructions only after runtime/operator work is approved.
- Review and audit builder/operator reports.

ChatGPT should not treat raw emotional notes, altered-state notes, or passing
ideas as automatic tasks, beliefs, goals, or permanent memory.

### Codex / Fable

Codex/Fable is the repo implementation layer.

Codex/Fable may, within approved phase scope:

- Create branches.
- Edit code, tests, docs, fixtures, migrations, and repo protocols.
- Run unit and integration tests.
- Run local simulation scripts.
- Prepare PRs.
- Report implementation evidence.

Codex/Fable may not, unless explicitly approved in a future live phase:

- Send email.
- Write Todoist tasks.
- Write Calendar events.
- Load credentials/OAuth.
- Activate LaunchAgents, crontab, daemons, scheduler loops, or background jobs.
- Mutate production SQLite state.
- Modify production ledgers.
- Inspect or mutate `/Users/coldstake/PersonalOS` or
  `/Users/coldstake/.openclaw` unless specifically authorized.
- Run live OpenClaw workflows.
- Perform external writes.

### OpenClaw

OpenClaw is the runtime/operator layer, not the repo implementation layer.

OpenClaw eventually runs approved local jobs, creates approved
tasks/events/drafts/writes, manages runtime workflows, and produces
logs/reports. It should receive clean approved instructions, not raw
unstructured project material.

OpenClaw should not handle repo implementation, PR review, merges, validation,
or development work unless Chris later explicitly chooses it for a narrow
runtime/operator smoke test.

### Mac Mini

The Mac Mini is the always-on runtime host for the local Personal OS runtime,
OpenClaw, SQLite, repo clone, scheduler, and local files once live operation is
approved.

### GitHub

GitHub is the private source of truth for code, tests, docs, schemas,
migrations, fixtures, module definitions, and development workflow docs.

## 4. Product Principles

1. Clean state first.
   Raw input goes through synthesis before storage or execution.

2. Editable state, not hardcoded routines.
   Routine changes should be state/config driven, not code edits.

3. Narrow model packets.
   Composer/model calls should receive only narrow, validated state packets.

4. Execution is validated.
   Composer output must be structured, schema-valid, permission-gated, and
   deduplicated before execution.

5. Safety-light UX, safety-aware architecture.
   The UI should not feel paranoid, but architecture must include permissions,
   ledgers, idempotency, rollback/recovery posture, logs, completion reports,
   and explicit safety flags.

6. No-send before send.
   Any live external rail should first exist as preview/simulation/no-send
   evidence.

7. Local-first, modular growth.
   Future modules should plug into the same state, dashboard, scheduler,
   composer, permission, and evidence layers.

8. High-stakes review stays explicit.
   Tax, legal/estate, portfolio/crypto/investments, relationship messages,
   health/medical decisions, large financial commitments, family conflict, and
   emotionally charged communication require extra review before execution.

## 5. Source-Of-Truth And Documentation Architecture

### Canonical Source Locations

- Code, tests, schemas, migrations, fixtures: GitHub repo,
  `/Users/coldstake/dev/personal-os` locally.
- Canonical PRD for Codex/Fable: `docs/PRD.md`.
- Architecture detail: `docs/ARCHITECTURE.md`.
- Safety policy: `docs/SAFETY_POLICY.md`.
- Roadmap: `docs/ROADMAP.md`.
- Codex/Fable development workflow: `docs/CODEX_WORKFLOW.md`.
- Phase runbooks: `docs/PHASE_*.md`.
- Repo-level agent instructions: `AGENTS.md` at repo root.
- Structured runtime state: SQLite.
- Durable personal notes later: PersonalOS / Obsidian / Markdown.

### Recommended Repo Documentation Pattern

The PRD should be in the repo, but not as a loose root-level DOCX.

Recommended pattern:

```text
/Users/coldstake/dev/personal-os/
  AGENTS.md
  README.md
  docs/
    PRD.md
    ARCHITECTURE.md
    SAFETY_POLICY.md
    ROADMAP.md
    CODEX_WORKFLOW.md
    PHASE_13E_D_SYNTHETIC_NO_SEND_DEMO.md
    archive/
      Personal_OS_Master_PRD_Architecture_Brief_v0_1.docx
```

`docs/PRD.md` is the canonical machine-readable PRD that Codex/Fable can
reference every session. The Word document is useful for human review, sharing,
and archival snapshots, but Markdown is the repo source of truth.

`AGENTS.md` should stay concise. It should point Codex/Fable to the relevant
docs, state the hard safety boundaries, list validation commands, and define
stop conditions. It should not become the full PRD.

## 6. Current Repo State Reconciliation

The canonical current snapshot is `../STATUS.md`. This PRD records the current
product baseline, but `../STATUS.md` remains the source of truth for the latest
post-merge validation.

As of this post-merge validation update after PR #61:

- Last validated main baseline after PR #61:
  `16a71bc6c8f500d5c21c9329586698f3156b9f92`
- Latest merged PR: PR #61, Phase 14-C decision-support strict readiness status validation
- PR #45 Claude Code audit: Pass
- PR #47 Claude Code audit: Pass
- PR #48 Claude Code audit: Pass
- PR #49 Claude Code audit: Pass
- PR #50 Claude Code audit: Pass
- PR #51 Claude Code audit: Pass
- PR #52 Claude Code audit: Pass
- PR #53 Claude Code audit: Pass
- PR #54 Claude Code audit: Pass
- PR #55 Claude Code audit: Pass
- PR #56 Claude Code audit: Pass
- PR #57 Claude Code audit: Pass
- PR #58 Claude Code audit: Pass
- PR #59 Claude Code audit: Pass
- PR #60 Claude Code audit: Pass
- PR #61 Claude Code audit: Pass
- Completed through: Phase 14-A/B preparation on `main`; pre-Phase-14-C
  candidate-selection preparation is implemented on `main` and post-merge
  validated; long-run repo workflow and Claude Code audit triage protocols are
  codified in repo docs; Phase 14-C candidate decision-support docs are merged
  on `main`
- Current/next phase: candidate-selection process prepared; one future
  Todoist candidate is recorded for candidate-review tracking only; the
  Phase 14-C candidate decision gate records future approval requirements;
  Phase 14-C live pilot remains blocked pending explicit candidate approval
  and live authorization
- Phase 14 live pilot: not started; no pilot authorized or run
- Full test suite: 539 tests OK
- ResourceWarning-sensitive suite: 539 tests OK
- Hygiene clean
- No repo-local `var/`
- No SQLite/DB artifacts outside `.git`
- Readiness reports `not_ready`
- `inert_report_only=true`
- `live_rails_activated=false`
- All live rails disabled
- No credentials loaded/read
- No production DB active
- No scheduler active
- No LaunchAgent, crontab, daemon, or background loop active
- No external writes
- No OpenClaw call
- Dashboard has no activation controls
- Dashboard has no credential/OAuth UI
- Phase 14-A/B preparation found no exact concrete validated Phase 13G Todoist
  candidate to select automatically; human selection is required before any
  future live authorization packet
- Pre-Phase-14-C candidate-selection preparation adds an inert
  process/template/validator path on `main`
- Human review result recorded for future authorization review: Clean Kitchen
  Countertops and Stovetop, Monday, Kitchen, household cleaning routine task,
  selected for candidate-review tracking only
- No Todoist candidate is approved, authorized, activated, or run
- Phase 14-C candidate decision-gate documentation is
  [PHASE_14C_DECISION_GATE.md](PHASE_14C_DECISION_GATE.md). It is an inert
  approval boundary and evidence checklist only.
- Phase 14-C candidate decision-support documentation is
  [PHASE_14C_CANDIDATE_DECISION_SUPPORT.md](PHASE_14C_CANDIDATE_DECISION_SUPPORT.md).
  It is an inert review checklist and unfilled false-default template only.
- Phase 14-C candidate decision-support validation is
  `src/personalos/phase14c_candidate_decision_support.py`. It validates only
  the unfilled false-default decision-support record/report and blocks unsafe
  filled records, including unknown schema fields, nested payloads under known
  fillable fields, every fillable decision field, every required false field,
  and unsupported validation statuses. Its tests also verify that blocked
  reports do not echo unsafe input values and default timestamps remain
  deterministic, that report/validation payload shapes stay explicit, and that
  missing required text defaults or required false fields fail closed as
  `decision_needed`. It also keeps caller-supplied decision and drift values
  and caller-supplied unknown schema keys out of blocked report JSON. It does
  not approve, reject, defer, authorize, activate, or access any live rail.
  The blocked report sanitization matrix locks representative non-echo cases,
  and nested prohibited-field coverage keeps caller-controlled nested live/API
  and credential/secret values out of blocked report JSON. Strict
  required-false-field hardening blocks non-boolean false-like values instead
  of accepting them as the unfilled false-default template. Strict
  required-text-default hardening blocks case/spacing variants instead of
  accepting them as the unfilled template. Strict readiness status hardening
  blocks case/spacing variants instead of accepting them as
  `readiness.status=not_ready` and keeps caller-controlled readiness drift
  values out of blocked report JSON.
  Required readiness status coverage keeps `readiness.status=not_ready` in the
  false-default template and fails closed as `decision_needed` when missing.

This state is the baseline. Do not restart from earlier roadmap phases.

## 7. Completed Implementation Through Phase 14-A/B Preparation

Completed major phases:

- Phase 1: runtime foundation.
- Phase 2: dashboard/state foundation.
- Phase 3: routine engine foundation.
- Phase 4: priority engine foundation.
- Phase 5: Todoist/Calendar module foundation, fake/simulated only.
- Phase 6: composer model integration foundation, fake/local only.
- Phase 7: report jobs / weekly chart pack foundation.
- Phase 8: fitness integration foundation.
- Phase 9A: correctness hardening.
- Phase 9B: runtime DB bootstrap.
- Phase 10A: Today View / dashboard shell.
- Phase 10B: no-send briefing loop.
- Phase 10C: dashboard briefing integration.
- Phase 11A: ChatGPT synthesis import preview backend.
- Phase 11B: dashboard synthesis preview UI.
- Phase 12A: operator CLI for no-send workflows.
- Phase 12B: side-effect/idempotency ledgers.
- Phase 13A: approval-gated synthesis apply flow.
- Phase 13B: synthesis apply atomicity/recovery hardening.
- Phase 13C: no-send scheduler/runtime loop foundation.
- Phase 13D: checkpoint hardening / permissions and status cleanup.
- Phase 13F-A: pre-live readiness policy docs.
- Phase 13F-B: inert fail-closed readiness evaluator/tests.
- Phase 13F-C: read-only CLI/status/dashboard readiness visibility.
- Phase 13F-D: activation checklist and first-live pilot protocol.
- Phase 13E-A: operator status vocabulary and report shape.
- Phase 13E-B: CLI no-send workflow polish.
- Phase 13E-C: dashboard safe-action/status polish via PR #28.
- Phase 13E-D: synthetic end-to-end no-send demo via PR #31.
- Phase 13G: pre-live readiness matrix and Long-Run Agent Work Packet Protocol
  v1 via PR #33.
- Phase 14-A/B: first live pilot preparation, proposed-only design, and
  fail-closed scaffolding. No live pilot authorized or run.
- Pre-Phase-14-C candidate-selection preparation: inert candidate-selection
  process, fail-closed blank template, and validator scaffolding, implemented
  and post-merge validated via PR #37. Clean Kitchen Countertops and Stovetop
  is recorded for candidate-review tracking only; no Todoist candidate is
  approved, authorized, activated, or run.
- Phase 14-C candidate decision gate: inert docs/test-only future decision
  boundary for reviewing the recorded candidate. It does not approve Phase
  14-C, approve the candidate, authorize execution, authorize live
  Todoist/Gmail/Calendar access, invoke OpenClaw, handle credentials/auth,
  activate production DB, activate scheduler/background behavior, implement
  dynamic cleaning, import a 15-task cleaning list, implement skip/push/bump
  behavior, implement automatic rescheduling, adopt Watch Tower, add
  `.agent/`, add `CLAUDE.md`, or add runtime/operator scaffolding.
- Phase 14-C candidate decision support: inert docs/test-only review checklist
  and unfilled false-default decision-record template. It does not select
  approve, reject, or defer and does not authorize execution or live service
  access.
- Phase 14-C candidate decision-support validator: inert source/test report
  helper for the same unfilled template. It preserves `decision_needed` or
  `blocked` outcomes only, blocks unknown schema fields and nested payloads
  under known fillable fields, covers every fillable decision field and every
  required false field with table-driven tests, verifies blocked reports do not
  echo unsafe input values, keeps default timestamps deterministic, confirms
  missing required text defaults and required false fields fail closed as
  `decision_needed`, keeps caller-supplied decision and drift values out of
  blocked report JSON, keeps caller-supplied unknown schema keys out of
  blocked report JSON, adds blocked report sanitization matrix coverage for
  representative caller-controlled tokens, keeps caller-controlled nested
  prohibited live/API and credential/secret values out of blocked report JSON,
  blocks non-boolean false-like required-false-field values, blocks
  non-exact required text defaults, blocks non-exact readiness status values,
  requires the not-ready readiness status field, and does not record a human
  decision.
  Report and validation payload shape tests keep raw decision-record echo
  fields out of the report contract.

The next human decision is separate authorization review of the recorded
candidate, or a decision that no candidate is suitable. This PRD update does
not authorize that move.

## 8. Current Capability

The repo currently supports:

- SQLite runtime foundation.
- Migration system and FK enforcement.
- Dashboard/status/Today View shell.
- No-send briefing loop.
- ChatGPT synthesis import preview.
- Approval-gated synthesis apply into internal SQLite state.
- Atomic apply and audit trail.
- Side-effect/idempotency ledgers.
- Simulated scheduler job/run tables.
- CLI operator surface for safe local workflows.
- `operator_status.v1`.
- `personalos workflows` / `workflows --json`.
- Inert pre-live readiness evaluator.
- Read-only readiness CLI/status/dashboard display.
- Dashboard safe-action/status panels.
- Formal activation checklist and first-live pilot protocol.

All of these are local, fake/simulated/no-send/inert foundations unless
explicitly proven otherwise in a later approved phase.

## 9. Phase 13E-D - Synthetic End-To-End No-Send Demo

### Objective

Phase 13E-D should add a deterministic local demo workflow that proves the
Personal OS inert/no-send system works end to end using fixture data, a
temporary SQLite DB, fake/local adapters only, and a JSON-first evidence bundle.

This PRD defines the target. It does not implement Phase 13E-D and does not
authorize Phase 14.

### Canonical Demo Command Target

Preferred shape:

```bash
PYTHONPATH=src python3 -m personalos.cli demo no-send-e2e --output-dir <safe_output_dir> --json
```

Exact naming can follow existing CLI conventions, but the repo should end Phase
13E-D with one obvious copy/paste command for local audit.

### Required Demo Path

The demo should prove this flow:

1. Create isolated temp workspace and temp SQLite DB.
2. Bootstrap local demo DB using existing migrations and FK enforcement.
3. Seed deterministic synthetic routines, priorities, follow-ups, and safe
   simulated state.
4. Import a deterministic synthetic ChatGPT synthesis payload.
5. Generate a synthesis preview.
6. Apply only approved internal SQLite-safe synthesis items.
7. Generate a no-send briefing preview using fake Composer/local adapter only.
8. Generate a no-send briefing export to the explicit output directory only.
9. Produce workflow/status/readiness/Today View/dashboard evidence.
10. Produce side-effect/idempotency ledger summary.
11. Emit a final `demo_report.json` with safety assertions.

### Required Synthetic Fixture Coverage

The future demo fixture set should include:

- routines
- priorities
- projects/focus areas, if supported
- follow-ups
- Todoist candidates as preview/simulated only
- Calendar candidates as preview/simulated only
- Gmail/no-send briefing export only
- Markdown note candidates as preview/review-only
- blocked high-stakes candidates
- side-effect/idempotency evidence
- scheduler simulation evidence, if used

### Required Safety Proof

The demo report must show:

- `readiness_status=not_ready`
- `inert_report_only=true`
- `live_rails_activated=false`
- `credentials_loaded=false`
- `credentials_read=false`
- `production_db_path_active=false`
- `scheduler_activated=false`
- `openclaw_called=false`
- `external_services_contacted=false`
- `external_mutation=false`
- live Gmail disabled
- live Todoist disabled
- live Calendar disabled
- PersonalOS Markdown writes disabled
- live model/API disabled

### Phase 13E-D Non-Goals

Do not add or activate:

- live Gmail
- live Todoist
- live Calendar
- PersonalOS Markdown writes
- credentials/OAuth
- production DB activation
- scheduler activation
- LaunchAgent
- crontab
- daemon/background loop
- OpenClaw integration
- live model/API calls
- OpenAI/OpenRouter/Anthropic integration
- external writes
- dashboard activation controls
- live send/apply/task/calendar controls
- Phase 14 implementation

## 10. V1 Product Scope

V1 product goals remain useful as the north star, but they are not permission to
activate live rails during Phase 13E-D.

### V1 Includes

- Local dashboard shell.
- Routine editor.
- Today View.
- Priority registry.
- ChatGPT synthesis import box.
- SQLite runtime state store.
- 8am / 12pm / 4pm / 8pm briefing generation.
- Todoist auto-write for low-risk routines and follow-ups, after future live
  approval.
- Calendar auto-write for approved self-only blocks, after future live
  approval.
- Gmail briefings, after future live approval.
- PersonalOS Markdown Clarity Notes and General Follow-Up Notes, after future
  approved-write design.
- Configurable permissions.
- System status/logs.
- Reports/jobs module shell.
- Fitness integration hook.
- Weekly chart pack workflow hook.

### V1 Stretch

- Todoist / Calendar preview screen.
- Weekly chart pack workflow operational.
- Fitness tracker dashboard link.
- Permissions editor.
- Basic report runner.
- Routine adherence tracking.

### Not V1

- Full investment analytics dashboard.
- Autonomous investment interpretation.
- Reply parser.
- Public internet dashboard access.
- External-user collaboration.
- Local AI inference box.
- Autonomous legal/tax/portfolio execution.

## 11. Dashboard Requirements

The dashboard is the primary local user interface.

### Access

- Local network only.
- No public internet exposure.
- No login/password for V1 unless later security design requires it.
- Mobile-friendly for iPhone.
- Usable from Windows/Mac browser.

### Sections

- Today View: briefing windows, routines, Todoist task previews, calendar block
  previews, priorities, carryovers, follow-ups, and system status.
- Routine Editor: add/edit/disable/delete routines, cadence, windows,
  Todoist/Calendar behavior, missed behavior, rotation, priority.
- Priority Editor: high-value priorities, project status, review cadence, next
  review date, follow-up notes, source notes.
- Todoist / Calendar Preview: tasks/blocks to create, duplicates skipped,
  blocked items, review-required items, auto-written items after future
  approval.
- System Status / Logs: scheduler, email, Todoist, Calendar, ledgers, model
  routing, OpenClaw health, errors, last completion report.
- Settings / Permissions: auto-write rules, review-required rules, models,
  routine defaults, Todoist mappings, Calendar behavior, email cadence,
  missed-task behavior.

During inert phases, the dashboard must not include activation controls,
credential/OAuth UI, live send controls, or live task/calendar write controls.

## 12. Structured Runtime State

SQLite stores structured runtime state.

Expected stored entities:

- routines
- routine_completions
- routine_rotations
- missed_routine_events
- priorities
- projects
- followups
- todoist_tasks
- calendar_blocks
- daily_plans
- briefing_windows
- briefing_outputs
- composer_packets
- composer_outputs
- model_runs
- permissions
- system_events
- report_jobs
- chart_pack_reviews
- fitness_integration_state
- ledgers/idempotency records
- readiness/operator status evidence

Production DB activation is blocked until a future approved phase defines
path/config, backups, restore tests, integrity checks, migration policy,
permissions, and operator procedures.

## 13. ChatGPT Synthesis Import

V1 must include an Import ChatGPT Synthesis flow. The current repo already has
preview and approval-gated apply foundations.

The import flow should accept:

- Markdown.
- JSON.
- Structured text.

Output candidates may include:

- priorities
- projects
- follow-ups
- clarity notes
- routine changes
- Todoist candidates
- Calendar candidates
- review tasks
- blocked/high-stakes candidates

Import requirements:

- Preview before save.
- Validation.
- Reject option.
- Rollback/recovery posture.
- Source timestamp.
- Source note/reference field.
- Explicit approval file or approval record before internal SQLite apply.
- Unsupported/external candidates must remain blocked or review-only.

## 14. Routine Engine

Initial default routines:

- Cleaning: 1 task/day, Monday-Friday.
- Reading: 4x/week.
- Prayer / Meditation: 2x/week.
- Grease-the-Groove: rotating exercises as needed; target 45 reps per exercise
  per week.
- Fitness / Strength: separate from GTG; integrate existing fitness tracker
  later.
- Shutdown / Review: daily evening.

Routine object fields:

- routine_id
- name
- category
- description
- cadence_rule
- preferred_windows
- enabled
- todoist_behavior
- calendar_behavior
- email_behavior
- missed_behavior
- rotation_group
- target_count
- target_unit
- weekly_target
- priority
- last_completed
- next_due
- created_at
- updated_at

Cadence types:

- daily
- weekdays
- x_times_per_week
- weekly
- every_n_days
- specific_days
- rotating_sequence
- manual_only

Missed behavior options:

- combine_with_next
- bump_schedule_by_one_day
- carry_forward_within_week
- skip_and_continue
- escalate_to_review

Recommended defaults:

- Cleaning missed combines once, then escalates if repeated.
- Reading carries forward within week.
- Prayer/meditation skips and continues.
- GTG bumps rotation or carries forward.
- Shutdown skips and continues.

All defaults must be editable.

## 15. Todoist Module

Todoist is the action rail, not the brain.

### Auto-Write Allowed After Future Live Approval

- routine_todoist_tasks
- cleaning tasks
- reading tasks
- prayer/meditation tasks
- GTG tasks
- shutdown/review tasks
- high-value review/follow-up tasks

### Approval Required

- investment execution actions
- legal/tax instructions
- relationship messages
- messages to other people
- large financial commitments
- health/medical decisions

### Task Schema

- task_title
- description
- source_type
- source_id
- project
- labels
- due_date_or_due_string
- priority
- risk_level
- approval_mode
- dedupe_key
- status

Stable routines can use recurring task patterns where appropriate. Dynamic items
are generated from state. Completed Todoist tasks should be removed from later
briefings.

During Phase 13E-D, Todoist may only appear as simulated/preview/blocked/
candidate evidence. No live Todoist writes.

## 16. Calendar Module

V1 uses preferred windows first. Availability-aware scheduling comes later.

### Auto-Write Allowed After Future Live Approval

- self-only review blocks
- deep work blocks
- admin cleanup blocks
- routine blocks explicitly configured for calendar
- weekly chart pack review block
- fitness/recovery review block if approved

### Approval Required

- events involving other people
- external meetings
- legal/tax appointments
- family-sensitive events
- financial commitments

### Calendar Object Schema

- title
- description
- source_type
- source_id
- start_time
- end_time
- duration_minutes
- calendar_id
- timezone
- approval_mode
- risk_level
- dedupe_key
- status

During Phase 13E-D, Calendar may only appear as simulated/preview/blocked/
candidate evidence. No live Calendar writes.

## 17. Gmail / Briefing Module

### Cadence

- 8am - Morning Brief.
- 12pm - Midday Reset.
- 4pm - Afternoon Checkpoint.
- 8pm - Evening Shutdown.
- Timezone: America/Chicago.

Daily plan is generated once in the morning. Each briefing is generated
just-in-time before its window. Todoist/Calendar baseline writes happen in the
morning only after future live approval. Later windows adjust based on updated
state.

If the 8am briefing includes a task and Chris completes it in Todoist at 10am,
the 12pm briefing should not show that task as remaining once live sync exists.

Briefing content:

- current window focus
- remaining routines
- open priority tasks
- calendar awareness
- Todoist changes
- missed/carryover items
- follow-ups
- warnings/blockers

During Phase 13E-D, Gmail may only appear as no-send briefing preview/export.
No Gmail draft. No Gmail send.

## 18. Composer Model Architecture

The composer model writes high-quality daily content and structured tasks/events
from a narrow Composer Packet.

### Allowed Input

- routine state
- priority titles
- selected follow-up summaries
- calendar availability summary
- Todoist task summaries
- today's schedule
- WSP/routine rules
- prior briefing results
- completion status

### Not Allowed Input

- full PersonalOS vault
- raw notes
- legal/tax source documents
- credentials
- unrestricted file access
- full journal archive
- arbitrary filesystem access

### Output

Composer output must be structured JSON plus readable text.

Required sections:

- email_briefs
- todoist_tasks
- calendar_blocks
- followups
- warnings

No prose-only output may be used for execution.

### Model Roles

- operator_model
- composer_model
- high_stakes_review_model
- coding_model

During Phase 13E-D, composer behavior must use fake/local adapters only. No live
model/API calls.

## 19. Permissions Model

Permissions must be simple and editable from the dashboard.

Initial permission examples:

- `routine_todoist_tasks = auto_write` after future live approval
- `self_calendar_blocks = auto_write` after future live approval
- `high_value_review_tasks = auto_write` after future live approval
- `high_value_execution_actions = approval_required`
- `messages_to_other_people = approval_required`
- `external_calendar_events = approval_required`

Architecture requirements:

- fail closed
- explicit readiness status
- live rails disabled by default
- no credentials loaded/read during inert phases
- no production DB activation during inert phases
- no scheduler/background activation during inert phases
- no external write without configured permission and explicit phase approval
- ledgers/idempotency for all write-like operations
- rollback/recovery posture for state-changing operations

## 20. Notes And PersonalOS Markdown

PersonalOS / Obsidian / Markdown is the durable memory layer, not the initial
raw capture dumping ground.

### Clarity Notes

For high-signal synthesis:

- big objectives
- durable insights
- priority changes
- relationship/family insights
- investment thesis shifts
- fitness/physical weak-area insights
- decision logs

Created after ChatGPT synthesis and Chris approval.

### General Follow-Up Notes

For:

- things to revisit
- open questions
- loose admin notes
- project reminders
- people/family follow-ups
- research threads

They become Todoist tasks only if they meet the task schema.

During Phase 13E-D, PersonalOS Markdown may only appear as candidate/preview
evidence. No writes to `/Users/coldstake/PersonalOS`.

## 21. Weekly Chart Pack Workflow

Every weekend Chris produces Weekly Chart Packs and gathers TradingView alerts.
Chris sends chart pack and alerts to ChatGPT. ChatGPT synthesizes market/thesis
review. OpenClaw eventually stores the synthesis, tracks week-over-week changes,
and creates follow-up review tasks if approved.

OpenClaw does not analyze investments independently. It stores and delivers
workflow outputs. ChatGPT handles thesis synthesis and chart-pack
interpretation.

Portfolio/crypto/investment actions remain high-stakes and review-required.

## 22. Fitness Integration

Fitness/strength is separate from GTG.

Existing OpenClaw/ChatGPT CSV-based fitness tracking should be preserved.

V1:

- fitness module shell
- dashboard link/status
- no rebuild of the existing CSV tracker

V1.5:

- deeper integration with existing CSV tracker
- recovery/training context in briefings

Principles:

- local CSV-based
- library-first
- minimal verbosity
- no Notion dependency

Core files remain:

- `workout_sessions.csv`
- `workout_exercises.csv`
- `weekly_recovery.csv`
- `exercise_library.csv`

## 23. Reports And Dashboard Jobs

Reports are coded jobs, not a separate analyst persona.

Chris + ChatGPT define requirements. Codex/Fable builds jobs. OpenClaw
eventually runs approved runtime jobs. ChatGPT interprets reports if needed.

Potential jobs:

- weekly chart pack index
- macro calendar
- earnings calendar
- TradingView alert digest
- priority status report
- routine adherence report
- Todoist completion report
- calendar utilization report

## 24. Codex/Fable Workflow

Codex/Fable works through repo branches, tests, docs, migrations, and PRs. Repo
work starts by reading `STATUS.md`, `AGENTS.md`, and the relevant docs under
`docs/`.

Codex/Fable should:

- verify branch and worktree state before edits
- keep changes inside the approved phase scope
- prefer repo-local tests and deterministic fixtures
- preserve explicit `--db` and safe output paths for local workflows
- report changed files and validation output
- stop at the approved boundary, especially between audit, implementation, PR
  creation, merge, and live operation

Codex/Fable should not:

- operate production workflows
- inspect protected personal/runtime paths
- load credentials
- activate live rails
- perform external writes
- call OpenClaw
- start Phase 14 without explicit approval

## 25. Evidence Standard

### Development Work

Required evidence:

- branch name
- diff summary
- files changed
- implementation notes
- test logs
- unit/integration output
- hygiene output
- demo evidence when applicable
- deviations and rationale
- PR number if opened

### Runtime/Live Operations

Required evidence after future approval:

- persisted completion report
- ledger/log snapshot
- safety flags
- idempotency evidence
- rollback/recovery information where applicable

### Forensic Bundles

Only required for:

- incidents
- production activation
- high-stakes operations
- duplicate/mutation anomalies
- suspected credential or external-write issues

Phase 13E-D should produce a development/demo evidence bundle, not a live
forensic bundle.

## 26. Phase 14 Dependency Inventory

Do not start Phase 14-C live activation until these are designed and approved:

- Production DB path/config, backup, restore test, integrity checks, migration
  policy.
- Credential loading strategy with owner/scope/rotation/revocation labels,
  without exposing secrets.
- Live permission keys and fail-closed enforcement per rail.
- Live read-only probes before live writes.
- Gmail draft/send pilot dependency and no-send preview evidence.
- Todoist live write pilot dependency, ledger/idempotency integration,
  rollback/undo path.
- Calendar live write pilot dependency, self-only/external-attendee boundaries,
  rollback path.
- Scheduler activation dependency, kill switch, unload/stop proof, no background
  default.
- OpenClaw runtime smoke-test handoff packet and stop conditions.
- PersonalOS Markdown approved-write dependency, backup/restore or
  patch/preview flow.

## 27. Current Roadmap

### Completed Through Current Baseline

Phases 1 through 14-A/B preparation are complete on the last validated main
baseline listed in Section 6. Phase 14-A/B preparation is implemented on
`main` as proposed-only design and fail-closed scaffolding. Pre-Phase-14-C
candidate-selection preparation adds an inert process, blank template, and
validator scaffolding for a later human decision.

### Current Recommended Phase

Pre-Phase-14-C candidate decision-gate review.

Purpose:

- record one future Todoist candidate for candidate-review tracking only
- provide a blank fail-closed candidate template
- validate candidate records as `decision_needed`, `blocked`, or
  `proposed_only`
- preserve an explicit Phase 14-C candidate decision gate in
  [PHASE_14C_DECISION_GATE.md](PHASE_14C_DECISION_GATE.md)
- preserve an explicit Phase 14-C candidate decision-support artifact in
  [PHASE_14C_CANDIDATE_DECISION_SUPPORT.md](PHASE_14C_CANDIDATE_DECISION_SUPPORT.md)
- preserve an inert Phase 14-C candidate decision-support validator/report in
  `src/personalos/phase14c_candidate_decision_support.py`
- keep candidate selection and candidate approval separate from live pilot
  authorization
- preserve no live rails, credentials, production DB, scheduler activation,
  external writes, or OpenClaw calls

### Not Yet Started

Phase 14-C - first live pilot activation.

Phase 14-C requires a separate selected-candidate authorization packet and
explicit Chris approval. The decision gate documents the required evidence and
wording for that future decision; it does not itself authorize the decision.
The candidate decision-support artifact documents review questions, failure
modes, stop conditions, required future approval wording, and an unfilled
false-default decision-record template only. The decision-support validator
checks that this record remains unfilled/false by default and blocks unsafe
filled records, including unknown schema fields and nested payloads under
known fillable fields. Table-driven invariant coverage checks every fillable
decision field, every required false field, and the allowed validation status
set. Missing-field matrix coverage checks that absent required text defaults
and absent required false fields fail closed as `decision_needed`. Blocked
report coverage checks that unsafe input values are not echoed, deterministic
timestamp coverage keeps default reports stable, and report shape coverage
keeps the payload contract explicit. Blocked-reason sanitization keeps
caller-supplied decision and drift values out of report JSON. Unknown schema
key-name sanitization keeps caller-supplied unknown keys out of report JSON; it
does not select approve, reject, or defer. The blocked report sanitization
matrix locks representative non-echo cases for unknown schema,
decision-selection, candidate-drift, and nested-fillable payload inputs.
Strict readiness status coverage checks that non-exact `not_ready` variants
block and do not echo caller-controlled readiness drift values.
Required readiness status coverage checks that missing readiness status fails
closed as `decision_needed`.

## 28. V1 Acceptance Criteria

V1 is acceptable only when:

- Dashboard works locally from phone/laptop.
- SQLite state store exists and is backed up.
- Routine editor can add/edit/disable routines.
- Today View shows routines, priorities, tasks, calendar blocks, and status.
- ChatGPT synthesis import can create structured state.
- Daily routine rules are configurable.
- Todoist auto-write works for approved low-risk routine tasks after live
  approval.
- Calendar auto-write works for approved self-only blocks after live approval.
- 8 / 12 / 4 / 8 briefings generate from current state.
- Completed Todoist tasks are removed from later briefings once live sync exists.
- High-value review/follow-up tasks can be created after permission approval.
- High-stakes execution actions remain gated.
- Composer model uses narrow state packets only.
- OpenClaw executes validated outputs only after runtime approval.
- Logs/completion reports exist for runtime operations.
- No live production mutation occurs without configured permission.
- Codex/Fable development workflow is repo-based and tested.

## 29. Immediate Next Step

The immediate human decision after this repo-local update is whether to use
[PHASE_14C_DECISION_GATE.md](PHASE_14C_DECISION_GATE.md) for a later explicit
review of the recorded Clean Kitchen Countertops and Stovetop candidate, or
to reject/defer the candidate and keep Phase 14-C blocked.
The related decision-support aid is
[PHASE_14C_CANDIDATE_DECISION_SUPPORT.md](PHASE_14C_CANDIDATE_DECISION_SUPPORT.md).

Phase 14-C remains blocked unless Chris later approves a separate
selected-candidate authorization packet.

Codex/Fable must not turn Phase 14-A/B preparation into live activation.

## Appendix A - Fresh Chat Carryover Prompt

We are continuing the Personal OS repo buildout in a fresh ChatGPT thread.

Do not start from scratch.

Current project:

- Product: Personal OS
- Repo: `/Users/coldstake/dev/personal-os`
- GitHub repo: `cdsouza235/personal-os`
- Runtime host: Mac Mini
- Structured state: SQLite
- Durable notes later: PersonalOS / Obsidian / Markdown
- Execution rails later: Todoist, Google Calendar, Gmail

Role boundary:

- ChatGPT = strategy, synthesis, PRD, architecture, audit, review, and
  instruction-writing.
- Codex/Fable = repo implementation, tests, docs, migrations, PRs, merges, and
  post-merge validation.
- OpenClaw = approved runtime/operator only after repo is ready and Chris
  approves.
- Chris = owner/final approver.

Important correction:

Repo work goes to Codex/Fable by default, not OpenClaw. OpenClaw should not
handle repo implementation, PR review, merge, or validation unless explicitly
chosen later for a narrow runtime/operator smoke test.

Last validated main baseline after PR #61:

`16a71bc6c8f500d5c21c9329586698f3156b9f92`

Current validated state:

- Full suite: 539 tests OK
- ResourceWarning-sensitive suite: 539 tests OK
- Hygiene clean
- No repo-local var/
- No SQLite/DB artifacts outside .git
- Readiness reports not_ready
- inert_report_only true
- live_rails_activated false
- All live rails disabled
- No credentials loaded/read
- No production DB active
- No scheduler active
- No LaunchAgent/crontab/daemon/background loop active
- No external writes
- No OpenClaw call
- Dashboard has no activation controls
- Dashboard has no credential/OAuth UI
- Phase 14-A/B preparation is proposed-only and inert
- Pre-Phase-14-C candidate-selection preparation is proposed-only and inert
- Clean Kitchen Countertops and Stovetop is recorded for candidate-review
  tracking only
- No Todoist candidate is approved, authorized, activated, or run
- Phase 14-C candidate decision-gate documentation is inert and
  non-authorizing
- Phase 14-C candidate decision-support documentation is inert, unfilled, and
  non-authorizing
- Phase 14-C candidate decision-support validator/reporting is inert,
  source/test-only, and non-authorizing
- PR #45 Claude Code audit passed with no required fixes
- PR #46 anti-micro-loop workflow and checkpoint refresh is merged
- PR #47 Phase 14-C candidate decision support bundle is merged
- PR #48 Phase 14-C candidate decision-support validator is merged
- PR #49 Phase 14-C decision-support strict-schema hardening is merged
- PR #50 Phase 14-C decision-support nested-field hardening is merged
- PR #51 Phase 14-C decision-support invariant matrix is merged
- PR #52 Phase 14-C decision-support report sanitization is merged
- PR #53 Phase 14-C decision-support report shape contract is merged
- PR #54 Phase 14-C decision-support missing-field matrix is merged
- PR #55 Phase 14-C decision-support blocked-reason sanitization is merged
- PR #56 Phase 14-C decision-support unknown schema reason sanitization is
  merged
- PR #57 Phase 14-C decision-support sanitization matrix tests are merged
- PR #58 Phase 14-C decision-support nested prohibited sanitization tests are
  merged
- PR #59 Phase 14-C decision-support strict false-field validation is merged
- PR #60 Phase 14-C decision-support strict text-default validation is merged
- PR #61 Phase 14-C decision-support strict readiness status validation is
  merged

Next human decision:

Review whether to approve or reject the recorded candidate in a separate
authorization packet, or decide that Phase 14-C remains blocked until a
different candidate is created or validated.

Do not authorize, activate, schedule, or run a live pilot from this packet.
