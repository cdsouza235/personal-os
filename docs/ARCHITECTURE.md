# Personal OS Architecture Brief v0.1

## System Definition

Personal OS is a modular, local-first productivity, routine, priority, and execution operating system. It coordinates strategy, state, durable notes, local automation, external execution rails, and reporting through clear operator boundaries.

## Runtime Topology

- GitHub private repo: code source of truth.
- Mac Mini: runtime and deployment host, always-on scheduler host, local repo clone, SQLite state host, and local PersonalOS file host.
- OpenClaw: local Personal Assistant and runtime operator on the Mac Mini.
- SQLite: structured runtime state.
- Markdown, Obsidian, and PersonalOS: durable notes, logs, protocols, and reviews.
- Todoist, Calendar, and Gmail: execution rails touched only by validated runtime modules.
- Codex: primary coding agent and development layer for repository code.
- Fable: optional or future alternate coding agent for long-horizon development work.
- ChatGPT: synthesis, analysis, architecture, PRD, and audit layer.

## Role Boundaries

### Chris

Chris owns the system, approves high-stakes actions, and supplies judgment and priorities.

### ChatGPT

ChatGPT is the thought partner, synthesis layer, analysis layer, PRD writer, architect, and auditor. It produces structured thinking and review artifacts, not live mutations.

### Codex

Codex is the primary coding agent and software development layer. It edits repository code, tests, and documentation after phase gates. It does not operate production workflows.

### Fable

Fable is an optional or future alternate coding agent for long-horizon software development work. It has the same production boundary as Codex unless a future policy says otherwise.

### OpenClaw

OpenClaw is the local runtime operator. It runs approved local workflows, writes approved runtime outputs, and interacts with execution rails through validated modules.

### Mac Mini

The Mac Mini hosts the runtime, scheduler, local clone, SQLite state, OpenClaw runtime, and local PersonalOS files.

## State Architecture

Personal OS uses a split state model:

- Code state lives in the private GitHub repo.
- Structured runtime state lives in SQLite on the Mac Mini.
- Durable narrative state lives in Markdown, Obsidian, and PersonalOS.
- Execution state lives in Todoist, Calendar, and Gmail, but those systems are not treated as the source of truth for thinking.

## SQLite Entities

The initial runtime state model should document and eventually implement these entities:

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
- fitness_validation_runs
- fitness_file_contracts

## SQLite Environment Separation

- Production SQLite state lives on the Mac Mini runtime path.
- Development and test SQLite files live inside repo-local temporary or test paths.
- Codex may create and edit dev/test databases in the repository.
- Codex may not mutate production SQLite state without explicit approval.
- Production migrations require a backup before migration.
- Production backups should include periodic JSON and SQLite snapshots.

## Dashboard Architecture

The V1 dashboard is a local-network-only web surface. It should have no public internet exposure and no login or password requirement for V1 by choice. It should work well on iPhone and in Windows or Mac browsers.

Threat model:

- Risks include accidental local network access, stale browser sessions, and exposure from trusted devices on the network.
- Future security options may include a password, device allowlist, Tailscale/VPN access, or local-only binding.

Sections:

- Today View
- Routine Editor
- Priority Editor
- Todoist/Calendar Preview
- System Status/Logs
- Settings/Permissions
- Reports/Jobs shell

## Routine Engine

Routines must be data-driven, not hardcoded. The editor must support add, edit, disable, and delete operations.

The Phase 3 routine engine foundation is narrower than the full routine system.
It provides dev/test-only data access, validation, permission-gated read/write
helpers, and dry-run-safe completion recording on top of the Phase 2 SQLite
tables. It does not implement scheduling, recurrence expansion, default routine
seeding, editor UI, dashboard UI, OpenClaw wiring, or external integrations.
Routine completions are append-only dev/test records in Phase 3 and do not yet
enforce idempotency by `routine_id` plus `completed_for_date`. Scheduler and
idempotency rules are deferred to a future scheduler/runtime phase before any
automated recurring completion loop is activated.

Cadence rules:

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

Default routines:

- Cleaning: 1 task/day, Monday-Friday.
- Reading: 4x/week.
- Prayer / Meditation: 2x/week.
- Grease-the-Groove: rotating exercises as needed, target 45 reps per exercise per week.
- Fitness / Strength: separate from Grease-the-Groove and integrated later from the existing tracker.
- Shutdown / Review: daily evening.

## Priority Engine

The Phase 4 priority engine foundation is narrower than the full priority
system. It provides dev/test-only priority registry access, validation,
permission-gated read/write helpers, dry-run-safe create/update/status
transition flows, and deterministic read models on top of the Phase 2 SQLite
`priorities` table.

Priority statuses are deterministic registry states:

- active
- paused
- completed
- archived

Phase 4 does not infer priorities from raw notes, rank priorities
automatically, score tasks, generate Todoist tasks, create Calendar blocks,
write Gmail briefs, call OpenClaw, produce composer packets, activate
schedulers, add dashboard UI, or touch production state. Scheduler behavior,
idempotency/send ledger rules, Todoist/Calendar modules, composer integration,
and dashboard UI remain later-phase work.

## Todoist and Calendar Module Foundation

The Phase 5 Todoist and Calendar foundation is narrower than live execution.
It adds dev/test-only module objects, validation, persistence, permission
gates, preview flows, fake adapters, simulated write reports, and
module-level dedupe.

Todoist is the action rail, not the brain. Phase 5 stores normalized Todoist
task proposals in `todoist_tasks` with required task/source/project fields,
labels serialized as JSON, Todoist-like priorities 1 through 4, risk level,
approval mode, dedupe key, status, and a nullable fake/future external task
ID.

Calendar is for real time-bound blocks and commitments. Phase 5 stores
normalized Calendar block proposals in `calendar_blocks` with required
title/source/window/calendar fields, timezone-aware start and end times,
duration consistency checks, risk level, approval mode, dedupe key, status,
and a nullable fake/future external event ID.

Risk levels are:

- low: routine/admin/self-only tasks or blocks.
- medium: self-only but sensitive, ambiguous, unusually time-consuming, or tied
  to a larger project.
- high: legal, tax, portfolio/crypto/investment execution, health/medical
  decisions, relationship messages, messages to other people, external
  meetings, family-sensitive events, or large financial commitments.

Approval modes are:

- auto_allowed: valid only with low risk.
- approval_required: default for medium and high risk.
- manual_only: storable and previewable, but not routable to a write client.

Phase 5 permission keys are:

- `todoist_module_dev_test_read`
- `todoist_module_dev_test_write`
- `todoist_module_dev_test_simulated_write`
- `calendar_module_dev_test_read`
- `calendar_module_dev_test_write`
- `calendar_module_dev_test_simulated_write`

These keys fail closed by default. No live-write permission keys exist in
Phase 5.

Module-level dedupe is scoped to `todoist_tasks` and `calendar_blocks`.
`dedupe_key` is required and unique within each table. When a caller omits a
dedupe key, the modules generate one deterministically from stable normalized
fields such as module/object type, source type, source ID, title, due date, or
start time. Duplicate creates return the existing object explicitly and do not
silently insert another row.

Fake Todoist and Calendar clients are recording adapters for tests and
simulated write flows only. They never read credentials, touch the network, or
mutate external systems. Their fake external IDs are deterministic and derived
from dedupe keys.

Phase 5 does not add live Todoist writes, live Calendar writes, credentials,
OAuth, scheduler activation, production SQLite access, Gmail integration,
composer/model integration, dashboard UI, OpenClaw wiring, LaunchAgents,
public internet exposure, external-user collaboration, autonomous
legal/tax/portfolio execution, or a broader scheduler idempotency/send ledger.
Any post-merge live smoke test is a separate OpenClaw-approved operation, not
part of this PR.

## Briefing Architecture

Timezone: America/Chicago.

America/Chicago is Chris's operating timezone for briefings and routines. The Mac Mini system timezone may differ. Scheduler code must explicitly use the configured operating timezone and must not assume the host timezone.

- 8am Morning Brief.
- 12pm Midday Reset.
- 4pm Afternoon Checkpoint.
- 8pm Evening Shutdown.

The daily plan is generated once in the morning. Each email is generated just-in-time before its briefing window. Todoist and Calendar baseline writes happen in the morning. Later windows use updated state, including completed tasks and schedule changes.

## Composer Model Architecture

Phase 6 creates the Composer model integration foundation without live model
integration. The composer receives only a dedicated Composer Packet built from
narrow dev/test summaries. It must not receive broad filesystem access, raw
notes, the full PersonalOS vault, protected runtime paths, credentials,
legal/tax source documents, Gmail bodies, live Todoist API data, live Calendar
API data, or unrestricted files.

Composer Packet `composer_packet.v1` contains:

- `packet_id`
- `packet_type`: `daily_brief`, `window_brief`, or `ad_hoc_preview`
- `briefing_window`: `morning`, `midday`, `afternoon`, `evening`, or `none`
- `source_date`
- `timezone`: `America/Chicago`
- `generated_at`
- `inputs`
- `omissions`
- `warnings`

Allowed `inputs` sections are routine state, priority summaries, selected
follow-up summaries, Todoist task summaries, Calendar block summaries,
Calendar availability summary, today's schedule summary, WSP/routine rules,
prior briefing summaries, and completion status.

Composer Output `composer_output.v1` must include structured JSON plus
non-empty readable text. Required output sections are:

- `email_briefs`
- `todoist_tasks`
- `calendar_blocks`
- `followups`
- `warnings`

No prose-only output may be used for execution. Output validation rejects
missing required sections, missing readable text, malformed Todoist or Calendar
candidates, medium/high-risk `auto_allowed` candidates, and forbidden
fields/claims.

Phase 6 routes Todoist and Calendar candidates through the Phase 5 preview
validators only. Candidate routing produces a structured report with
`accepted_candidates`, `rejected_candidates`, `blocked_candidates`, `warnings`,
and `no_external_writes: true`. Accepted candidates are not executed.

The only model adapter in Phase 6 is `FakeComposerAdapter`
(`adapter_name = fake_composer_adapter`, `model_name = fake-composer-v1`).
It is deterministic, dry-run only, and records fake model-run metadata in
`model_runs`. It never touches network, credentials, live model APIs, Todoist,
Calendar, Gmail, OpenClaw, LaunchAgents, production SQLite, or production
state.

Phase 6 permission keys are:

- `composer_module_dev_test_read`
- `composer_module_dev_test_write`
- `composer_module_dev_test_run`

These keys fail closed by default and allow dev/test work only when explicitly
set to `auto_write`.

## Validated Runtime Module Definition

A module is validated only after:

- Schema exists.
- Unit tests exist.
- Dry-run or no-send mode exists.
- Dedupe behavior exists where applicable.
- Permissions behavior is tested.
- Logging or completion report exists.
- One controlled live test passes if the module has side effects.

## Model Roles

- operator_model
- composer_model
- high_stakes_review_model
- coding_model

## Permissions Architecture

Permissions must be editable from the dashboard, safety-aware, configurable, logged, and reversible.

Default permissions:

- routine_todoist_tasks: auto_write
- self_calendar_blocks: auto_write
- high_value_review_tasks: auto_write
- high_value_execution_actions: approval_required
- messages_to_other_people: approval_required
- external_calendar_events: approval_required

## Integration Boundaries

### Todoist

Todoist is the action rail. Low-risk routine tasks and high-value review/follow-up tasks may auto-write. High-stakes execution actions require approval. Raw emotional notes and vague thoughts do not become Todoist tasks. Completed Todoist tasks should drop out of later briefings.

### Calendar

Calendar scheduling should use preferred windows first. Availability-aware scheduling is later-phase work. Self-only review, deep work, admin, and routine blocks may auto-write after validation. Events involving other people or high-stakes appointments require review.

### Gmail

Gmail is a briefing delivery rail. Gmail state and sending behavior remain protected until validated runtime modules and gates exist.

Gmail phase boundaries:

- Phase 0: no Gmail access.
- Phase 1: no-send scheduler and email infrastructure.
- Later: metadata or read-only access only if explicitly approved.
- Later: draft generation.
- Later: send-enabled only with ledger, idempotency, and permission gates.
- Gmail send remains an OpenClaw runtime responsibility, not a Codex development responsibility.

## Reports and Jobs

Reports are coded jobs, not a separate analyst persona. Chris and ChatGPT
define requirements. Codex builds job definitions, schemas, validation,
deterministic local runners, tests, and documentation. OpenClaw runs approved
jobs and stores approved outputs later, but Phase 7 does not add scheduler or
live runtime wiring.

Phase 7 stores report job definitions in `report_jobs`, local run records in
`report_runs`, and Weekly Chart Pack reviews in `chart_pack_reviews`. Supported
job types are weekly chart pack index, TradingView alert digest, macro
calendar, earnings calendar, priority status report, routine adherence report,
Todoist completion report, and Calendar utilization report.

Report runs are preview, dry-run, or simulated records only. The deterministic
fake report runner produces structured local-only output with
`no_external_writes: true`. It never fetches market data, calls TradingView,
calls model APIs, writes Todoist, writes Calendar, sends Gmail, touches
credentials, starts schedulers, loads LaunchAgents, or mutates production
SQLite.

Phase 7 permission keys are:

- `report_jobs_dev_test_read`
- `report_jobs_dev_test_write`
- `report_jobs_dev_test_run`
- `chart_pack_reviews_dev_test_read`
- `chart_pack_reviews_dev_test_write`

These keys fail closed by default and allow dev/test work only when explicitly
set to `auto_write`.

## Weekly Chart Pack Hook

The weekend workflow reminds Chris to produce chart packs. Chris sends chart
packs and TradingView alerts to ChatGPT. TradingView alerts are manually
supplied; Phase 7 stores them as validated JSON and does not fetch them live.
ChatGPT is the interpretation layer for market and thesis synthesis. OpenClaw
stores approved synthesis and updates weekly chart review notes in a later
approved runtime workflow. The system tracks week-over-week changes. OpenClaw
does not independently analyze investments.

The chart pack review schema stores review date, week start/end, source type,
source ID, title, thesis context, chart pack JSON, TradingView alert digest
JSON, synthesis markdown, structured summary JSON, status, and timestamps.
Structured summaries must include market context, BTC context, ETH context,
miner/HPC context, portfolio watch items, week-over-week changes, follow-up
candidates, and warnings.

Phase 7 does not add live market data fetching, TradingView API access,
investment recommendations, portfolio execution, Todoist writes, Calendar
writes, Gmail send, live model/API calls, credentials, OAuth, scheduler
activation, LaunchAgents, production SQLite access, dashboard UI, protected
PersonalOS vault access, or unrestricted filesystem access. Follow-up
candidates are review/logging candidates only and are not execution tasks.

## Fitness Hook

Phase 8 Fitness Integration Foundation preserves the existing CSV-based local
fitness tracker and adds a contract/status shell around it. The existing
CSV-based local fitness tracker is preserved; this repository does not rebuild
or migrate it in Phase 8.

Fitness/strength is separate from Grease-the-Groove. The local tracker contract
is library-first and CSV-based, with no Notion dependency. The expected files
are:

- `workout_sessions.csv`
- `workout_exercises.csv`
- `weekly_recovery.csv`
- `exercise_library.csv`

Phase 8 stores only integration labels, expected filenames, fixture validation
runs, and file contracts in dev/test SQLite. It uses `personal_os_fitness_csvs`
as a label, not an absolute live path. Fixture validation checks
caller-supplied CSV headers only and returns reports with
`no_external_writes: true` and `no_live_personalos_access: true`.

Phase 8 permission keys are:

- `fitness_integration_dev_test_read`
- `fitness_integration_dev_test_write`
- `fitness_integration_dev_test_validate`

These keys fail closed by default and allow dev/test work only when explicitly
set to `auto_write`.

Phase 8 has no live PersonalOS CSV reads or writes, no Apple Health or wearable
API integration, no Notion integration, no workout recommendation engine, no
medical/health advice engine, no Todoist/Calendar/Gmail writes, no live
model/API calls, no credentials or OAuth, no scheduler or LaunchAgents, no
production SQLite/runtime state, no dashboard UI yet, no full PersonalOS vault
access, and no unrestricted filesystem access. V1.5 may later add deeper
recovery/training context in briefings after separate approval.

## Runtime DB Bootstrap

Phase 9B adds the local/dev-preview runtime SQLite bootstrap bridge needed
before a dashboard, no-send briefing loop, scheduler, or live integration is
activated. It is not production activation and not a live runtime launch.

Runtime bootstrap profiles must use an explicit database path, a
`dev_runtime` or `local_runtime_preview` mode, `no_external_writes: true`, and
`no_send_mode: true`. The bootstrap layer rejects protected PersonalOS,
OpenClaw, LaunchAgents, credential/OAuth-looking, and production-looking paths.
Only explicit temp/dev runtime DB paths are eligible for mutation in this
phase.

The bootstrap preview is non-mutating. It reports the target DB path, pending
migrations, possible backup path, seed profile, and safety flags. Bootstrap
execution creates a timestamped backup before migrating an existing DB, creates
a new DB only when the target does not exist, applies migrations through the
existing checksum-tracked migration system, and keeps SQLite foreign keys
enabled on the bootstrap connection.

Phase 9B stores bootstrap evidence in `runtime_bootstrap_runs` and inert
briefing schedule definitions in `briefing_windows`. Briefing windows support
only `no_send` or `manual_export` delivery modes and `draft`, `active`, or
`disabled` statuses. They are definitions only; no scheduler or briefing loop
exists yet.

The safe MVP preview seed profile writes only local SQLite state. It disables
external/live-facing permissions, creates paused disabled preview routines,
creates a fake paused preview priority, and creates no-send draft briefing
windows for morning, midday, afternoon, and evening.

Phase 9B permission keys are:

- `runtime_bootstrap_dev_test_read`
- `runtime_bootstrap_dev_test_write`
- `runtime_bootstrap_dev_test_run`

These keys fail closed by default and allow dev/test work only when explicitly
set to `auto_write`. No production runtime permission or live external write
permission exists in Phase 9B.

## Local Dashboard Today View

Phase 10A local dashboard Today View foundation adds the first visible local
dashboard surface on top of the existing runtime state architecture. It is a
read-only local dashboard shell, not a production runtime launch.

The Today View read model accepts an existing SQLite connection plus explicit
source date and timezone parameters. It reads existing state only and returns
routine summaries, priority summaries, follow-up summaries, Todoist candidate
counts, Calendar block counts, briefing window definitions, permission safety
state, system/runtime status, warnings, and `no_external_writes: true`.

The dashboard shell is standard-library only. It can render `Personal OS Today
View` HTML from a supplied connection or read-only SQLite DB path, and it can
serve read-only HTML/JSON routes when explicitly started. It binds to
localhost-only by default and rejects public bind hosts such as `0.0.0.0`.
Dashboard DB paths must be explicit temp or repo-local dev SQLite paths, and
protected, credential/OAuth-looking, and production-looking paths are rejected.

Phase 10A adds no new permission keys and no mutation routes. It does not add
live Todoist writes, live Calendar writes, Gmail send, live model/API calls,
Notion, Apple Health, TradingView/API calls, credentials/OAuth,
scheduler/LaunchAgents, public internet exposure, login/auth, task/calendar
mutation from dashboard, routine editor, priority editor, synthesis import,
no-send daily briefing generation loop, production SQLite/runtime state
mutation, protected PersonalOS or OpenClaw access, or production runtime
activation.

## Phase 0 Inventory Charter

Phase 0 requires explicit approval before starting. It is read-only. Phase 0 may inspect specified live paths only after explicit approval for that inventory scope.

Proposed read-only paths may include:

- `/Users/coldstake/PersonalOS`
- `/Users/coldstake/.openclaw`
- `/Users/coldstake/Library/LaunchAgents`
- `/Users/coldstake/dev/personal-os`

Forbidden actions:

- Sending email.
- Executing `gog gmail send`.
- Mutating Todoist.
- Mutating Calendar.
- Loading or unloading LaunchAgents.
- Modifying production ledgers.
- Modifying production SQLite state.
- Reading or printing credentials.

Required Phase 0 outputs:

- Current file/module inventory.
- Inventory report.
- Protected path map.
- Boundary map.
- Current runtime architecture map.
- Config, ledger, and LaunchAgent inventory.
- Risk register.
- Migration recommendations.
- Recommended Phase 1 implementation plan.
- Open questions.
