# Safety Policy

## Purpose

Personal OS should feel lightweight to use while remaining safety-aware, configurable, logged, and reversible. This policy defines which systems are protected, how execution gates work, and what evidence is required.

## Current Boundary

Phases -1 through 9A are complete, and the Phase 6B, Phase 7B, and Phase 8B
fake/local smoke tests are complete. The current Phase 9B work is local/dev
runtime DB bootstrap foundation. It may edit repo-local code, tests, and
documentation, and may create temporary dev/test SQLite databases during tests.
It must not inspect or mutate live runtime files, live PersonalOS files or
fitness CSVs, credentials, external systems, production ledgers, production
SQLite state, or any production state.

Codex must not inspect:

- `/Users/coldstake/PersonalOS`
- `/Users/coldstake/.openclaw`

## Protected Systems

Codex must not inspect or mutate the following without explicit approval:

- Gmail
- Todoist
- Calendar
- LaunchAgents
- Production ledgers
- Credentials
- Production SQLite state
- OpenClaw runtime files or runtime config
- Live PersonalOS runtime files
- Any other production state

## Production Operator Rule

OpenClaw is the production and runtime operator. Codex is the primary coding agent and builds repository code, tests, and documentation. Fable is an optional or future alternate coding agent for long-horizon software development work. Codex and Fable may not run live OpenClaw workflows unless a future phase explicitly grants that authority.

## Phase 0 Rule

Phase 0 is read-only inventory first. It requires explicit approval before it starts. Its purpose is to observe approved surfaces and produce an evidence-backed map without mutation.

Phase 0 may inspect specified live paths only after explicit approval for that inventory scope. Proposed read-only paths may include:

- `/Users/coldstake/PersonalOS`
- `/Users/coldstake/.openclaw`
- `/Users/coldstake/Library/LaunchAgents`
- `/Users/coldstake/dev/personal-os`

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

## Prohibited Codex Actions

Codex may not:

- Send email.
- Execute `gog gmail send`.
- Write Todoist.
- Write Calendar.
- Mutate Todoist.
- Mutate Calendar.
- Load or modify LaunchAgents.
- Load or unload LaunchAgents.
- Modify production ledgers.
- Mutate production SQLite state.
- Modify production SQLite state.
- Run live OpenClaw workflows.
- Inspect `/Users/coldstake/PersonalOS`.
- Inspect `/Users/coldstake/.openclaw`.
- Touch credentials.
- Read or print credentials.
- Touch production state.
- Create live workflow scripts during documentation or scaffold phases.

## Timezone Authority

America/Chicago is Chris's operating timezone for briefings and routines. The Mac Mini system timezone may differ. Scheduler code must explicitly use the configured operating timezone and must not assume the host timezone.

## SQLite Environment Separation

- Production SQLite state lives on the Mac Mini runtime path.
- Development and test SQLite files live inside repo-local temporary or test paths.
- Codex may create and edit dev/test databases in the repository.
- Codex may not mutate production SQLite state without explicit approval.
- Production migrations require a backup before migration.
- Production backups should include periodic JSON and SQLite snapshots.

## Permission Defaults

Permissions must be editable from the dashboard.

Default permissions:

- routine_todoist_tasks: auto_write
- self_calendar_blocks: auto_write
- high_value_review_tasks: auto_write
- high_value_execution_actions: approval_required
- messages_to_other_people: approval_required
- external_calendar_events: approval_required

Phase 3 routine engine permissions are stored in `permission_settings` and are
separate from live integration permissions:

- routine_engine_dev_test_read
- routine_engine_dev_test_write

Routine engine read and write paths fail closed when the relevant key is
missing, disabled, invalid, or approval-only. They allow work only when the
relevant dev/test key is explicitly set to `auto_write`.

Phase 4 priority engine permissions are stored in `permission_settings` and are
separate from live integration permissions:

- priority_engine_dev_test_read
- priority_engine_dev_test_write

Priority engine read and write paths fail closed when the relevant key is
missing, disabled, invalid, or approval-only. They allow work only when the
relevant dev/test key is explicitly set to `auto_write`.

Phase 5 Todoist and Calendar module permissions are stored in
`permission_settings` and are separate from live integration permissions:

- todoist_module_dev_test_read
- todoist_module_dev_test_write
- todoist_module_dev_test_simulated_write
- calendar_module_dev_test_read
- calendar_module_dev_test_write
- calendar_module_dev_test_simulated_write

These module read, dev/test write, and simulated-write paths fail closed when
the relevant key is missing, disabled, invalid, or approval-only. They allow
work only when the relevant dev/test key is explicitly set to `auto_write`.
Phase 5 does not add live-write permission keys.

Phase 6 Composer module permissions are stored in `permission_settings` and
are separate from live model/API or live execution permissions:

- composer_module_dev_test_read
- composer_module_dev_test_write
- composer_module_dev_test_run

Composer read, dev/test write, and fake-run/routing paths fail closed when the
relevant key is missing, disabled, invalid, or approval-only. They allow work
only when the relevant dev/test key is explicitly set to `auto_write`.
Phase 6 does not add live model/API permission keys or live execution keys.

Phase 7 report job and chart pack review permissions are stored in
`permission_settings` and are separate from live scheduler, TradingView,
market data, model/API, and execution permissions:

- report_jobs_dev_test_read
- report_jobs_dev_test_write
- report_jobs_dev_test_run
- chart_pack_reviews_dev_test_read
- chart_pack_reviews_dev_test_write

Report job, report run, and chart pack review read, dev/test write, and fake
run paths fail closed when the relevant key is missing, disabled, invalid, or
approval-only. They allow work only when the relevant dev/test key is
explicitly set to `auto_write`. Phase 7 does not add live scheduler,
TradingView/API, market-data, portfolio-execution, Todoist, Calendar, Gmail,
or model/API permission keys.

Phase 8 fitness integration permissions are stored in `permission_settings`
and are separate from live fitness tracker, Notion, Apple Health, wearable API,
scheduler, model/API, and execution permissions:

- fitness_integration_dev_test_read
- fitness_integration_dev_test_write
- fitness_integration_dev_test_validate

Fitness integration read, dev/test write, and fixture/schema validation paths
fail closed when the relevant key is missing, disabled, invalid, or
approval-only. They allow work only when the relevant dev/test key is
explicitly set to `auto_write`. Phase 8 does not add live fitness import,
live CSV write, Notion, Apple Health, wearable API, Todoist, Calendar, Gmail,
or model/API permission keys.

Phase 9B runtime bootstrap permissions are stored in `permission_settings` and
are separate from production runtime activation, live scheduler, live
integration, and live model/API permissions:

- runtime_bootstrap_dev_test_read
- runtime_bootstrap_dev_test_write
- runtime_bootstrap_dev_test_run

Runtime bootstrap preview/read, local DB write, and seed/run paths fail closed
when the relevant key is missing, disabled, invalid, or approval-only. They
allow work only when the relevant dev/test key is explicitly set to
`auto_write`. Phase 9B does not add a production runtime permission, live
external write permission, live model/API permission, Gmail permission,
Todoist live-write permission, Calendar live-write permission, scheduler
permission, or LaunchAgent permission.

## Execution Rules

Phase 3 routine completion is not live execution. In dry-run mode it validates
the intended completion, checks the dev/test permission setting, and returns
what would be written without inserting a row. In non-dry-run dev/test mode it
writes only a `routine_completions` row to the injected dev/test SQLite
connection and returns an inert result. It does not send notifications, create
Todoist tasks, write Calendar events, send email, call OpenClaw, or touch
production state.

Phase 3 routine completions are append-only dev/test records. They do not yet
enforce idempotency by `routine_id` plus `completed_for_date`, and this phase
does not add a database unique constraint. Scheduler and idempotency rules are
deferred to a future scheduler/runtime phase before any automated recurring
completion loop is activated.

Phase 4 priority work is not live execution or autonomous prioritization. In
dry-run mode it validates intended priority creation, update, or status
transition, checks the dev/test permission setting, and returns what would be
written without mutating SQLite. In non-dry-run dev/test mode it writes only to
the injected dev/test SQLite connection and returns an inert result. It does
not infer meaning from raw notes, score or rank priorities, create Todoist
tasks, write Calendar events, send email, call OpenClaw, generate composer
packets, activate a scheduler, write production SQLite, or touch production
state.

Phase 4 does not add scheduler behavior, idempotency/send ledger behavior,
Todoist/Calendar modules, composer integration, or dashboard UI.

Phase 5 Todoist and Calendar module work is not live execution. Preview flows
validate proposed objects, calculate deterministic dedupe keys, calculate
risk/approval results, and return intended writes without mutating SQLite or
calling adapters. Dev/test persistence flows write only to the injected
dev/test SQLite connection. Simulated write flows require simulated-write
permissions, use only fake recording clients, update local dev/test rows to
`simulated_created`, and return fake external IDs derived from dedupe keys.

Phase 5 risk levels:

- low: routine/admin/self-only tasks or blocks.
- medium: self-only but sensitive, ambiguous, unusually time-consuming, or tied
  to a larger project.
- high: legal, tax, portfolio/crypto/investment execution, health/medical
  decisions, relationship messages, messages to other people, external
  meetings, family-sensitive events, or large financial commitments.

Phase 5 approval modes:

- auto_allowed: valid only with low risk.
- approval_required: default for medium and high risk.
- manual_only: may be stored or previewed but must not be routed to a write
  client, including fake simulated clients.

Phase 5 module-level dedupe is scoped to `todoist_tasks` and
`calendar_blocks`. `dedupe_key` is required and unique within each table.
Duplicate creates return an existing object explicitly and never silently
create duplicate rows.

Phase 5 fake Todoist and Calendar adapters never read credentials, touch the
network, or mutate external systems. No tests or module code call live Todoist
or Google Calendar APIs.

Phase 5 does not add live Todoist writes, live Calendar writes, credentials,
OAuth, scheduler activation, production SQLite access, Gmail integration,
composer/model integration, dashboard UI, OpenClaw runtime wiring,
LaunchAgents, public internet exposure, external-user collaboration,
autonomous legal/tax/portfolio execution, or a broader scheduler
idempotency/send ledger. Any post-merge live smoke test is a separate
OpenClaw-approved operation, not part of this PR.

Phase 6 Composer model integration is not live model integration and not live
execution. Packet builders read only narrow dev/test SQLite summaries through
injected connections. Packet and output validators reject prose-only outputs,
missing readable text, missing required sections, malformed Todoist/Calendar
candidates, medium/high-risk `auto_allowed` candidates, forbidden fields, and
forbidden access claims. The fake Composer adapter is deterministic and never
touches network, credentials, live model APIs, Todoist, Calendar, Gmail,
OpenClaw, protected runtime paths, production SQLite, or production state.

Phase 6 candidate routing produces only a structured preview report. Valid
Todoist and Calendar candidates pass through the Phase 5 preview validators,
but routing never creates external tasks or events. The report must include
`no_external_writes: true`; accepted candidates are candidates only, review
required/manual-only candidates stay marked for review/manual handling, and
malformed or unsafe candidates are rejected or blocked.

Phase 6 does not add live model/API calls, live Todoist writes, live Calendar
writes, Gmail send, credentials, OAuth, scheduler activation, dashboard UI,
OpenClaw runtime wiring, LaunchAgents, production SQLite access, broad
filesystem access, full PersonalOS vault access, raw journal ingestion,
legal/tax document ingestion, or autonomous legal/tax/portfolio/health/
relationship execution.

Phase 7 report jobs are coded jobs, not analyst personas. Report runs are
preview, dry-run, or simulated local records only. The deterministic fake
report runner validates an explicit report job and explicit input JSON, then
creates a local `report_runs` row only when dev/test run and write permissions
are enabled. Its output must include `no_external_writes: true`, and it must
not call network, live model APIs, TradingView, market data providers,
Todoist, Calendar, Gmail, OpenClaw, LaunchAgents, production SQLite, or
protected runtime paths.

Phase 7 Weekly Chart Pack reviews store manually supplied chart-pack data,
manually supplied TradingView alert digests, and ChatGPT-provided synthesis.
TradingView alerts are manually supplied and stored as validated JSON; they
are not fetched live. ChatGPT is the interpretation layer for market and
thesis synthesis. OpenClaw may later store approved workflow outputs and
track week-over-week changes, but OpenClaw does not analyze investments
independently.

Chart pack reviews must enforce structured summary sections for market
context, BTC context, ETH context, miner/HPC context, portfolio watch items,
week-over-week changes, follow-up candidates, and warnings. Follow-up
candidates are review/logging candidates only. Any represented investment
action candidate must be high risk and approval-required or manual-only, and
must not be marked executable or routed as a Todoist, Calendar, Gmail, or
portfolio execution action.

Phase 7 does not add live market data fetching, TradingView API access,
investment recommendations, portfolio execution, Todoist writes, Calendar
writes, Gmail send, live model/API calls, credentials, OAuth, scheduler
activation, dashboard UI, OpenClaw runtime wiring, LaunchAgents, production
SQLite access, full PersonalOS vault access, raw journal ingestion,
unrestricted filesystem access, or autonomous legal/tax/portfolio/health/
relationship execution.

Phase 8 Fitness Integration Foundation is not live fitness tracking and not a
data migration. The existing CSV-based local fitness tracker is preserved.
Fitness/strength remains separate from Grease-the-Groove. Phase 8 stores
dev/test integration labels, expected filenames, fixture validation runs, and
file contracts only. It uses labels such as `personal_os_fitness_csvs` instead
of absolute live paths. Fixture validation checks caller-supplied CSV headers
only and must return `no_external_writes: true` and
`no_live_personalos_access: true`.

Phase 8 has no Notion dependency, no live PersonalOS CSV reads or writes, no
Apple Health or wearable API integration, no live fitness data import, no
workout recommendation engine, no medical/health advice engine, no
Todoist/Calendar/Gmail writes, no live model/API calls, no credentials or
OAuth, no scheduler or LaunchAgents, no production SQLite/runtime state, no
dashboard UI yet, no full PersonalOS vault access, and no unrestricted
filesystem access. V1.5 may later add recovery/training context in briefings
after separate approval.

Phase 9B runtime bootstrap is not production activation and not a runtime
launch. It validates explicit `dev_runtime` and `local_runtime_preview`
profiles, requires no-send and no-external-write mode, rejects protected and
production-looking paths, previews pending migrations without mutation, and
creates a backup before migrating an existing explicit temp/dev runtime DB.

Phase 9B seed behavior writes only local SQLite state after explicit dev/test
write and run permissions are enabled. The seed profile disables
external/live-facing permissions, creates paused disabled preview routines,
creates a fake paused preview priority, and creates inert no-send draft
briefing window definitions. Briefing windows are schedule definitions only;
Phase 9B adds no scheduler and no daily briefing generation loop.

Phase 9B does not add live Todoist writes, live Calendar writes, Gmail send,
live model/API calls, Notion, Apple Health, TradingView, external API calls,
credentials, OAuth, scheduler activation, LaunchAgents, dashboard UI, web
server, production SQLite/runtime state mutation, protected PersonalOS access,
protected OpenClaw access, or real production activation.

Low-risk routine Todoist tasks may auto-write after the validated runtime module exists and permission is enabled.

High-value review and follow-up Todoist tasks may auto-write after validation when they meet the task schema.

High-stakes execution actions require approval.

Self-only review, deep work, admin, and routine Calendar blocks may auto-write after validation. Calendar events involving other people or high-stakes appointments require review.

No vague thoughts or raw emotional notes become Todoist tasks.

No prose-only model output may be used for execution.

## Validated Runtime Module Definition

A module is validated only after:

- Schema exists.
- Unit tests exist.
- Dry-run or no-send mode exists.
- Dedupe behavior exists where applicable.
- Permissions behavior is tested.
- Logging or completion report exists.
- One controlled live test passes if the module has side effects.

## Gmail Phase Boundaries

- Phase 0: no Gmail access.
- Phase 1: no-send scheduler and email infrastructure.
- Later: metadata or read-only access only if explicitly approved.
- Later: draft generation.
- Later: send-enabled only with ledger, idempotency, and permission gates.
- Gmail send remains an OpenClaw runtime responsibility, not a Codex development responsibility.

## Composer Safety

The composer model receives only a dedicated Composer Packet. It must not
receive broad filesystem access, raw notes, the full PersonalOS vault,
protected runtime paths, credentials, legal/tax source documents, Gmail bodies,
live Todoist API data, live Calendar API data, or unrestricted files.

Composer Packet input fields:

- `schema_version`
- `packet_id`
- `packet_type`
- `briefing_window`
- `source_date`
- `timezone`
- `generated_at`
- `inputs`
- `omissions`
- `warnings`

Allowed `inputs` sections:

- `routine_state`
- `priority_summaries`
- `followup_summaries`
- `todoist_task_summaries`
- `calendar_block_summaries`
- `calendar_availability_summary`
- `today_schedule_summary`
- `wsp_routine_rules`
- `prior_briefing_summaries`
- `completion_status`

Composer output must include structured JSON plus readable text. Required
sections are `email_briefs`, `todoist_tasks`, `calendar_blocks`, `followups`,
and `warnings`. Prose-only output is rejected. Missing or empty readable text
is rejected.

## Evidence Standard

Development work evidence:

- Diff summary.
- Test logs when tests exist or behavior changes.
- Unit or integration output when applicable.
- Brief implementation note.

Runtime or live operations evidence:

- Persisted completion report.
- Ledger or log snapshot.
- Safety flags.

Forensic bundles are only required for incidents, production activation, high-stakes operations, or duplicate/mutation anomalies.
