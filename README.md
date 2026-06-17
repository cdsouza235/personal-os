# Personal OS

Personal OS is a modular, local-first productivity, routine, priority, and execution operating system. It helps Chris think clearly, maintain routines, manage high-value priorities, generate briefings, create Todoist tasks, schedule Calendar blocks, preserve durable notes, and run reports through OpenClaw on the Mac Mini.

This repository is the private code source of truth for Personal OS. It now
contains local dev/test foundations through Phase 13D: SQLite migrations and
state helpers, no-send CLI and dashboard surfaces, fake/simulated execution
rails, approval-gated internal synthesis apply, side-effect/idempotency
ledgers, simulated scheduler records, and Phase 13F-A pre-live readiness
policy docs. It still has no live/prod rails:
no live Gmail, Todoist, Calendar, model/API, LaunchAgent, OpenClaw,
PersonalOS Markdown, production SQLite, or background scheduler activation is
enabled from this repo.

## Operating Roles

- Chris: owner, final approver, source of judgment and priorities.
- ChatGPT: thought partner, synthesis layer, analysis layer, PRD writer, architect, and auditor.
- Codex: primary coding agent and software development layer for repository code, tests, and documentation.
- Fable: optional or future alternate coding agent for long-horizon software development work.
- OpenClaw: local Personal Assistant and runtime operator on the Mac Mini.
- Mac Mini: always-on runtime host, OpenClaw host, SQLite state host, local PersonalOS file host, scheduler, and local repo clone.
- GitHub private repo: source of truth for code.
- SQLite: structured runtime state.
- Markdown, Obsidian, and PersonalOS: Clarity Notes, General Follow-Up Notes, protocols, logs, and reviews.
- Todoist, Calendar, and Gmail: execution rails, only touched by validated runtime modules.

## V1 Scope

- Local dashboard shell.
- Routine editor.
- Today view.
- Priority registry.
- ChatGPT synthesis import box.
- SQLite runtime state store.
- 8am, 12pm, 4pm, and 8pm briefing generation.
- Todoist auto-write for low-risk routine tasks and follow-ups.
- Calendar auto-write for approved self-only blocks.
- Gmail briefings.
- PersonalOS Markdown Clarity Notes and General Follow-Up Notes.
- Configurable permissions.
- System status and logs.
- Reports/jobs module shell.
- Fitness integration hook.
- Weekly chart pack workflow hook.

## Dashboard Requirements

The V1 dashboard is local-network only, with no public internet exposure and no login or password requirement by choice. It should be mobile-friendly for iPhone and usable from Windows or Mac browsers on the local network.

This is a deliberate V1 tradeoff, not an absence of risk. Risks include accidental local network access, stale browser sessions, and exposure from trusted devices on the network. Future security options may include a password, device allowlist, Tailscale/VPN access, or local-only binding.

Planned sections:

- Today View
- Routine Editor
- Priority Editor
- Todoist/Calendar Preview
- System Status/Logs
- Settings/Permissions
- Reports/Jobs shell

## State Architecture

- GitHub private repo: code source of truth.
- SQLite on the Mac Mini: structured runtime state.
- Markdown and Obsidian: Clarity Notes, Follow-Up Notes, logs, and protocols.
- Mac Mini: runtime and deployment host.
- OpenClaw: local runtime operator.
- Codex: primary software developer.
- Fable: optional or future alternate coding agent.

America/Chicago is Chris's operating timezone for briefings and routines. The Mac Mini system timezone may differ, so scheduler code must explicitly use the configured operating timezone and must not assume the host timezone.

Production SQLite state lives on the Mac Mini runtime path. Development and test SQLite files live inside repo-local temporary or test paths. Codex may create and edit dev/test databases in this repository, but may not mutate production SQLite state without explicit approval. Production migrations require a backup first, and production backups should include periodic JSON and SQLite snapshots.

## Safety Boundary

Codex may work on documentation, tests, and repository code after the appropriate phase gate, but OpenClaw remains the production/runtime operator.

Codex must not send email, write Todoist, write Calendar, load LaunchAgents, modify production ledgers, mutate production SQLite state, run live OpenClaw workflows, inspect `/Users/coldstake/PersonalOS`, inspect `/Users/coldstake/.openclaw`, touch credentials, or touch production state without explicit approval.

Before any Phase 14/live-rail work, the repo must satisfy the docs-only
[Pre-Live Readiness Gate](docs/PRE_LIVE_READINESS.md), the
[Live Rail Activation Policy](docs/LIVE_RAIL_ACTIVATION_POLICY.md), the
[Operator Handoff Contract](docs/OPERATOR_HANDOFF_CONTRACT.md), and the
[Production DB Policy](docs/PRODUCTION_DB_POLICY.md). These policies do not
activate live rails, production SQLite, OpenClaw workflows, schedulers, or
live model/API calls.

The first live-system interaction phase is Phase 0 read-only inventory.

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

## Repository Layout

Existing repo scaffold paths:

```text
docs/          Product, architecture, safety, roadmap, and Codex workflow docs.
app/           Placeholder for local dashboard and API surfaces.
personalos/    Placeholder for domain modules.
scripts/       Reserved for later inert or approved helper scripts.
tests/         Placeholder for repository tests.
.codex/        Codex-local project guidance and metadata.
```

Planned future modules include routines, priorities, composer, Todoist, Calendar, Gmail, reports, evidence, dashboard views, and local API surfaces.

Protected live runtime paths are outside this repository and must not be inspected or mutated without explicit approval. They include `/Users/coldstake/PersonalOS`, `/Users/coldstake/.openclaw`, LaunchAgents, credentials, production ledgers, production SQLite state, and other production runtime state.

## Current Phase

Phases -1 through 13D are complete. The Phase 6B, Phase 7B, Phase 8B,
Phase 12A, and Phase 12B fake/local smoke tests are complete. Phase 13F-A is
a docs-only pre-live readiness gate. It adds policy documents for live rail
activation, operator handoff, and production DB activation before any future
Phase 14/live-rail work.

Phase 13F-A must not add source code, migrations, configs, runtime state,
scripts, live rails, scheduler activation, LaunchAgents, crontab entries,
daemons, background workers, production runtime state, OpenClaw runtime
operation, or live external writes.

Canonical full-suite test command:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py"
```

Run the suite with `PYTHONPATH=src`; running without it can produce misleading
import failures that do not reflect the repo state.

Phase 12A added the `personalos` command-line surface so Chris/OpenClaw can
run existing inert read, preview, export, and static-render workflows without
custom smoke scripts. Every DB-backed command requires an explicit `--db`
path. Every file-writing command requires an explicit `--output-file` path.
The CLI rejects protected PersonalOS/OpenClaw paths, LaunchAgents paths,
credential/OAuth-looking paths, production-looking paths, and repo-local
`var/` output paths.

Supported local CLI commands:

- `personalos status --db /tmp/personalos-preview.sqlite3`
- `personalos today --db /tmp/personalos-preview.sqlite3 --date 2026-06-15 --timezone America/Chicago`
- `personalos briefing preview --db /tmp/personalos-preview.sqlite3 --date 2026-06-15 --timezone America/Chicago --window morning`
- `personalos briefing export --db /tmp/personalos-preview.sqlite3 --briefing-output-id <id> --output-file /tmp/morning-brief.md`
- `personalos synthesis preview --db /tmp/personalos-preview.sqlite3 --input-file /tmp/structured-synthesis.json --source-type chatgpt_synthesis`
- `personalos synthesis apply --db /tmp/personalos-preview.sqlite3 --preview-id <preview_id> --approval-file /tmp/synthesis-approval.json`
- `personalos side-effects summary --db /tmp/personalos-preview.sqlite3`
- `personalos side-effects record-dry-run --db /tmp/personalos-preview.sqlite3 --input-file /tmp/side-effect-intent.json`
- `personalos scheduler jobs --db /tmp/personalos-preview.sqlite3`
- `personalos scheduler preview --db /tmp/personalos-preview.sqlite3 --date 2026-06-15 --timezone America/Chicago`
- `personalos scheduler run --db /tmp/personalos-preview.sqlite3 --job-type status_summary`
- `personalos scheduler seed-dev --db /tmp/personalos-preview.sqlite3 --profile safe_no_send`
- `personalos dashboard render --db /tmp/personalos-preview.sqlite3 --date 2026-06-15 --timezone America/Chicago --output-file /tmp/today.html`

The CLI prints human-readable completion reports by default and supports
`--json` where practical. It does not bootstrap, migrate, bind a server, write
PersonalOS Markdown, write Todoist or Calendar, send or draft Gmail, call live
model APIs, install or activate an OS scheduler, activate production runtime,
access protected PersonalOS/OpenClaw paths, or perform live external writes.
The only seed command is the explicit Phase 13C `scheduler seed-dev` path,
which inserts safe dev/test scheduler job records only. The Phase 13A
`synthesis apply` command is the only synthesis apply surface and mutates only
internal dev/test SQLite core tables after explicit approval.

Phase 12B adds `external_write_intents`, `external_write_attempts`, and
`idempotency_records`. The `side-effects summary` command is read-only and
requires explicit `side_effect_ledger_dev_test_read` permission. The
`side-effects record-dry-run` command records only local dev/test ledger rows
from an explicit safe JSON input file and requires explicit
`side_effect_ledger_dev_test_write` and
`side_effect_ledger_dev_test_record_attempt` permissions. It cannot execute,
apply, send, draft, write files into PersonalOS, call external APIs, or claim
`live_write=true`.

Phase 12B permission keys:

- `side_effect_ledger_dev_test_read`
- `side_effect_ledger_dev_test_write`
- `side_effect_ledger_dev_test_record_attempt`

All Phase 12B read/write/attempt permissions fail closed when missing,
disabled, invalid, or approval-only. No live-write permission key is added.

Phase 13A adds `synthesis_apply_runs` and `synthesis_apply_items` audit
tables plus a CLI-only apply path for reviewed synthesis previews. Approval
files must reference the exact `preview_id` and list approved candidates
explicitly by type and index. There is no approve-all default, no raw-prose
apply path, and no dashboard Apply button.

Phase 13A supported apply targets:

- priorities
- projects
- followups

Unsupported candidates such as routine changes, Todoist tasks, Calendar
blocks, clarity notes, review questions, PersonalOS Markdown notes, Gmail
messages, relationship messages, and high-stakes execution actions are
recorded at item level as skipped, unsupported, review-required, blocked, or
failed. They are not executed and are not converted into external write
intents.

Phase 13A permission keys:

- `synthesis_apply_dev_test_read`
- `synthesis_apply_dev_test_write`
- `synthesis_apply_dev_test_apply`

Apply requires the dev/test apply permission plus read/write permissions and
fails closed when they are missing, disabled, invalid, or approval-only. No
production apply permission and no live rail permission is added.

Phase 13B hardens synthesis apply atomicity and recovery. Internal core-state
inserts, apply run rows, apply item rows, and preview apply-status updates are
committed in one explicit SQLite transaction. If an in-transaction write fails,
the transaction rolls back and any recovery audit must verify that planned
core-state inserts did not persist. Phase 13B does not expand apply targets or
add live rails.

Phase 13C adds `scheduler_jobs` and `scheduler_runs` for no-send scheduler
simulation only. Scheduler jobs are database records, not active OS scheduler
configuration. The `enabled` flag means enabled for dev/test simulation only.
Running a job is synchronous, foreground, and manual through the CLI.

Allowed Phase 13C simulated job types:

- `status_summary`
- `today_view`
- `briefing_preview`
- `side_effect_summary`
- `synthesis_apply_summary`
- `dashboard_render_preview`

Every scheduler run completion report must expose `no_send_mode=true`,
`no_external_writes=true`, `fake_model_only=true`, `live_write=false`,
`external_mutation=false`, `scheduler_activation=false`, and
`launch_agent_installed=false`. Briefing preview runs use the existing fake
Composer no-send path only. Dashboard render preview writes only to an explicit
safe `--output-file`.

Phase 13C does not add Gmail send/draft, Todoist writes, Calendar writes,
PersonalOS Markdown writes, `.openclaw` integration, LaunchAgents, crontab,
daemons, background processes, live model/API calls, OpenAI/OpenRouter/
Anthropic integration, production DB activation, dashboard mutation controls,
public/LAN dashboard exposure, auth/login, Phase 14, or live-rail work.

Phase 13D adds checkpoint hardening only. It constrains project statuses to
`active`, `paused`, `completed`, and `archived`, and followup statuses to
`open`, `proposed`, `completed`, `archived`, and `blocked`. Synthesis import
and apply rerun those validations before any internal SQLite apply. The runtime
bootstrap known-permission registry lists newer module keys and seeds them
disabled by default, except the existing safe bootstrap read key. Dashboard and
Today View wording is read-only except explicit local synthesis preview record
creation; there is still no Apply button, no live rail, and no external write.

## Phase 1 Runtime Foundation

The Phase 1 runtime stabilization foundation adds repository-local Python tooling
and dev/test-only runtime primitives. The foundation currently includes:

- Python package and test scaffold.
- Secret-free sample config and dev/test environment defaults.
- Repo-local dev/test SQLite connection and migration helpers.
- Migration metadata, idempotent application, and checksum drift protection.
- Dev/test system event records.
- Fail-closed permission defaults.
- Dry-run/no-send validation results.
- Inert completion report serialization.

Phase 1 remains dev/test-only. It does not send email, write Todoist, write
Calendar, call OpenClaw, start schedulers, call external APIs, or access
production state.

## Phase 2 Dashboard-State Foundation

Phase 2 added a dev/test-only SQLite state foundation and read-model layer for
future dashboard work. It includes:

- Core state tables for `routines`, `routine_completions`, `priorities`,
  `projects`, `followups`, and `permission_settings`.
- State-store helpers for `permission_settings` get/list/upsert operations.
- Read-only list/count helpers for routines, priorities, projects, and
  followups.
- A local status summary read model with core counts, permission settings,
  recent system events, a generated UTC timestamp, and an optional environment
  label.

Phase 2 is not production-ready. It does not include a dashboard UI, API server,
scheduler, Gmail/Todoist/Calendar integration, OpenClaw wiring, LaunchAgents,
production SQLite access, credentials, external API clients, live runtime
behavior, public internet exposure, or a login/password system.

## Phase 3 Routine Engine Foundation

Phase 3 added a safe internal routine engine foundation on top of the Phase 2
tables. It includes:

- Routine data-access helpers for get/list/count/create and status/enabled
  updates.
- Routine validation for IDs, status values, enabled flags, completion dates,
  JSON-safe metadata, missing routines, disabled routines, and inactive
  routines.
- Routine completion helpers that write only to dev/test SQLite when explicitly
  allowed.
- Permission-gated routine-engine read and write paths backed by
  `permission_settings`.
- A dry-run-safe completion flow that validates intended work and reports what
  would be written without inserting a completion row.
- A non-dry-run dev/test completion flow that records a completion row only in
  the injected dev/test SQLite connection and returns an inert result dict.

Phase 3 routine completions are append-only dev/test records. They do not yet
enforce idempotency by `routine_id` plus `completed_for_date`, and this phase
does not add a database unique constraint. Scheduler and idempotency rules are
deferred to a future scheduler/runtime phase before any automated recurring
completion loop is activated.

Phase 3 permission keys:

- `routine_engine_dev_test_read`
- `routine_engine_dev_test_write`

Both keys fail closed when missing, disabled, invalid, or set to approval-only.
The routine engine allows work only when the relevant key is explicitly set to
`auto_write` in the dev/test database.

Phase 3 is not a scheduler, dashboard UI, API server, OpenClaw integration,
Todoist integration, Gmail integration, Calendar integration, LaunchAgent,
production SQLite path, credential path, external API client, notification
system, or live runtime activation.

## Phase 4 Priority Engine Foundation

Phase 4 added the priority registry foundation required by the PRD. It
includes:

- Priority data-access helpers for get/list/count/create, field updates, and
  status transitions.
- Priority validation for required IDs and titles, allowed status values,
  JSON-safe metadata, notes, and timezone-aware UTC timestamp inputs.
- Permission-gated priority-engine read and write paths backed by
  `permission_settings`.
- Dry-run-safe priority create, update, and status transition flows that return
  inert preview dictionaries and do not mutate SQLite.
- Non-dry-run dev/test flows that write only to the injected dev/test SQLite
  connection when the write permission is explicitly enabled.
- Deterministic read-model helpers for active priority summaries and counts by
  status.

Phase 4 permission keys:

- `priority_engine_dev_test_read`
- `priority_engine_dev_test_write`

Both keys fail closed when missing, disabled, invalid, or set to approval-only.
The priority engine allows work only when the relevant key is explicitly set to
`auto_write` in the dev/test database.

Phase 4 is not an autonomous prioritization system. It does not score, rank,
infer, generate, or schedule priorities from raw notes. It does not write
Todoist tasks, Calendar events, Gmail briefs, composer packets, OpenClaw
actions, LaunchAgents, production SQLite, credentials, or production state.
Scheduler behavior, idempotency/send ledger rules, Todoist/Calendar modules,
composer integration, and dashboard UI remain deferred to later phases.

## Phase 5 Todoist and Calendar Module Foundation

Phase 5 adds dev/test-only foundations for the Todoist action rail and Calendar
time-block rail. It includes:

- SQLite migration `0004_todoist_calendar_module_tables.sql` with
  `todoist_tasks` and `calendar_blocks` tables.
- Todoist task validation for required title/source/project fields, string
  labels, Todoist-like priority values 1 through 4, risk levels, approval
  modes, status values, and deterministic dedupe keys.
- Calendar block validation for required title/source/window/calendar fields,
  timezone-aware start/end times, positive duration, duration/window
  consistency, risk levels, approval modes, status values, and deterministic
  dedupe keys.
- Permission-gated read, dev/test write, and simulated-write wrappers backed
  by `permission_settings`.
- Preview flows that validate and return intended writes without mutating
  SQLite or calling adapters.
- Dev/test persistence flows that write only to the injected SQLite
  connection and never create external Todoist tasks or Calendar events.
- Fake recording clients for simulated Todoist and Calendar writes. Fake
  external IDs are deterministic and derived from dedupe keys.
- Module-level dedupe that returns an existing object instead of silently
  creating duplicate rows.

Phase 5 risk levels:

- `low`: routine/admin/self-only tasks or blocks.
- `medium`: self-only but sensitive, ambiguous, unusually time-consuming, or
  tied to a larger project.
- `high`: legal, tax, portfolio/crypto/investment execution, health/medical
  decisions, relationship messages, messages to other people, external
  meetings, family-sensitive events, or large financial commitments.

Phase 5 approval modes:

- `auto_allowed`: valid only for low-risk objects.
- `approval_required`: default for medium and high risk.
- `manual_only`: may be stored or previewed, but is not routed to a write
  client, including fake simulated clients.

Phase 5 permission keys:

- `todoist_module_dev_test_read`
- `todoist_module_dev_test_write`
- `todoist_module_dev_test_simulated_write`
- `calendar_module_dev_test_read`
- `calendar_module_dev_test_write`
- `calendar_module_dev_test_simulated_write`

All Phase 5 module permissions fail closed when missing, disabled, invalid, or
approval-only. They allow work only when the relevant dev/test key is
explicitly set to `auto_write`.

Phase 5 does not add live Todoist writes, live Calendar writes, credentials,
OAuth, scheduler activation, production SQLite access, Gmail integration,
composer/model integration, dashboard UI, LaunchAgents, OpenClaw wiring,
public internet exposure, external-user collaboration, autonomous
legal/tax/portfolio execution, or a scheduler idempotency/send ledger.

Any post-merge live smoke test is a separate OpenClaw-approved operation and
is not part of the Phase 5 PR.

## Phase 6 Composer Model Integration Foundation

Phase 6 adds a narrow Composer Packet to fake Composer adapter to structured
Composer Output to validation to candidate routing report layer. It includes:

- SQLite migration `0005_composer_model_tables.sql` with `composer_packets`,
  `composer_outputs`, and `model_runs` tables.
- Composer Packet schema `composer_packet.v1` with `packet_id`,
  `packet_type`, `briefing_window`, `source_date`, `timezone`,
  `generated_at`, narrow `inputs`, `omissions`, and `warnings`.
- Allowed packet inputs only: routine state, priority summaries, selected
  follow-up summaries, Todoist task summaries, Calendar block summaries,
  Calendar availability summary, today's schedule summary, WSP/routine rules,
  prior briefing summaries, and completion status.
- Forbidden packet/output inputs and claims include broad filesystem access,
  raw notes, the full vault, protected runtime paths, Gmail bodies, live
  Todoist or Calendar API data, legal/tax source documents, and secrets.
- Composer Output schema `composer_output.v1` requiring structured JSON plus
  non-empty readable text.
- Required output sections: `email_briefs`, `todoist_tasks`,
  `calendar_blocks`, `followups`, and `warnings`.
- A deterministic `FakeComposerAdapter` that never touches network,
  credentials, live model APIs, Todoist, Calendar, Gmail, OpenClaw, or
  production state.
- Candidate routing reports with `accepted_candidates`,
  `rejected_candidates`, `blocked_candidates`, `warnings`, and
  `no_external_writes: true`.
- Todoist and Calendar candidates routed through the Phase 5 preview
  validators only. Routing validates candidate shape and risk/approval
  semantics but does not execute writes.
- Model-run logging for fake dry runs with `model_role = composer_model`,
  `model_name = fake-composer-v1`, and
  `adapter_name = fake_composer_adapter`.

Phase 6 permission keys:

- `composer_module_dev_test_read`
- `composer_module_dev_test_write`
- `composer_module_dev_test_run`

All Phase 6 module permissions fail closed when missing, disabled, invalid, or
approval-only. They allow dev/test work only when the relevant key is
explicitly set to `auto_write`.

Phase 6 does not add live model/API calls, live Todoist writes, live Calendar
writes, Gmail send, credentials, OAuth, scheduler activation, LaunchAgents,
dashboard UI, OpenClaw runtime wiring, production SQLite access, broad
filesystem access, full PersonalOS vault access, raw journal ingestion,
legal/tax document ingestion, or autonomous high-stakes execution.

## Phase 7 Report Jobs and Weekly Chart Pack Foundation

Phase 7 adds the dev/test-only report job and Weekly Chart Pack storage
foundation. It includes:

- SQLite migration `0006_report_jobs_chart_pack_tables.sql` with
  `report_jobs`, `report_runs`, and `chart_pack_reviews` tables.
- Report job definitions for coded jobs such as weekly chart pack index,
  TradingView alert digest, macro calendar, earnings calendar, priority
  status report, routine adherence report, Todoist completion report, and
  Calendar utilization report.
- Report run records for preview, dry-run, and simulated local runs.
- A deterministic fake report runner that produces local-only structured
  output with `no_external_writes: true`.
- Chart pack review storage for manually supplied chart-pack data,
  manually supplied TradingView alert digests, and ChatGPT-provided synthesis.
- Structured summary validation for market context, BTC context, ETH context,
  miner/HPC context, portfolio watch items, week-over-week changes,
  follow-up candidates, and warnings.

ChatGPT is the interpretation layer for market and thesis synthesis. Chris
supplies chart packs and TradingView alerts to ChatGPT; OpenClaw may later run
approved workflows that store outputs, but OpenClaw does not analyze
investments independently. Phase 7 report jobs are coded jobs, not analyst
personas.

Phase 7 permission keys:

- `report_jobs_dev_test_read`
- `report_jobs_dev_test_write`
- `report_jobs_dev_test_run`
- `chart_pack_reviews_dev_test_read`
- `chart_pack_reviews_dev_test_write`

All Phase 7 module permissions fail closed when missing, disabled, invalid, or
approval-only. They allow dev/test work only when the relevant key is
explicitly set to `auto_write`.

Phase 7 does not add live market data fetching, TradingView API access,
investment recommendations, portfolio execution, Todoist writes, Calendar
writes, Gmail send, live model/API calls, credentials, OAuth, scheduler
activation, LaunchAgents, dashboard UI, OpenClaw runtime wiring, production
SQLite access, protected PersonalOS vault access, or unrestricted filesystem
access. Follow-up candidates are review/logging candidates only; they are not
execution tasks.

Local checks:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py"
```

Run the suite with `PYTHONPATH=src`; running without it can produce misleading
import failures that do not reflect the repo state. `pytest` is configured in
`pyproject.toml`, but it is not installed in the current local environment used
for this phase.

## Phase 8 Fitness Integration Foundation

Phase 8 adds a dev/test-only fitness integration state foundation. It includes:

- SQLite migration `0007_fitness_integration_tables.sql` with
  `fitness_integration_state`, `fitness_validation_runs`, and
  `fitness_file_contracts` tables.
- Expected local CSV tracker contracts for `workout_sessions.csv`,
  `workout_exercises.csv`, `weekly_recovery.csv`, and
  `exercise_library.csv`.
- Fixture-only CSV header validation. The validator checks caller-supplied
  fixture headers only and does not open live files.
- Deterministic validation reports with `no_external_writes: true` and
  `no_live_personalos_access: true`.
- Permission-gated dev/test read, write, and validate helpers backed by
  `permission_settings`.

Phase 8 permission keys:

- `fitness_integration_dev_test_read`
- `fitness_integration_dev_test_write`
- `fitness_integration_dev_test_validate`

All Phase 8 permissions fail closed when missing, disabled, invalid, or
approval-only. They allow dev/test work only when the relevant key is
explicitly set to `auto_write`.

The existing CSV-based local fitness tracker is preserved. There is no Notion
dependency. Phase 8 uses labels such as `personal_os_fitness_csvs` and expected
filenames instead of absolute live paths.

Phase 8 has no live PersonalOS CSV reads or writes, no Apple Health or wearable
API integration, no workout recommendation engine, no medical/health advice
engine, no Todoist/Calendar/Gmail writes, no live model/API calls, no
credentials or OAuth, no scheduler or LaunchAgents, no production
SQLite/runtime state, no dashboard UI yet, no full PersonalOS vault access,
and no unrestricted filesystem access. V1.5 may later add deeper
recovery/training context in briefings after separate approval.

## Phase 9B Runtime DB Bootstrap Foundation

Phase 9B adds a safe local/dev-preview runtime SQLite bootstrap foundation
before dashboard, briefing loop, scheduler, or live integrations. It includes:

- Runtime bootstrap profile validation for explicit `dev_runtime` and
  `local_runtime_preview` database paths.
- Protected path rejection for PersonalOS, OpenClaw, LaunchAgents,
  credential/OAuth-looking paths, and production-looking paths.
- A non-mutating bootstrap plan that reports target DB path, pending
  migrations, possible backup path, seed profile, and safety flags.
- Backup-before-migrate behavior for existing explicit temp/dev runtime DBs.
- Migration application through the existing checksum-tracked migration system.
- SQLite foreign key enforcement on bootstrap connections.
- Migration `0008_runtime_bootstrap_tables.sql` for `runtime_bootstrap_runs`
  and inert `briefing_windows`.
- A safe MVP preview seed profile that writes only local SQLite state:
  disabled external/live-facing permissions, paused disabled preview routines,
  a fake paused preview priority, and no-send draft briefing window
  definitions.
- A structured runtime bootstrap/status report with migration state, table
  counts, permission summary, seeded objects, backup status, and safety flags.

Phase 9B permission keys:

- `runtime_bootstrap_dev_test_read`
- `runtime_bootstrap_dev_test_write`
- `runtime_bootstrap_dev_test_run`

All Phase 9B runtime bootstrap permissions fail closed when missing, disabled,
invalid, or approval-only. Bootstrap writes and seed behavior require explicit
dev/test write and run permissions. No production runtime permission and no
live external write permission is added.

Phase 9B does not add live Todoist writes, live Calendar writes, Gmail send,
live model/API calls, Notion, Apple Health, TradingView/API calls,
credentials/OAuth, scheduler/LaunchAgents, dashboard UI, web server, daily
briefing generation loop, production SQLite/runtime state mutation, protected
PersonalOS or OpenClaw access, or real production activation. The likely next
phase is a minimal local Today View/dashboard shell or a no-send daily
briefing loop, after separate approval.

## Phase 10A Local Dashboard Today View Foundation

Phase 10A adds the first minimal read-only local dashboard shell and Today View
read model. It includes:

- `src/personalos/today.py`, a pure read model that accepts an existing
  SQLite connection plus source date/timezone parameters and returns routines,
  priorities, follow-ups, Todoist candidate counts, Calendar block counts,
  briefing windows, permissions, system/runtime status, warnings, and
  `no_external_writes: true`.
- `src/personalos/dashboard.py`, a standard-library local HTTP shell with pure
  render helpers for `Personal OS Today View` HTML and JSON.
- Localhost-only bind validation by default. Phase 10A rejects `0.0.0.0` and
  non-local bind hosts.
- Dashboard DB path validation that allows only explicit temp or repo-local
  dev SQLite paths and rejects protected, credential/OAuth-looking, and
  production-looking paths.

Phase 10A adds no new permission keys. It relies on existing read-only state
helpers and direct SQLite reads from caller-supplied connections or read-only
SQLite connections for dashboard rendering.

Phase 10A does not add live Todoist writes, live Calendar writes, Gmail send,
live model/API calls, Notion, Apple Health, TradingView/API calls,
credentials/OAuth, scheduler/LaunchAgents, public internet exposure, login/auth,
task/calendar mutation from dashboard, routine editor, priority editor,
synthesis import, no-send daily briefing generation loop, production
SQLite/runtime state mutation, protected PersonalOS or OpenClaw access, or
production runtime activation. The likely next phase is a no-send daily
briefing loop or a dashboard editor/import flow, after separate approval.

## Phase 10B No-Send Daily Briefing Loop Foundation

Phase 10B adds the first no-send daily briefing loop foundation on top of
runtime bootstrap, briefing windows, Composer packets/outputs, and Today View.
It includes:

- SQLite migration `0009_briefing_loop_tables.sql` with `daily_plans` and
  `briefing_outputs`.
- Daily plan generation from existing runtime state, Today View summaries,
  active/draft briefing windows, routine summaries, priority summaries,
  follow-up summaries, warnings, `no_external_writes: true`, and
  `no_send_mode: true`.
- Briefing window lookup for `morning`, `midday`, `afternoon`, and `evening`
  definitions in the existing inert `briefing_windows` table.
- No-send briefing preview generation through the fake Composer path only.
- Local persistence of the daily plan, Composer packet/output/model-run
  records, and briefing output records.
- Manual export only markdown suitable for later copy/paste outside this
  phase.
- Completion report records with no-send and no-external-write flags, including
  no live model calls, no Todoist writes, no Calendar writes, and no Gmail
  sending.
- Read-only Today View summary fields for briefing output counts, briefing
  window status, and no-send mode.

Phase 10B permission keys:

- `briefing_loop_dev_test_read`
- `briefing_loop_dev_test_write`
- `briefing_loop_dev_test_run`

All Phase 10B briefing loop permissions fail closed when missing, disabled,
invalid, or approval-only. Read/list/count helpers require the read key.
Generating and storing a no-send briefing preview requires the write and run
keys. No live/send permission is added.

Phase 10B does not add Gmail sending, Gmail drafts, live Todoist writes, live
Calendar writes, live model calls, OpenAI/OpenRouter/Anthropic calls,
credentials/OAuth, scheduler/LaunchAgents, public internet exposure,
dashboard mutation, routine/priority editors, synthesis import, real model
routing, production SQLite/runtime state mutation, protected PersonalOS or
OpenClaw access, or external writes of any kind.

## Phase 10C Dashboard Briefing Integration

Phase 10C dashboard briefing integration makes Phase 10B no-send briefing
outputs visible in the read-only Today View and local dashboard shell. It adds:

- A Today View `briefing_output_summary` over existing `daily_plans` and
  `briefing_outputs`.
- A dashboard Briefing Outputs section with latest window/name/status details.
- A read-only latest manual export preview or excerpt.
- Completion report safety flags, including `no_external_writes`,
  `no_send_mode`, `no_live_model_call`, `no_todoist_writes`,
  `no_calendar_writes`, and `no_gmail_send`.
- Failed briefing and warning status.
- JSON output through the existing `/today.json` read-only render path.

The manual export preview is read-only. Phase 10C has no generation button, no
dashboard mutation, no scheduler, no Gmail/model/Todoist/Calendar writes, no
Gmail drafts, no live model/API calls, no credentials/OAuth, no
LaunchAgents, no production SQLite/runtime activation, no protected PersonalOS
or OpenClaw access, no public internet exposure, no routine or priority
editor, and no synthesis import.

The Phase 10B manual exports are fake/local no-send content. Future
real-content redaction or review may be needed before broader network exposure
or any non-local dashboard access is considered.
Future real-content redaction may be needed before broader network exposure.

Likely next phases after Phase 10C are ChatGPT synthesis import preview or
controlled manual live rail testing after ledgers and separate approval.

## Phase 11A ChatGPT Synthesis Import Preview Foundation

Phase 11A adds a safe intake layer for ChatGPT-synthesized material. It is not
raw-note ingestion and not an apply/save flow. It includes:

- SQLite migration `00010_synthesis_import_preview_tables.sql` with
  `synthesis_import_previews`.
- Parser support for canonical JSON, Markdown containing one fenced JSON
  block, and a small structured Markdown heading/bullet subset.
- Accepted source types: `chatgpt_synthesis`, `manual_structured_import`, and
  `fake_fixture`.
- Rejected source types: `raw_notes`, `raw_journal`, `full_vault_dump`,
  `legal_source_documents`, `tax_source_documents`, `credential_dump`, and
  `unrestricted_file_input`.
- Canonical schema `synthesis_import.v1` with summary, warnings, and candidate
  lists for priorities, projects, follow-ups, routine changes, Todoist tasks,
  Calendar blocks, clarity notes, and review questions.
- Todoist and Calendar candidates routed through the existing Phase 5 preview
  validators only.
- Deterministic high-stakes checks for tax, legal, estate, portfolio, crypto,
  investments, health, medical, relationship messages, family-sensitive
  communication, and large financial commitments.
- Preview reports with candidate counts, accepted/rejected/blocked/review
  required/manual-only lists, review questions, warnings, and explicit safety
  flags.

Phase 11A permission keys:

- `synthesis_import_dev_test_read`
- `synthesis_import_dev_test_write`
- `synthesis_import_dev_test_preview`

All Phase 11A permissions fail closed when missing, disabled, invalid, or
approval-only. Parsing and preview report generation can be pure. Persisting a
preview record requires both write and preview permissions. Reading, listing,
or counting preview records requires the read permission.

Phase 11A does not add raw journal ingestion, automatic task creation from raw
notes, applying/saving candidates into priorities/routines/follow-ups,
PersonalOS Markdown writes, Todoist writes, Calendar writes, Gmail send or
draft, live model/API calls, OpenAI/OpenRouter/Anthropic calls, scheduler or
LaunchAgents, production runtime activation, `.openclaw` access, full
PersonalOS vault access, dashboard mutation/edit forms, paste box UI, public
internet exposure, credentials/OAuth, or live external writes of any kind.

Likely Phase 11B options are either a dashboard paste/import preview UI or an
apply/save flow with explicit approval gates.

## Phase 11B Dashboard Synthesis Import Preview UI

Phase 11B adds a local dashboard paste/import form for structured ChatGPT
synthesis. The dashboard shows a `ChatGPT Synthesis Import Preview` section
with a preview-only safety banner, a structured synthesis textarea,
`source_type`, optional `source_reference`, optional `source_timestamp`, and a
single `Preview import` button.

The form posts to `/synthesis-import/preview` and uses the existing Phase 11A
preview engine. Persisted preview submission requires
`synthesis_import_dev_test_write` and
`synthesis_import_dev_test_preview`; prior-preview summaries require
`synthesis_import_dev_test_read`. Only `synthesis_import_previews` may be
written. There is no apply permission and no apply/save route.

The dashboard renders the preview report with `preview_id`, `source_type`,
`input_format`, candidate counts, accepted/rejected/blocked/review-required/
manual-only candidate buckets, warnings, questions for review, and safety
flags for no external writes, no state mutation, no PersonalOS writes, no
Todoist writes, no Calendar writes, no Gmail send, and no live model call.
Untrusted content is HTML-escaped, and raw input is shown only as the bounded
Phase 11A `raw_excerpt`.

Phase 11B expects ChatGPT-synthesized structured input, not raw notes. It
continues to reject unsupported prose, raw notes, credential/protected-looking
input, and unsafe high-stakes low/auto candidates through the Phase 11A gates.
The dashboard bind boundary remains localhost-only by default; public or LAN
bind relaxation, auth/login, scheduler activation, production runtime use,
PersonalOS Markdown writes, Todoist/Calendar/Gmail writes, live model/API
calls, credentials/OAuth, and live external writes remain non-goals.

Likely next phase:

- Phase 11C explicit apply/save flow with approval gates, or a no-send
  operator CLI, depending on MVP priority.
