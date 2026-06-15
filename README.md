# Personal OS

Personal OS is a modular, local-first productivity, routine, priority, and execution operating system. It helps Chris think clearly, maintain routines, manage high-value priorities, generate briefings, create Todoist tasks, schedule Calendar blocks, preserve durable notes, and run reports through OpenClaw on the Mac Mini.

This repository is the private code source of truth for Personal OS. It is documentation-first right now: no live workflow scripts, runtime mutations, or production integrations are enabled from this repo yet.

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

Phases -1 through 8 are complete. The Phase 6B, Phase 7B, and Phase 8B
fake/local smoke tests are complete.

The current next phase is correctness hardening and MVP readiness, not another
domain module. This repository still has no production runtime activation: no
dashboard UI, scheduler, Gmail send, live Todoist or Calendar writes, live
model/API calls, credentials/OAuth, production SQLite/runtime state access,
protected PersonalOS path access, or unrestricted filesystem access is enabled
from this repo.

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
PYTHONPATH=src python3 -m unittest discover -s tests
```

`pytest` is configured in `pyproject.toml`, but it is not installed in the
current local environment used for this phase.

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
