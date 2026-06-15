# Roadmap

Phases -1 through 10A are complete. The Phase 6B, Phase 7B, and Phase 8B
fake/local smoke tests are complete. The current Phase 10B work is a no-send
daily briefing loop foundation for local/manual previews only. This repo still
has no production runtime activation.

## Phase -1: Codex Setup and Repo Foundation

Status: complete.

Scope:

- Create the initial private repo scaffold.
- Add README and core docs.
- Establish the safety boundary.
- Add inert placeholders for future modules.

Exit criteria:

- Scaffold committed at `04d51891c2778971f7657eda6076a8cd80b11129`.
- No live-system inventory performed.
- No production state inspected or mutated.

## Phase 0: Read-Only Inventory

Status: complete.

Note: any future inventory of protected live paths remains a separate explicit
approval gate. Completion of the repo-local roadmap phases does not grant
permission to inspect protected runtime paths.

Scope:

- Inventory approved local project surfaces.
- Map existing repo, state, and runtime boundaries.
- Produce evidence-backed notes.
- Keep all interactions read-only.

Gate:

- Requires explicit approval before starting.
- Read-only only.
- May inspect specified live paths only after explicit approval for that inventory scope.

Proposed read-only paths:

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

Required outputs:

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

## Phase 1: Runtime Stabilization

Status: complete.

Scope:

- Define safe runtime boundaries.
- Confirm OpenClaw operator responsibilities.
- Establish logs and system event conventions.
- Prepare non-mutating checks around runtime readiness.
- Build no-send scheduler and email infrastructure only; no Gmail access or send behavior.

## Phase 2: Dashboard and State Store

Status: complete.

Scope:

- Build the local dashboard shell.
- Add Today View, Settings/Permissions, System Status/Logs, and module navigation.
- Define and migrate SQLite runtime state.
- Keep the dashboard local-network only with no public internet exposure.
- Keep no login or password for V1 by choice, while documenting local-network risks and future options such as password, device allowlist, Tailscale/VPN, or local-only binding.
- Keep dev/test SQLite files repo-local; require backup before any future production migration.

Current foundation:

- Dev/test-only SQLite tables exist for routines, routine_completions,
  priorities, projects, followups, and permission_settings.
- State-store helpers support permission_settings get/list/upsert operations.
- Read-only list/count helpers exist for routines, priorities, projects, and
  followups.
- A status summary read model exposes core counts, permission settings, recent
  system events, a generated UTC timestamp, and an optional environment label.

Current non-goals:

- No dashboard UI or API server yet.
- No scheduler, live runtime behavior, production SQLite, credentials,
  LaunchAgents, OpenClaw wiring, external API clients, or public internet
  exposure.
- No Gmail, Todoist, or Calendar integration.
- No login/password system.

## Phase 3: Routine Engine

Status: complete.

Scope:

- Build the dev/test-only routine engine foundation on top of the Phase 2
  SQLite tables.
- Add routine helpers for get/list/count/create and status/enabled updates.
- Add routine completion helpers that validate the referenced routine and write
  only to injected dev/test SQLite connections.
- Validate routine status values, enabled flags, completion input shape,
  missing routines, disabled routines, and inactive routines.
- Gate routine-engine read and write paths through explicit
  `permission_settings` keys:
  `routine_engine_dev_test_read` and `routine_engine_dev_test_write`.
- Support a dry-run completion flow that checks permissions and reports the
  intended completion without writing a row.
- Support a non-dry-run dev/test completion flow that writes only a
  `routine_completions` row and returns an inert result.
- Prove through unit tests that missing/disabled permissions deny action and
  enabled dev/test permissions allow the intended routine operations.

Non-goals:

- No scheduler.
- No recurring automation activation.
- No default routine seeding.
- No routine editor UI.
- No dashboard UI or API server.
- No OpenClaw runtime wiring.
- No Gmail, Todoist, or Calendar integration.
- No LaunchAgents, production SQLite, credentials, external API clients,
  public internet exposure, notifications, task creation, email sending, or
  calendar writes.

## Phase 4: Priority Engine

Status: complete.

Scope:

- Build the dev/test-only priority registry foundation on top of the Phase 2
  SQLite `priorities` table.
- Add priority helpers for get/list/count/create, field updates, and status
  transitions.
- Validate priority IDs, titles, allowed status values, JSON-safe metadata,
  notes, and timezone-aware timestamp inputs.
- Gate priority-engine read and write paths through explicit
  `permission_settings` keys:
  `priority_engine_dev_test_read` and `priority_engine_dev_test_write`.
- Support dry-run priority creation, update, and status transition flows that
  report intended writes without mutating SQLite.
- Support non-dry-run dev/test priority writes only when the write permission is
  explicitly enabled.
- Add deterministic read models for active priorities, counts by status, and a
  small priority dashboard summary shape.

Non-goals:

- No autonomous prioritization, semantic scoring, ranking, inference from raw
  notes, or automatic task generation.
- No project/follow-up lifecycle expansion beyond existing Phase 2 tables.
- No ChatGPT synthesis imports or composer integration.
- No dashboard UI or API server.
- No scheduler behavior, recurring automation activation, idempotency/send
  ledger, or runtime wiring.
- No Todoist, Calendar, Gmail, OpenClaw, LaunchAgent, production SQLite,
  credential, external API client, public internet, task creation, email
  sending, or calendar write behavior.

## Phase 5: Todoist and Calendar Modules

Status: complete.

Scope:

- Add dev/test SQLite tables for Todoist task proposals and Calendar block
  proposals.
- Add validation for required fields, risk levels, approval modes, status
  values, Todoist-like priority values, labels, Calendar start/end windows, and
  Calendar duration consistency.
- Add deterministic module-level dedupe keys and prevent silent duplicate
  creates.
- Add permission-gated read, dev/test write, and simulated-write wrappers.
- Add dry-run preview flows that do not mutate SQLite or call adapters.
- Add fake recording Todoist and Calendar clients for deterministic simulated
  write reports.
- Keep high-risk actions, messages to other people, external meetings,
  family-sensitive events, legal/tax/portfolio execution, and large financial
  commitments behind approval or manual-only paths.

Risk and approval semantics:

- `low`: routine/admin/self-only tasks or blocks.
- `medium`: self-only but sensitive, ambiguous, unusually time-consuming, or
  tied to a larger project.
- `high`: legal, tax, portfolio/crypto/investment execution, health/medical
  decisions, relationship messages, messages to other people, external
  meetings, family-sensitive events, or large financial commitments.
- `auto_allowed` is valid only with `low`.
- `medium` defaults to `approval_required`.
- `high` must be `approval_required` or `manual_only`.
- `manual_only` may be stored or previewed but must not be routed to a write
  client.

Permission keys:

- `todoist_module_dev_test_read`
- `todoist_module_dev_test_write`
- `todoist_module_dev_test_simulated_write`
- `calendar_module_dev_test_read`
- `calendar_module_dev_test_write`
- `calendar_module_dev_test_simulated_write`

Non-goals:

- No live Todoist writes.
- No live Calendar writes.
- No credentials or OAuth.
- No scheduler activation.
- No production SQLite access.
- No Gmail integration.
- No composer/model integration.
- No dashboard UI or API server.
- No LaunchAgents or OpenClaw runtime wiring.
- No public internet exposure or external-user collaboration.
- No autonomous legal, tax, portfolio, crypto, investment, health, medical, or
  relationship-message execution.
- No broader scheduler idempotency/send ledger in Phase 5.
- Post-merge live smoke testing is a separate OpenClaw-approved operation, not
  part of this PR.

## Phase 6: Composer Model Integration

Status: complete.

Scope:

- Add dev/test SQLite tables for `composer_packets`, `composer_outputs`, and
  `model_runs`.
- Define Composer Packet generation from narrow dev/test state summaries.
- Allow only routine state, priority summaries, selected follow-up summaries,
  Todoist task summaries, Calendar block summaries, Calendar availability
  summary, today's schedule summary, WSP/routine rules, prior briefing
  summaries, and completion status into packets.
- Reject packet or output content that claims broad filesystem access, raw
  notes, full vault access, protected runtime paths, Gmail bodies, live
  Todoist or Calendar API data, legal/tax source documents, or secrets.
- Use a deterministic fake Composer adapter only; no live model/API calls.
- Require Composer Output structured JSON plus non-empty readable text.
- Enforce output sections for `email_briefs`, `todoist_tasks`,
  `calendar_blocks`, `followups`, and `warnings`.
- Route valid Todoist and Calendar candidates through the Phase 5 preview
  validators and produce a structured candidate routing report with
  `no_external_writes: true`.
- Log fake dry-run model metadata in `model_runs`.
- Gate read, write, and fake-run/routing paths with
  `composer_module_dev_test_read`, `composer_module_dev_test_write`, and
  `composer_module_dev_test_run`.

Non-goals:

- No live model/API calls.
- No live Todoist writes.
- No live Calendar writes.
- No Gmail send.
- No credentials or OAuth.
- No scheduler activation.
- No production SQLite access.
- No dashboard UI or API server.
- No LaunchAgents or OpenClaw runtime wiring.
- No full PersonalOS vault access, raw journal ingestion, legal/tax document
  ingestion, arbitrary filesystem access, or autonomous high-stakes execution.

## Phase 7: Weekly Chart Pack and Report Jobs

Status: complete.

Scope:

- Add dev/test SQLite tables for `report_jobs`, `report_runs`, and
  `chart_pack_reviews`.
- Add report job validation for supported coded job types, cadence, status,
  JSON-safe config, and timestamps.
- Add report run validation for preview, dry-run, and simulated local runs.
- Add chart pack review validation for manually supplied chart-pack data,
  manually supplied TradingView alert digests, ChatGPT synthesis markdown, and
  structured summaries.
- Enforce structured summary sections for market context, BTC context, ETH
  context, miner/HPC context, portfolio watch items, week-over-week changes,
  follow-up candidates, and warnings.
- Add a deterministic fake report runner that writes local `report_runs`
  records only when dev/test permissions are enabled and returns
  `no_external_writes: true`.
- Track week-over-week chart review changes as stored review data, not as
  autonomous investment interpretation.
- Support jobs such as weekly chart pack index, TradingView alert digest,
  macro calendar, earnings calendar, priority status report, routine
  adherence report, Todoist completion report, and Calendar utilization
  report.

Workflow boundary:

- Chris produces Weekly Chart Packs and gathers TradingView alerts.
- TradingView alerts are manually supplied and stored as validated JSON; they
  are not fetched live.
- Chris sends chart packs and alerts to ChatGPT.
- ChatGPT is the interpretation layer for market and thesis synthesis.
- OpenClaw may later store approved workflow outputs and track changes, but
  OpenClaw does not analyze investments independently.
- Report jobs are coded jobs, not analyst personas.

Permission keys:

- `report_jobs_dev_test_read`
- `report_jobs_dev_test_write`
- `report_jobs_dev_test_run`
- `chart_pack_reviews_dev_test_read`
- `chart_pack_reviews_dev_test_write`

Non-goals:

- No live market data fetching.
- No TradingView API.
- No investment recommendations.
- No portfolio execution.
- No Todoist writes.
- No Calendar writes.
- No Gmail send.
- No live model/API calls.
- No credentials or OAuth.
- No scheduler or LaunchAgents.
- No production SQLite access.
- No dashboard UI.
- No protected PersonalOS vault access or unrestricted filesystem access.

## Phase 8: Fitness Integration

Status: complete.

Scope:

- Add the Phase 8 Fitness Integration Foundation as a dev/test-only
  contract/status shell.
- Preserve the existing CSV-based local fitness tracker. The existing
  CSV-based local fitness tracker is preserved and not rebuilt or migrated.
- Add SQLite tables for `fitness_integration_state`,
  `fitness_validation_runs`, and `fitness_file_contracts`.
- Define expected CSV contracts for `workout_sessions.csv`,
  `workout_exercises.csv`, `weekly_recovery.csv`, and
  `exercise_library.csv`.
- Add fixture-only CSV header validation from caller-supplied test data.
- Return deterministic validation reports with `no_external_writes: true` and
  `no_live_personalos_access: true`.
- Add permission-gated dev/test read, write, and validate helpers.
- Later V1.5 may integrate routine prompts and recovery/training state in
  briefings after separate approval.

Permission keys:

- `fitness_integration_dev_test_read`
- `fitness_integration_dev_test_write`
- `fitness_integration_dev_test_validate`

Non-goals:

- No Notion dependency.
- No live PersonalOS CSV reads or writes.
- No Apple Health or wearable API integration.
- No live fitness data import.
- No workout recommendation engine.
- No medical/health advice engine.
- No Todoist/Calendar/Gmail writes.
- No live model/API calls.
- No credentials or OAuth.
- No scheduler or LaunchAgents.
- No production SQLite/runtime state.
- No dashboard UI yet.
- No full PersonalOS vault access or unrestricted filesystem access.

## Phase 9A: Correctness Hardening and MVP Readiness

Status: complete.

Scope:

- Enforce SQLite foreign key constraints on dev/test connections.
- Harden fake Composer run status consistency and timezone handling.
- Normalize Calendar block datetime filtering across timezone offsets.
- Clean up roadmap/status docs before MVP integration work.

Non-goals:

- No new domain module.
- No dashboard UI.
- No scheduler or LaunchAgents.
- No Gmail send.
- No live Todoist writes.
- No live Calendar writes.
- No live model/API calls.
- No Notion, Apple Health, TradingView, or other live API calls.
- No credentials or OAuth.
- No production SQLite/runtime state.
- No PersonalOS or `.openclaw` access.

## Phase 9B: Runtime DB Bootstrap Foundation

Status: complete.

Scope:

- Add a safe runtime bootstrap profile for explicit local/dev-preview SQLite
  paths only.
- Keep `runtime_mode` limited to `dev_runtime` and `local_runtime_preview`.
- Require `no_external_writes: true` and `no_send_mode: true`.
- Reject protected PersonalOS, OpenClaw, LaunchAgents, credential/OAuth-looking,
  and production-looking paths.
- Add non-mutating bootstrap previews that report the target DB path, pending
  migrations, possible backup path, seed profile, and safety flags.
- Create timestamped backups before migrating an existing explicit temp/dev DB.
- Apply migrations through the existing checksum-tracked migration system and
  keep SQLite foreign key enforcement enabled.
- Add `runtime_bootstrap_runs` and inert `briefing_windows` tables.
- Seed only safe local SQLite state: disabled external/live-facing permissions,
  paused disabled preview routines, a fake paused preview priority, and no-send
  draft briefing window definitions.
- Return a local runtime bootstrap/status report with migrations, table counts,
  permission summary, seeded objects, backup status, and safety flags.

Permission keys:

- `runtime_bootstrap_dev_test_read`
- `runtime_bootstrap_dev_test_write`
- `runtime_bootstrap_dev_test_run`

Non-goals:

- No live Todoist writes.
- No live Calendar writes.
- No Gmail send.
- No live model/API calls.
- No Notion, Apple Health, TradingView, or other live API calls.
- No credentials or OAuth.
- No scheduler or LaunchAgents.
- No production SQLite/runtime state mutation.
- No protected PersonalOS or `.openclaw` access.
- No dashboard UI or web server.
- No daily briefing generation loop.
- No production runtime activation.

## Phase 10A: Local Dashboard Today View Foundation

Status: complete.

Scope:

- Add a read-only Today View summary builder on top of existing runtime state.
- Accept a caller-supplied SQLite connection plus source date/timezone
  parameters.
- Include routines, priorities, follow-ups, Todoist candidate counts, Calendar
  block counts, briefing windows, permissions, system/runtime status, warnings,
  and `no_external_writes: true`.
- Add a minimal standard-library read-only dashboard shell for `Personal OS
  Today View`.
- Keep the dashboard localhost-only by default and reject public bind hosts.
- Validate dashboard DB paths so only explicit temp or repo-local dev SQLite
  files are eligible, while protected, credential/OAuth-looking, and
  production-looking paths are rejected.
- Provide pure render helpers that can be tested without starting a long-running
  server.

Permission keys:

- No new Phase 10A permission keys.

Non-goals:

- No live Todoist writes.
- No live Calendar writes.
- No Gmail send.
- No live model/API calls.
- No Notion, Apple Health, TradingView, or other live API calls.
- No credentials or OAuth.
- No scheduler or LaunchAgents.
- No production SQLite/runtime state mutation.
- No protected PersonalOS or `.openclaw` access.
- No public internet exposure.
- No login/auth.
- No task/calendar mutation from dashboard.
- No routine editor.
- No priority editor.
- No synthesis import.
- No no-send daily briefing generation loop.
- No production runtime activation.

Likely next phase:

- No-send daily briefing loop or dashboard editor/import flow, after separate
  approval.

## Phase 10B: No-Send Daily Briefing Loop Foundation

Status: complete.

Scope:

- Add dev/test SQLite tables for `daily_plans` and `briefing_outputs`.
- Build a no-send daily plan from Today View summaries, active/draft briefing
  windows, routine summaries, priority summaries, follow-up summaries,
  warnings, and explicit no-send/no-external-write flags.
- Select an inert briefing window by source date, timezone, and window name:
  `morning`, `midday`, `afternoon`, or `evening`.
- Generate local/manual briefing previews through the fake Composer path only.
- Persist the daily plan, Composer packet/output/model-run records, and
  briefing output record in the caller-supplied local SQLite DB.
- Produce readable text, manual export only markdown, and a structured
  completion report for each preview.
- Add read-only Today View fields for latest briefing output counts, briefing
  window status, and no-send mode.

Permission keys:

- `briefing_loop_dev_test_read`
- `briefing_loop_dev_test_write`
- `briefing_loop_dev_test_run`

Permission behavior:

- Missing, disabled, invalid, or approval-only permissions fail closed.
- Read/list/count helpers require `briefing_loop_dev_test_read`.
- Generating and storing a no-send preview requires
  `briefing_loop_dev_test_write` and `briefing_loop_dev_test_run`.
- Phase 10B adds no live/send permission.

Non-goals:

- No Gmail sending.
- No Gmail drafts.
- No live Todoist writes.
- No live Calendar writes.
- No Todoist/Calendar writes.
- No live model calls.
- No OpenAI/OpenRouter/Anthropic calls.
- No credentials or OAuth.
- No scheduler or LaunchAgents.
- No production SQLite/runtime state mutation.
- No protected PersonalOS or `.openclaw` access.
- No public internet exposure.
- No dashboard mutation.
- No routine editor.
- No priority editor.
- No synthesis import.
- No real model routing.
- No external writes of any kind.

## Phase 10C: Dashboard Briefing Integration

Status: current.

Scope:

- Add a read-only Today View `briefing_output_summary` over existing
  `daily_plans` and `briefing_outputs`.
- Show a dashboard Briefing Outputs section with latest briefing
  window/name/status, delivery mode, created timestamp, counts, warning counts,
  and failed briefing count.
- Show the latest manual export preview or excerpt as read-only dashboard
  content.
- Show completion report safety flags:
  `no_external_writes`, `no_send_mode`, `no_live_model_call`,
  `no_todoist_writes`, `no_calendar_writes`, and `no_gmail_send`.
- Include the same briefing output summary in the existing `/today.json`
  render path.
- Preserve localhost/read-only dashboard behavior.

Permission keys:

- No new Phase 10C permission keys.

Non-goals:

- No generation button.
- No Gmail sending.
- No Gmail drafts.
- No live Todoist writes.
- No live Calendar writes.
- No Gmail/model/Todoist/Calendar writes.
- No live model calls.
- No OpenAI/OpenRouter/Anthropic calls.
- No credentials or OAuth.
- No scheduler or LaunchAgents.
- No production SQLite/runtime state mutation.
- No protected PersonalOS or `.openclaw` access.
- No public internet exposure.
- No dashboard mutation.
- No routine editor.
- No priority editor.
- No synthesis import.
- No external writes of any kind.

Notes:

- Phase 10B manual exports are local fake/no-send content. Future
  real-content redaction or review may be needed before broader network
  exposure or any non-local dashboard access is considered.

Likely next phase:

- ChatGPT synthesis import preview or controlled manual live rail testing
  after ledgers and separate approval.
