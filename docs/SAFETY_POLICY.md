# Safety Policy

## Purpose

Personal OS should feel lightweight to use while remaining safety-aware, configurable, logged, and reversible. This policy defines which systems are protected, how execution gates work, and what evidence is required.

## Current Boundary

Phases -1 through 13F-B are complete, and the Phase 6B, Phase 7B, Phase 8B,
Phase 12A, and Phase 12B fake/local smoke tests are complete. The current
Phase 13F-C work is read-only pre-live readiness status visibility. It may edit
only approved repository source, tests, and documentation for inert readiness
reports. It must not add migrations, runtime state, live rails, scheduler
activation, OpenClaw runtime operation, production DB activation, credential
loading, or live external writes.
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

## Pre-Live Readiness Rule

Before any Phase 14/live-rail work, the repo must satisfy:

- [Pre-Live Readiness Gate](PRE_LIVE_READINESS.md)
- [Live Rail Activation Policy](LIVE_RAIL_ACTIVATION_POLICY.md)
- [Operator Handoff Contract](OPERATOR_HANDOFF_CONTRACT.md)
- [Production DB Policy](PRODUCTION_DB_POLICY.md)

These documents and the inert Phase 13F-B readiness evaluator define policy
and readiness status only. Phase 13F-C may expose this status through local
read-only CLI/status/dashboard surfaces. These surfaces do not create live
permissions, activate production SQLite, activate schedulers, authorize
OpenClaw runtime workflows, or enable Gmail, Todoist, Calendar, PersonalOS
Markdown, or live model/API calls.

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

Phase 11A synthesis import permissions are stored in `permission_settings` and
are separate from apply/save, live execution, live model/API, Todoist,
Calendar, Gmail, PersonalOS Markdown, scheduler, and LaunchAgent permissions:

- synthesis_import_dev_test_read
- synthesis_import_dev_test_write
- synthesis_import_dev_test_preview

Synthesis import read/list/count helpers fail closed when the read key is
missing, disabled, invalid, or approval-only. Persisting a local preview
record requires both the write key and preview key. Pure parsing and preview
report generation may run without persistence. Phase 11A does not add apply
permissions or live permissions.

Phase 13A synthesis apply permissions are stored in `permission_settings` and
are separate from live execution, live model/API, Todoist, Calendar, Gmail,
PersonalOS Markdown, scheduler, LaunchAgent, production runtime, and
production database permissions:

- synthesis_apply_dev_test_read
- synthesis_apply_dev_test_write
- synthesis_apply_dev_test_apply

Synthesis apply read summaries fail closed when the read key is missing,
disabled, invalid, or approval-only. Applying a preview requires read, write,
and apply keys to be explicitly set to `auto_write` in dev/test. Phase 13A
does not add a production apply permission, live-write permission, external
rail permission, or dashboard mutation permission.

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

Phase 10A local dashboard Today View foundation is a read-only local dashboard
shell and read model. It may read existing state from a caller-supplied SQLite
connection or from an explicitly supplied temp/repo-local dev SQLite path opened
read-only. The Today View summary must include `no_external_writes: true`.
Dashboard rendering may produce local HTML or JSON for `Personal OS Today View`
only.

Phase 10A dashboard server helpers must bind to localhost-only by default and
reject public bind hosts. Dashboard DB path validation must reject protected
PersonalOS, OpenClaw, LaunchAgents, credential/OAuth-looking, and
production-looking paths. Phase 10A adds no new permission keys and no mutation
routes.

Phase 10A does not add live Todoist writes, live Calendar writes, Gmail send,
live model/API calls, Notion, Apple Health, TradingView, external API calls,
credentials, OAuth, scheduler activation, LaunchAgents, public internet
exposure, login/auth, task/calendar mutation from dashboard, routine editor,
priority editor, synthesis import, no-send daily briefing generation loop,
production SQLite/runtime state mutation, protected PersonalOS access,
protected OpenClaw access, or production runtime activation.

Phase 10B no-send daily briefing loop foundation is local/manual preview only.
It may build a daily plan from existing runtime state and Today View summaries,
select an inert briefing window, run the fake Composer path only, persist local
`daily_plans` and `briefing_outputs`, and produce readable text, manual export
only markdown, and a structured completion report.

Phase 10B permission keys are `briefing_loop_dev_test_read`,
`briefing_loop_dev_test_write`, and `briefing_loop_dev_test_run`. They fail
closed by default. Read/list/count helpers require the read key. Generating and
storing a no-send preview requires the write and run keys. No live/send
permission is added.

Phase 10B does not add Gmail sending, Gmail drafts, live Todoist writes, live
Calendar writes, Todoist/Calendar writes, live model calls,
OpenAI/OpenRouter/Anthropic calls, credentials, OAuth, scheduler or
LaunchAgents, public internet exposure, dashboard mutation, routine or
priority editors, synthesis import, real model routing, production
SQLite/runtime state mutation, protected PersonalOS access, protected OpenClaw
access, or external writes of any kind.

Phase 10C dashboard briefing integration is read-only dashboard visibility for
existing Phase 10B no-send outputs. It may expose a Today View
`briefing_output_summary`, a dashboard Briefing Outputs section, latest output
status, manual export preview, completion report safety flags, warning counts,
failed briefing counts, and the same summary through the existing JSON render
path.

The manual export preview is read-only. Phase 10C adds no generation button,
no dashboard mutation, no scheduler, no Gmail/model/Todoist/Calendar writes,
no Gmail drafts, no live model/API calls, no credentials, no OAuth, no
LaunchAgents, no production SQLite/runtime state mutation, no protected
PersonalOS access, no protected OpenClaw access, no public internet exposure,
no routine or priority editor, no synthesis import, and no external writes of
any kind.

Phase 10B manual exports are local fake/no-send content. Future real-content
redaction or review may be needed before broader network exposure or any
non-local dashboard access is considered.

Phase 11A synthesis import is preview-only. It accepts only structured
ChatGPT-synthesized or manually structured imports in canonical JSON,
Markdown with one fenced JSON block, or a documented structured Markdown
subset. Unsupported prose, raw notes, raw journals, full vault dumps,
legal/tax source documents, credential dumps, and unrestricted file input are
rejected.

Phase 11A normalizes accepted input to `synthesis_import.v1` and validates
candidate objects for priorities, projects, follow-ups, routine changes,
Todoist tasks, Calendar blocks, clarity notes, and review questions. Todoist
and Calendar candidates pass through the Phase 5 preview validators only; no
Todoist task row, Calendar block row, adapter call, or external mutation is
created by the import preview layer.

High-stakes candidates covering tax, legal, estate, portfolio, crypto,
investments, health, medical, relationship messages, family-sensitive
communication, or large financial commitments must not be `auto_allowed`.
Portfolio/crypto/investment execution language such as buy, sell, rotate,
rebalance, allocate, exit, enter, long, or short must be high risk and
approval-required or manual-only. Legal/tax/medical directives and
relationship messages to other people must be approval-required or manual-only.

Phase 11A preview reports must include `no_external_writes: true`,
`no_state_mutation: true`, `no_personalos_writes: true`,
`no_todoist_writes: true`, `no_calendar_writes: true`, `no_gmail_send: true`,
and `no_live_model_call: true`. Optional persistence stores only local preview
records in `synthesis_import_previews`. Phase 11A does not apply/save
candidates into priorities, routines, follow-ups, Todoist, Calendar, Gmail, or
PersonalOS Markdown.

Phase 11B dashboard synthesis import preview UI remains preview-only. It adds
a local dashboard form for structured ChatGPT synthesis and a single
`/synthesis-import/preview` POST route that calls the Phase 11A preview
engine. It may persist only `synthesis_import_previews` records when
`synthesis_import_dev_test_write` and
`synthesis_import_dev_test_preview` are enabled. Today View and dashboard
prior-preview summaries require `synthesis_import_dev_test_read`.

Phase 11B does not add an apply permission, apply/save route, broad dashboard
editor framework, auth/login, LAN/public bind relaxation, public internet
exposure, PersonalOS Markdown writer, Todoist writer, Calendar writer, Gmail
send/draft path, live model/API call, OpenAI/OpenRouter/Anthropic call,
scheduler, LaunchAgent, production runtime activation, credential/OAuth
access, protected PersonalOS access, `.openclaw` access, or live external
write. Raw notes, unsupported prose, credential/protected-looking input, and
unsafe high-stakes low/auto candidates remain rejected or blocked by the
Phase 11A gates.

Phase 12A operator CLI is local-only and no-send. The `personalos` command
requires explicit `--db` for every DB-backed operation and never bootstraps,
seeds, migrates, or creates a database implicitly. Read commands use existing
status and Today View helpers. Preview commands use existing fake/no-send
briefing and synthesis import helpers. File-output commands require explicit
`--output-file` and write only to paths that pass the shared safety checks.

Phase 12A rejects protected PersonalOS paths, protected OpenClaw paths,
LaunchAgents paths, credential/OAuth-looking paths, production-looking paths,
repo-local `var/` input paths, and repo-local `var/` output paths. The static
dashboard render command writes only a local HTML file and does not bind a web
server. Briefing export reads an existing briefing output and writes only the
existing manual export content to the explicit safe output path. Synthesis
preview reads only explicit safe input files, remains preview-only, and
persists only `synthesis_import_previews`.

Phase 12A does not add a scheduler, LaunchAgents, live Gmail send/draft,
Todoist writes, Calendar writes, live model/API calls, OpenAI/OpenRouter/
Anthropic integration, PersonalOS Markdown writes, `.openclaw` integration,
full PersonalOS vault access, Notion integration, wearable/Apple Health
integration, TradingView/market data integration, public/LAN dashboard access,
auth/login, apply/save import flow, routine or priority mutation forms,
side-effect ledger implementation, or production DB path activation.

Phase 12B adds local-only side-effect and idempotency ledgers. It records
future write intent candidates in `external_write_intents`, simulated/dry-run
attempts in `external_write_attempts`, and durable duplicate guards in
`idempotency_records`. Idempotency keys are deterministic from stable source,
target, operation, dedupe, and payload fields. Payload fingerprints are
deterministic canonical JSON SHA-256 fingerprints.

Phase 12B permission keys are `side_effect_ledger_dev_test_read`,
`side_effect_ledger_dev_test_write`, and
`side_effect_ledger_dev_test_record_attempt`. Operator-facing read summaries,
write helpers, and attempt helpers fail closed unless the relevant dev/test
permission is explicitly enabled. Internal Today/status/dashboard read models
may use an explicit unpermissioned summary helper for local no-write counts.
These keys are not live-write permissions and do not authorize Todoist,
Calendar, Gmail, PersonalOS Markdown, API, scheduler, or production runtime
writes.

Current idempotency keys use truncated SHA-256 material for deterministic
dev/test ledger keys, with full SHA-256 payload fingerprints stored beside
them. This is acceptable for local dev/test ledgers. Before any external
write is enabled, Phase 14/live-rail planning must decide the collision
posture, including whether to lengthen keys, add secondary uniqueness checks,
or store full digest material for live rails.

Every Phase 12B completion report and attempt row must preserve
`no_external_writes=true`, `no_send_mode=true`, `live_write=false`, and
`simulated_or_dry_run=true`. The schema rejects `live_write=1`,
`no_external_writes=0`, and `no_send_mode=0`. High-risk intent candidates
cannot use `auto_allowed`.

Phase 12B does not add live Todoist writes, live Calendar writes, Gmail
send/draft, PersonalOS Markdown writes, `.openclaw` integration, scheduler,
LaunchAgents, live model/API calls, OpenAI/OpenRouter/Anthropic integration,
production DB activation, apply/save synthesis import flow, dashboard mutation
forms, public/LAN dashboard exposure, auth/login, Apple Health/wearable
integration, Notion integration, TradingView/market data integration, or any
Phase 12C/live-rail work.

Phase 13A synthesis apply is internal SQLite state mutation only. It applies
previously stored `synthesis_import_previews` only when an explicit approval
JSON file references the same `preview_id` and lists candidate approvals
candidate by candidate. There is no approve-all default, no implicit apply
after preview, no raw-prose apply path, and no dashboard Apply button.

Phase 13A may insert deterministic records into `priorities`, `projects`, and
`followups` only. Every attempt writes an audit run to `synthesis_apply_runs`
and per-candidate outcomes to `synthesis_apply_items` with validation reports,
target IDs when relevant, and rollback metadata for inserted internal rows.
Repeated approval of the same preview candidate must safely skip duplicate
internal state records rather than silently creating duplicates.

Phase 13A unsupported candidates, including routine changes, Todoist tasks,
Calendar blocks, clarity notes, review questions, PersonalOS Markdown notes,
Gmail messages, relationship messages, and external execution candidates, are
recorded as unsupported, skipped, review-required, blocked, or failed. They
are not routed to Todoist, Calendar, Gmail, PersonalOS Markdown, external
write intents, adapters, files, APIs, or OpenClaw.

High-stakes execution candidates covering tax, legal, estate, portfolio,
crypto, investments, health, medical, relationship messages,
family-sensitive communication, or large financial commitments remain blocked
or review-required in Phase 13A. Manual-only candidates remain manual-only and
are not applied.

Phase 13B hardens the Phase 13A apply path without expanding its product
surface. Candidate validation and approval checks happen before mutation where
possible, then internal core-state inserts, apply run insertion, apply item
insertion, and preview apply-status updates execute inside one explicit SQLite
transaction. A priority, project, or follow-up created by synthesis apply must
not commit without the corresponding apply audit trail.

If an in-transaction write fails, Phase 13B rolls back the whole apply
transaction. A failed recovery audit may be written only after planned
core-state inserts are verified absent after rollback; that recovery report
must set `rolled_back=true`, `rollback_verified=true`, and
`internal_state_mutation=false`, and no recovery item may claim
`apply_status=applied`.

Phase 13B completion reports must preserve `no_external_writes=true`,
`no_send_mode=true`, `live_write=false`, `no_todoist_writes=true`,
`no_calendar_writes=true`, `no_gmail_send=true`,
`no_personalos_writes=true`, and `no_live_model_call=true`.
`internal_state_mutation=true` is used only when core SQLite state actually
changed. Phase 13B does not add live Todoist writes, live Calendar writes,
Gmail send/draft, PersonalOS Markdown writes, `.openclaw` integration,
scheduler, LaunchAgents, live model/API calls, OpenAI/OpenRouter/Anthropic
integration, production DB activation, dashboard mutation forms, public/LAN
dashboard exposure, auth/login, Apple Health/wearable integration, Notion
integration, TradingView/market data integration, or any Phase 14/live-rail
work.

Phase 13C scheduler/runtime-loop work is no-send simulation only. It may store
safe job records in `scheduler_jobs`, store foreground/manual simulated
attempts in `scheduler_runs`, and show scheduler summaries in status, Today
View, and the static dashboard. A scheduler job record is not production
scheduler activation.

Allowed Phase 13C simulated job types are `status_summary`, `today_view`,
`briefing_preview`, `side_effect_summary`, `synthesis_apply_summary`, and
`dashboard_render_preview`. `briefing_preview` uses the existing fake Composer
no-send path only. `dashboard_render_preview` requires an explicit safe output
file path and writes static HTML only.

Every scheduler run completion report must preserve `no_send_mode=true`,
`no_external_writes=true`, `fake_model_only=true`, `live_write=false`,
`external_mutation=false`, `scheduler_activation=false`,
`launch_agent_installed=false`, `no_todoist_writes=true`,
`no_calendar_writes=true`, `no_gmail_send=true`,
`no_gmail_draft=true`, `no_personalos_writes=true`, and
`no_live_model_call=true`. The scheduler schema rejects live-write,
external-mutation, scheduler-activation, and LaunchAgent-installed claims.

Phase 13C must not add LaunchAgents, crontab, daemon/background processes,
production runtime activation, live Gmail send/draft, live Todoist writes,
live Calendar writes, PersonalOS Markdown writes, `.openclaw` integration,
live model/API calls, OpenAI/OpenRouter/Anthropic integration, dashboard
mutation controls, public/LAN dashboard exposure, auth/login, Phase 14, or
live-rail work.

Phase 13D checkpoint hardening is internal/no-send cleanup only. Project
statuses are constrained to `active`, `paused`, `completed`, and `archived`.
Followup statuses are constrained to `open`, `proposed`, `completed`,
`archived`, and `blocked`. Synthesis import and synthesis apply must validate
those status vocabularies before any internal SQLite apply. The runtime
bootstrap known-permission registry lists newer module keys and seeds them
disabled by default, except the existing safe bootstrap read key.

Dashboard and Today View wording must say read-only except explicit local
synthesis preview creation. Phase 13D must not add new dashboard mutation
forms, an Apply button, live side-effect execution, scheduler activation,
LaunchAgents, crontab, daemons/background workers, production runtime
activation, Gmail send/draft, Todoist writes, Calendar writes, PersonalOS
Markdown writes, `.openclaw` integration, live model/API calls,
OpenAI/OpenRouter/Anthropic integration, public/LAN dashboard exposure,
auth/login, Phase 13E, Phase 14, or live-rail work.

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
