# Codex Workflow

## Role

Codex is the primary coding agent and software development layer for Personal OS. It edits repository code, tests, and documentation after phase gates. It does not act as the production operator.

Fable is an optional or future alternate coding agent for long-horizon software development work. Fable has the same production boundary as Codex unless a future policy says otherwise.

OpenClaw remains the production and runtime operator.

ChatGPT remains the strategy, synthesis, and audit layer.

## Current Work Type

Phases -1 through 13F-D plus Phase 13E-A and Phase 13E-B are complete, and
the Phase 6B, Phase 7B, Phase 8B, Phase 12A, and Phase 12B fake/local smoke
tests are complete. Phase 13E-C is approved only for dashboard safe-action and
status polish inside the repository. Codex may edit repository code, tests,
and documentation for this phase. Codex must not inspect or mutate protected
runtime paths, external systems, credentials, production ledgers, production
SQLite state, production state, OpenClaw runtime workflows, or live rails.

Canonical full-suite command:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py"
```

Run tests with `PYTHONPATH=src`; omitting it can cause misleading import
failures.

## Phase Rules

Phase -1 is complete and committed. Phase 0 must be read-only inventory first and requires explicit approval before starting.

Phase 0 may inspect specified live paths only after explicit approval for that inventory scope. Proposed read-only paths may include:

- `/Users/coldstake/PersonalOS`
- `/Users/coldstake/.openclaw`
- `/Users/coldstake/Library/LaunchAgents`
- `/Users/coldstake/dev/personal-os`

Phase 0 forbidden actions:

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

After Phase 0, Codex may edit code, tests, and docs in repo branches according to the approved plan.

Before any future Phase 14/live-rail work, Codex/Fable must treat the
following policy docs as required gates:

- [Pre-Live Readiness Gate](PRE_LIVE_READINESS.md)
- [Live Rail Activation Policy](LIVE_RAIL_ACTIVATION_POLICY.md)
- [Activation Checklist](ACTIVATION_CHECKLIST.md)
- [First-Live Pilot Protocol](FIRST_LIVE_PILOT_PROTOCOL.md)
- [Operator Handoff Contract](OPERATOR_HANDOFF_CONTRACT.md)
- [Production DB Policy](PRODUCTION_DB_POLICY.md)

Phase 13F-A through Phase 13F-D create policy, readiness, checklist, and pilot
protocol gates only. They do not authorize implementation work, production DB
activation, scheduler activation, OpenClaw runtime operation, or live external
writes.

## Allowed Codex Work

Codex may:

- Read repository-local files.
- Edit documentation in this repository.
- Edit code and tests after the correct phase gate.
- Produce diff summaries and implementation notes.
- Run local tests for repository code.
- Document assumptions, acceptance criteria, and safety boundaries.

## Prohibited Codex Work

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
- Touch runtime or production state.
- Create scripts that run live workflows.
- Treat docs-only readiness policy as permission to implement or activate live
  rails.

## Development Database Boundary

Production SQLite state lives on the Mac Mini runtime path. Development and test SQLite files live inside repo-local temporary or test paths. Codex may create and edit dev/test databases in this repository, but may not mutate production SQLite state without explicit approval.

Production migrations require a backup before migration. Production backups should include periodic JSON and SQLite snapshots.

## Phase 3 Routine Engine Boundary

The Phase 3 routine engine foundation is internal and dev/test-only. It may:

- Read routines through permission-gated helpers.
- Create routine records and update status/enabled fields through
  permission-gated helpers.
- Record routine completions in an injected dev/test SQLite connection.
- Return dry-run and non-dry-run inert result dicts for tests and later
  development surfaces.

Phase 3 did not start a scheduler, activate recurring automation, wire
OpenClaw, create LaunchAgents, add external API clients, touch Gmail, Todoist,
or Calendar, write production SQLite, add credentials, expose a web surface, or
perform priority engine work.

The Phase 4 priority engine foundation is internal and dev/test-only. It may:

- Read priorities through permission-gated helpers.
- Create priority records and update fields or status through permission-gated
  helpers.
- Return dry-run and non-dry-run inert result dicts for tests and later
  development surfaces.
- Return deterministic active-priority and counts-by-status summaries.

Phase 4 may not infer priorities from raw notes, rank priorities
automatically, generate tasks, start a scheduler, add idempotency/send ledger
behavior, activate runtime automation, wire OpenClaw, create LaunchAgents, add
external API clients, touch Gmail, Todoist, or Calendar, write production
SQLite, add credentials, expose a dashboard or API surface, generate composer
packets, or start Phase 5.

## Phase 7 Report Jobs and Chart Pack Boundary

The Phase 7 report jobs and Weekly Chart Pack foundation is internal and
dev/test-only. It may:

- Define coded report job records in `report_jobs`.
- Store preview, dry-run, and simulated local report run records in
  `report_runs`.
- Store manually supplied chart-pack data, manually supplied TradingView alert
  digest JSON, and ChatGPT-provided synthesis in `chart_pack_reviews`.
- Validate required structured summary sections for market context, BTC
  context, ETH context, miner/HPC context, portfolio watch items,
  week-over-week changes, follow-up candidates, and warnings.
- Run a deterministic fake report runner that writes only local dev/test
  `report_runs` records after explicit dev/test permissions are enabled.

Phase 7 may not fetch live market data, call TradingView APIs, make investment
recommendations, create portfolio execution tasks, write Todoist, write
Calendar, send Gmail, call live model APIs, add credentials or OAuth, start a
scheduler, create or load LaunchAgents, write production SQLite, inspect
protected PersonalOS or OpenClaw paths, or expose a dashboard or API surface.

ChatGPT is the interpretation layer for market and thesis synthesis. OpenClaw
stores approved workflow outputs later but does not analyze investments
independently. Report jobs are coded jobs, not analyst personas.

## Phase 8 Fitness Integration Boundary

The Phase 8 Fitness Integration Foundation is internal and dev/test-only. It
may:

- Define `fitness_integration_state`, `fitness_validation_runs`, and
  `fitness_file_contracts` records in dev/test SQLite.
- Preserve the existing CSV-based local fitness tracker.
- Define expected file contracts for `workout_sessions.csv`,
  `workout_exercises.csv`, `weekly_recovery.csv`, and
  `exercise_library.csv`.
- Validate fixture CSV headers supplied by tests or callers.
- Return deterministic reports with `no_external_writes: true` and
  `no_live_personalos_access: true`.
- Gate read, write, and validation helpers with
  `fitness_integration_dev_test_read`, `fitness_integration_dev_test_write`,
  and `fitness_integration_dev_test_validate`.

Phase 8 may not read or write live PersonalOS CSVs, inspect protected
PersonalOS or OpenClaw paths, integrate with Notion, Apple Health, HealthKit,
Garmin, Whoop, Oura, Fitbit, or wearable APIs, import live fitness data,
infer workouts, recommend workouts, provide medical or health advice, write
Todoist, write Calendar, send Gmail, call live model APIs, add credentials or
OAuth, start a scheduler, create or load LaunchAgents, write production
SQLite/runtime state, expose dashboard UI yet, or start deeper V1.5 briefing
integration.

## Phase 9B Runtime DB Bootstrap Boundary

The Phase 9B Runtime DB Bootstrap Foundation is internal and local/dev-preview
only. It may:

- Validate explicit runtime bootstrap profiles for `dev_runtime` and
  `local_runtime_preview`.
- Reject protected, credential/OAuth-looking, and production-looking paths.
- Build non-mutating bootstrap previews with pending migrations, backup path,
  seed profile, and safety flags.
- Create timestamped backups before migrating existing explicit temp/dev DBs.
- Apply repository migrations to explicit temp/dev SQLite DBs.
- Seed safe local-only state after explicit dev/test write and run permissions
  are enabled.
- Record local bootstrap evidence in `runtime_bootstrap_runs`.
- Store inert no-send/manual-export briefing window definitions.

Phase 9B permission keys are
`runtime_bootstrap_dev_test_read`, `runtime_bootstrap_dev_test_write`, and
`runtime_bootstrap_dev_test_run`. They fail closed by default and allow work
only when explicitly set to `auto_write`.

Phase 9B may not activate production runtime behavior, mutate production
SQLite/runtime state, inspect protected PersonalOS or OpenClaw paths, create
or load LaunchAgents, start a scheduler, expose a dashboard or web server,
generate a daily briefing loop, send Gmail, write Todoist, write Calendar,
call live model APIs, call Notion/Apple Health/TradingView or other external
APIs, read credentials/OAuth, or create live external write permissions.

## Phase 10A Local Dashboard Today View Boundary

The Phase 10A local dashboard Today View foundation is read-only and local
only. It may:

- Build Today View summaries from existing SQLite state through caller-supplied
  connections.
- Render `Personal OS Today View` HTML or JSON from a supplied temp/repo-local
  dev SQLite DB path opened read-only.
- Start a standard-library dashboard server only when explicitly invoked.
- Bind to localhost-only by default and reject public bind hosts.
- Reject protected, credential/OAuth-looking, and production-looking dashboard
  DB paths.

Phase 10A adds no new permission keys. It may not write Todoist, write
Calendar, send Gmail, call live model APIs, call Notion/Apple
Health/TradingView or other external APIs, read credentials/OAuth, start a
scheduler, create or load LaunchAgents, expose public internet access, add
login/auth, mutate task/calendar state from the dashboard, add routine or
priority editors, import synthesis, start a no-send daily briefing generation
loop, mutate production SQLite/runtime state, inspect protected PersonalOS or
OpenClaw paths, or activate production runtime behavior.

## Phase 10B No-Send Daily Briefing Loop Boundary

The Phase 10B no-send daily briefing loop foundation is local/manual preview
only. It may:

- Build no-send daily plans from existing SQLite runtime state and Today View
  summaries.
- Read inert `briefing_windows` definitions by source date, timezone, and
  window name.
- Generate briefing previews through the fake Composer path only.
- Store local `daily_plans`, Composer packet/output/model-run records, and
  `briefing_outputs`.
- Produce readable text, manual export only markdown, and a structured
  completion report.

Phase 10B permission keys are `briefing_loop_dev_test_read`,
`briefing_loop_dev_test_write`, and `briefing_loop_dev_test_run`. They fail
closed by default. Read/list/count helpers require the read key. Generating and
storing a no-send preview requires the write and run keys. No Gmail, Todoist,
Calendar, model, scheduler, or live/send permission is added.

Phase 10B may not add Gmail sending, Gmail drafts, live Todoist writes, live
Calendar writes, Todoist/Calendar writes, live model calls,
OpenAI/OpenRouter/Anthropic calls, credentials or OAuth, scheduler or
LaunchAgents, public internet exposure, dashboard mutation, routine or
priority editors, synthesis import, real model routing, production
SQLite/runtime state mutation, protected PersonalOS or OpenClaw access, or
external writes of any kind.

## Phase 10C Dashboard Briefing Integration Boundary

The Phase 10C dashboard briefing integration is read-only visibility for
existing Phase 10B no-send briefing outputs. It may:

- Add a Today View `briefing_output_summary` for existing `daily_plans` and
  `briefing_outputs`.
- Render a dashboard Briefing Outputs section with latest output status,
  manual export preview, completion report safety flags, warnings, and failed
  briefing status.
- Include briefing output summaries in the existing `/today.json` route.

The manual export preview is read-only. Phase 10C may not add a generation
button, Gmail sending, Gmail drafts, live Todoist writes, live Calendar writes,
Gmail/model/Todoist/Calendar writes, live model calls,
OpenAI/OpenRouter/Anthropic calls, credentials or OAuth, scheduler or
LaunchAgents, public internet exposure, dashboard mutation, routine or
priority editors, synthesis import, production SQLite/runtime state mutation,
protected PersonalOS or OpenClaw access, or external writes of any kind.

Phase 10B manual exports are local fake/no-send content. Future real-content
redaction or review may be needed before broader network exposure or any
non-local dashboard access is considered.

## Phase 11A ChatGPT Synthesis Import Preview Boundary

The Phase 11A synthesis import foundation is preview-only. It may:

- Parse canonical JSON, Markdown with one fenced JSON block, or a documented
  structured Markdown heading/bullet subset.
- Accept only `chatgpt_synthesis`, `manual_structured_import`, and
  `fake_fixture` source types.
- Reject raw notes, raw journals, full vault dumps, legal/tax source
  documents, credential dumps, unrestricted file input, unsupported prose, and
  credential-like input.
- Normalize accepted input to `synthesis_import.v1`.
- Validate preview candidates for priorities, projects, follow-ups, routine
  changes, Todoist tasks, Calendar blocks, clarity notes, and review
  questions.
- Route Todoist and Calendar candidates through existing Phase 5 preview
  validators only.
- Store local preview records in `synthesis_import_previews` only when
  dev/test write and preview permissions are explicitly enabled.

Phase 11A permission keys are `synthesis_import_dev_test_read`,
`synthesis_import_dev_test_write`, and `synthesis_import_dev_test_preview`.
They fail closed by default. Read/list/count helpers require the read key.
Persisting a preview record requires the write and preview keys. No apply or
live permission is added.

Phase 11A may not ingest raw journals as tasks, automatically create tasks
from raw notes, apply/save candidates into priorities/routines/follow-ups,
write PersonalOS Markdown, write Todoist, write Calendar, send or draft Gmail,
call live model APIs, call OpenAI/OpenRouter/Anthropic, add a scheduler or
LaunchAgents, activate production runtime, access `.openclaw`, access the full
PersonalOS vault, add dashboard mutation/edit forms, add a paste box UI,
expose public internet access, read credentials/OAuth, or perform live
external writes of any kind.

## Phase 11B Dashboard Synthesis Import Preview UI Boundary

The Phase 11B dashboard synthesis import preview UI is preview-only. It may:

- Add a local dashboard `ChatGPT Synthesis Import Preview` section with a
  structured synthesis textarea, source fields, safety banner, and one
  `Preview import` button.
- Add `GET /synthesis-import` and `POST /synthesis-import/preview` on the
  existing localhost-only dashboard server.
- Route form-encoded structured input through the existing Phase 11A preview
  engine.
- Persist only `synthesis_import_previews` when
  `synthesis_import_dev_test_write` and
  `synthesis_import_dev_test_preview` are enabled.
- Read prior-preview summaries only when `synthesis_import_dev_test_read` is
  enabled.
- Render preview reports with candidate buckets, questions for review,
  warnings, bounded escaped raw excerpts, and no-write/no-model safety flags.

Phase 11B may not apply/save candidates into priorities, routines,
follow-ups, Todoist, Calendar, Gmail, or PersonalOS Markdown; write protected
PersonalOS files; write Todoist; write Calendar; send or draft Gmail; call
live model APIs; call OpenAI/OpenRouter/Anthropic; add live permissions; add
an apply permission; add a scheduler or LaunchAgents; activate production
runtime; access `.openclaw`; access the full PersonalOS vault; expose public
internet access; relax localhost/LAN bind rules; add auth/login; read
credentials/OAuth; or perform live external writes of any kind.

Phase 12A adds only a local operator CLI for no-send workflows. CLI commands
must require explicit `--db` for DB-backed operations, must require explicit
`--output-file` for file-writing operations, and must reject protected,
credential/OAuth-looking, production-looking, and repo-local `var/` input and
output paths. The command layer should call existing module APIs for status,
Today View, fake/no-send briefing preview, briefing export, structured
synthesis preview, and static dashboard rendering. It must not bootstrap,
seed, migrate, bind a server, activate production runtime, write PersonalOS
Markdown, write Todoist or Calendar, send or draft Gmail, call live model
APIs, create LaunchAgents, inspect protected PersonalOS or OpenClaw paths, or
perform live external writes.

Phase 13E-A may improve the operator/status report vocabulary and JSON shape
only. The relevant commands are `personalos readiness status`,
`personalos readiness status --json`, `personalos status --db <safe_db>`, and
`personalos status --db <safe_db> --json`. The report should make the current
inert posture obvious: `not_ready`, report-only mode, disabled live rails,
inactive scheduler, inactive production DB, credentials not loaded/read, no
external writes, safe local actions, blocked live actions, and evidence that
can be pasted back into ChatGPT for audit.

Phase 13E-A must not start Phase 14, add live integrations, load credentials,
activate production SQLite, create LaunchAgents/crontab entries, start
daemons/background loops, call OpenClaw, call live model/API providers, or
write Gmail, Todoist, Google Calendar, or PersonalOS Markdown.

Phase 13E-B may polish the existing local operator CLI by improving help text,
adding `personalos workflows`, clarifying human-readable completion summaries,
preserving JSON output, improving safe next-step errors, and documenting how
to paste no-send CLI evidence back to ChatGPT for audit. It must reuse the
Phase 13E-A `operator_status.v1` vocabulary for readiness, safe local actions,
blocked actions, credentials, external writes, scheduler status, and
production DB status.

Phase 13E-B must not create live integrations, load credentials, activate
production SQLite, create LaunchAgents/crontab entries, start daemons or
background loops, call OpenClaw, call live model/API providers, write
PersonalOS Markdown, or write Gmail, Todoist, or Google Calendar.

Phase 13E-C may polish dashboard/status presentation by rendering the
existing `operator_status_summary` as a NOT READY inert/no-send/report-only
banner, safe local action list, blocked live action list, and inert evidence
panel. It may clarify dashboard wording for previews, approved local apply
history, no-send briefing output, and simulated scheduler summaries. It must
reuse `operator_status.v1` vocabulary and keep the panels informational only.

Phase 13E-C must not add dashboard activation controls, credential/OAuth UI,
scheduler controls, production DB toggles, new live routes, live integrations,
credential loading, LaunchAgent/crontab entries, daemons/background loops,
OpenClaw calls, live model/API calls, PersonalOS Markdown writes, Gmail sends,
Todoist writes, or Google Calendar writes.

## Phase 12B Side-Effect and Idempotency Ledger Boundary

Phase 12B may add local SQLite migrations, helper functions, tests, docs, and
minimal CLI support for side-effect intent ledgers, idempotency records,
duplicate prevention, dry-run/simulated attempts, and read-only summaries.

Allowed commands and helpers are permissioned read-only summary helpers and
simulated ledger writes such as `personalos side-effects summary` and
`personalos side-effects record-dry-run`. Operator-facing summaries require
`side_effect_ledger_dev_test_read`. Simulated writes must use explicit safe
operator paths and must preserve `no_external_writes=true`,
`no_send_mode=true`, `live_write=false`, and `simulated_or_dry_run=true`.

Phase 12B must not add an execute/apply command, live Todoist writes, live
Calendar writes, Gmail send/draft, PersonalOS Markdown writes, `.openclaw`
integration, scheduler, LaunchAgents, live model/API calls,
OpenAI/OpenRouter/Anthropic integration, production DB activation, apply/save
synthesis import flow, dashboard mutation forms, public/LAN dashboard
exposure, auth/login, Apple Health/wearable integration, Notion integration,
TradingView/market data integration, or Phase 12C/live-rail work.

## Phase 13A Approval-Gated Synthesis Apply Boundary

Phase 13A may add local SQLite migrations, helper functions, tests, docs,
CLI support, and read-only summaries for applying reviewed synthesis import
previews into safe internal core state. The only apply command is
`personalos synthesis apply --db <safe_db> --preview-id <id> --approval-file
<safe_json>`.

Allowed internal apply targets are priorities, projects, and follow-ups.
Approval must be explicit and candidate-by-candidate. The approval file must
reference the same `preview_id`; there is no approve-all default, implicit
apply after preview, raw-prose apply path, or dashboard Apply button.

Phase 13A must record every apply attempt in `synthesis_apply_runs` and every
candidate outcome in `synthesis_apply_items`.

Phase 13B hardens that apply path by making the internal core-state insert,
apply run insert, apply item inserts, and preview apply-status update one
explicit SQLite transaction. If an in-transaction write fails, the transaction
must roll back. A failed recovery audit may be recorded only after planned core
inserts are verified absent; that report must set `rolled_back=true` and
`internal_state_mutation=false`, and no recovery item may claim
`apply_status=applied`.

Synthesis apply completion reports must preserve `no_external_writes=true`,
`no_send_mode=true`, `live_write=false`, `no_todoist_writes=true`,
`no_calendar_writes=true`, `no_gmail_send=true`,
`no_personalos_writes=true`, and `no_live_model_call=true`.
`internal_state_mutation=true` is allowed only when core SQLite rows actually
changed.

Phase 13B must not add live Todoist writes, live Calendar writes, Gmail
send/draft, PersonalOS Markdown writes, external write intent creation,
`.openclaw` integration, scheduler, LaunchAgents, live model/API calls,
OpenAI/OpenRouter/Anthropic integration, production DB activation, dashboard
mutation forms or POST apply routes, public/LAN dashboard exposure,
auth/login, Apple Health/wearable integration, Notion integration,
TradingView/market data integration, or Phase 14/live-rail work.

## Phase 13C No-Send Scheduler Runtime Loop Boundary

Phase 13C may add local SQLite migrations, helper functions, tests, docs, and
CLI support for representing scheduler jobs and running foreground/manual
simulated jobs. It may add read-only scheduler summaries to status, Today View,
and dashboard output.

Allowed simulated job types are `status_summary`, `today_view`,
`briefing_preview`, `side_effect_summary`, `synthesis_apply_summary`, and
`dashboard_render_preview`. Briefing preview must use the existing fake
Composer no-send path. Dashboard render preview must require an explicit safe
output file.

Phase 13C completion reports must preserve `no_send_mode=true`,
`no_external_writes=true`, `fake_model_only=true`, `live_write=false`,
`external_mutation=false`, `scheduler_activation=false`, and
`launch_agent_installed=false`. `enabled=true` on a scheduler job means
enabled for dev/test simulation only.

Phase 13C must not install or load LaunchAgents, edit crontab, start daemons,
spawn background workers, activate production runtime, send or draft Gmail,
write Todoist, write Calendar, write PersonalOS Markdown, integrate
`.openclaw`, call live model/API providers, add OpenAI/OpenRouter/Anthropic
clients, add dashboard mutation controls, expose public/LAN dashboard access,
start Phase 14, or start live-rail work.

## Phase 13D Checkpoint Hardening Boundary

Phase 13D may add local SQLite migrations, helper validation, tests, and docs
to tighten internal state and operator clarity after the Phase 13C checkpoint
audit. It may constrain project and followup status values, enforce
side-effect ledger read permission on operator-facing summary paths, make
known permission seeds auditable and disabled by default, clarify dashboard
wording, and clean up SQLite ResourceWarnings.

Phase 13D dashboard wording is read-only except explicit local synthesis
preview creation. It may not add an Apply button, broad dashboard editor,
live rails, external writes, scheduler activation, production activation,
LaunchAgents, `.openclaw` integration, PersonalOS Markdown writes, Gmail,
Todoist, Calendar, live model/API calls, Phase 13E, Phase 14, or live-rail
work.

## Runtime Module Validation

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

## Timezone and Dashboard Notes

America/Chicago is Chris's operating timezone for briefings and routines. The Mac Mini system timezone may differ. Scheduler code must explicitly use the configured operating timezone and must not assume the host timezone.

The V1 dashboard is local-network only, has no public internet exposure, and has no login or password by choice. Risks include accidental local network access, stale browser sessions, and exposure from trusted devices on the network. Future security options may include a password, device allowlist, Tailscale/VPN access, or local-only binding.

## Development Evidence Standard

For development work, Codex should return:

- Files changed.
- Diff summary.
- Test logs or command output when applicable.
- Unit or integration output when applicable.
- Brief implementation note.
- Assumptions and recommended next step.

## Runtime Evidence Standard

Runtime and live operations are owned by OpenClaw after approval gates. Evidence should include:

- Persisted completion report.
- Ledger or log snapshot.
- Safety flags.

Forensic bundles are reserved for incidents, production activation, high-stakes operations, or duplicate/mutation anomalies.

## Branch and Commit Guidance

Documentation-only changes may be made directly in the repo when requested. Code changes after Phase 0 should usually happen in branches with focused commits and tests.

Do not commit unless the user explicitly asks for a commit.

## Model Boundary

Codex uses the repository as its working surface. It must not give a composer model broad filesystem access or unrestricted production context. Composer integrations must use dedicated Composer Packets and structured JSON outputs before execution.

Composer Packet `composer_packet.v1` may include only narrow structured
summaries: routine state, priority summaries, selected follow-up summaries,
Todoist task summaries, Calendar block summaries, Calendar availability
summary, today's schedule summary, WSP/routine rules, prior briefing
summaries, and completion status.

Composer integrations must reject packets or outputs that claim broad
filesystem access, raw notes, full vault access, protected runtime paths,
Gmail bodies, live Todoist API data, live Calendar API data, legal/tax source
documents, credentials, secrets, OAuth tokens, unrestricted file access, raw
journal archives, or arbitrary filesystem paths.

Composer output schema must include:

- Structured JSON.
- Non-empty readable text.
- `email_briefs`
- `todoist_tasks`
- `calendar_blocks`
- `followups`
- `warnings`

Phase 6 Composer work is fake-adapter and report-only. It must not add live
model/API calls, Gmail send, live Todoist writes, live Calendar writes,
credentials, OAuth, scheduler activation, LaunchAgents, production SQLite,
OpenClaw runtime wiring, or dashboard UI.
