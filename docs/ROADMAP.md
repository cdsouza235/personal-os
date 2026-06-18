# Roadmap

Phases -1 through 13F-D plus Phase 13E-A and Phase 13E-B are complete. The
Phase 6B, Phase 7B, Phase 8B, Phase 12A, and Phase 12B fake/local smoke tests
are complete. The current Phase 13E-C work is dashboard safe-action/status
polish. This repo still has no production runtime activation.

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

Status: complete.

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

## Phase 11A: ChatGPT Synthesis Import Preview

Status: complete.

Scope:

- Add `synthesis_import_previews` as a local preview-record table through
  migration `00010_synthesis_import_preview_tables.sql`.
- Add deterministic parsing for canonical JSON, Markdown with one fenced JSON
  block, and a documented structured Markdown heading/bullet subset.
- Accept only `chatgpt_synthesis`, `manual_structured_import`, and
  `fake_fixture` as import source types.
- Reject `raw_notes`, `raw_journal`, `full_vault_dump`,
  `legal_source_documents`, `tax_source_documents`, `credential_dump`, and
  `unrestricted_file_input`.
- Normalize imports to `synthesis_import.v1` with summary, warnings, and
  candidate lists for priorities, projects, follow-ups, routine changes,
  Todoist tasks, Calendar blocks, clarity notes, and review questions.
- Route Todoist and Calendar candidates through the existing Phase 5 preview
  validators without creating rows or calling adapters.
- Classify high-stakes domains deterministically: tax, legal, estate,
  portfolio, crypto, investments, health, medical, relationship messages,
  family-sensitive communication, and large financial commitments.
- Produce preview reports with candidate counts, accepted candidates, rejected
  candidates, blocked candidates, review-required candidates, manual-only
  candidates, warnings, questions for review, and explicit no-write/no-model
  safety flags.

Permission keys:

- `synthesis_import_dev_test_read`
- `synthesis_import_dev_test_write`
- `synthesis_import_dev_test_preview`

Permission behavior:

- Missing, disabled, invalid, or approval-only permissions fail closed.
- Pure parsing and preview report generation do not require persistence.
- Persisted preview creation requires both
  `synthesis_import_dev_test_write` and
  `synthesis_import_dev_test_preview`.
- Read/list/count helpers require `synthesis_import_dev_test_read`.
- No apply permission and no live permission exist in Phase 11A.

Non-goals:

- No raw journal ingestion as tasks.
- No automatic task creation from raw notes.
- No applying/saving candidates into priorities, routines, or follow-ups.
- No PersonalOS Markdown writes.
- No Todoist writes.
- No Calendar writes.
- No Gmail send or draft.
- No live model/API calls.
- No OpenAI/OpenRouter/Anthropic calls.
- No scheduler or LaunchAgents.
- No production runtime activation.
- No `.openclaw` access.
- No full PersonalOS vault access.
- No dashboard mutation/edit forms.
- No paste box UI.
- No public internet exposure.
- No credentials or OAuth.
- No live external writes of any kind.

## Phase 11B: Dashboard Synthesis Import Preview UI

Status: complete.

Scope:

- Add a local dashboard `ChatGPT Synthesis Import Preview` section.
- Show a preview-only safety banner with no core state mutation, no PersonalOS
  Markdown writes, no Todoist/Calendar/Gmail writes, and no live model/API
  calls.
- Provide a structured synthesis textarea, `source_type`, optional
  `source_reference`, optional `source_timestamp`, and one `Preview import`
  submit button.
- Add `GET /synthesis-import` and `POST /synthesis-import/preview` routes on
  the existing localhost-only dashboard server.
- Route form-encoded submissions through the existing Phase 11A synthesis
  import preview engine.
- Persist only `synthesis_import_previews` records when
  `synthesis_import_dev_test_write` and
  `synthesis_import_dev_test_preview` are enabled.
- Keep prior-preview counts and latest-preview summary read-gated by
  `synthesis_import_dev_test_read`.
- Render preview reports with `preview_id`, `source_type`, `input_format`,
  candidate counts, accepted candidates, rejected candidates, blocked
  candidates, review-required candidates, manual-only candidates, warnings,
  questions for review, and no-write/no-model safety flags.
- Escape HTML output and show only the bounded Phase 11A `raw_excerpt`.
- Add a small Today View summary for preview count, latest preview timestamp
  and status, latest blocked/rejected counts, and latest warnings count.

Permission keys:

- `synthesis_import_dev_test_read`
- `synthesis_import_dev_test_write`
- `synthesis_import_dev_test_preview`

Permission behavior:

- Missing, disabled, invalid, or approval-only permissions fail closed.
- Preview form submission persists only when write and preview permissions are
  enabled.
- Prior-preview summaries require read permission.
- No apply permission, live permission, model permission, or external-write
  permission exists in Phase 11B.

Non-goals:

- No applying/saving candidates into priorities, routines, follow-ups, or any
  other core state.
- No PersonalOS Markdown writes.
- No Todoist writes.
- No Calendar writes.
- No Gmail send or draft.
- No live model/API calls.
- No OpenAI/OpenRouter/Anthropic calls.
- No scheduler or LaunchAgents.
- No production runtime activation.
- No `.openclaw` access.
- No full PersonalOS vault access.
- No public internet exposure.
- No credentials or OAuth.
- No live external writes of any kind.
- No broad dashboard editor framework.
- No auth/login yet.
- No LAN/public bind relaxation.

## Phase 12A: Operator CLI for No-Send Workflows

Status: complete.

Scope:

- Add a package CLI entrypoint exposed as `personalos`.
- Keep the command layer thin and reuse existing status, Today View,
  dashboard render, briefing loop, synthesis import, permission, validation,
  and safety helpers.
- Require explicit `--db` on all DB-backed commands.
- Require explicit `--output-file` on file-writing commands.
- Print human-readable completion reports by default and support `--json`
  where practical.
- Add static/read-only dashboard HTML rendering without binding a server.
- Add briefing preview through the existing fake Composer/no-send path only.
- Add briefing export for existing local briefing outputs.
- Add synthesis preview persistence for structured inputs only.

Supported commands:

- `personalos status --db <absolute-temp-or-dev-sqlite-path>`
- `personalos today --db <path> --date YYYY-MM-DD --timezone America/Chicago`
- `personalos briefing preview --db <path> --date YYYY-MM-DD --timezone America/Chicago --window morning`
- `personalos briefing export --db <path> --briefing-output-id <id> --output-file <safe-output-file>`
- `personalos synthesis preview --db <path> --input-file <structured-input-file> --source-type chatgpt_synthesis`
- `personalos dashboard render --db <path> --date YYYY-MM-DD --timezone America/Chicago --output-file <safe-html-file>`

Safety behavior:

- DB paths must be explicit absolute paths to existing temp or repo-local dev
  SQLite files and must pass protected-path, credential/OAuth-looking, and
  production-looking rejection.
- Input paths for `synthesis preview` must be explicit absolute paths and must
  pass protected-path, credential/OAuth-looking, production-looking, and
  repo-local `var/` rejection before file reads.
- File output paths must be explicit absolute paths, must not be under
  `/Users/coldstake/PersonalOS`, `/Users/coldstake/.openclaw`, LaunchAgents,
  credential/OAuth-looking paths, production-looking paths, or repo-local
  `var/`, and must have an existing parent directory.
- Status, Today View, briefing export, and dashboard render do not mutate DB
  state.
- Briefing preview persists only no-send local preview records through the
  fake Composer adapter and preserves `no_external_writes: true`.
- Synthesis preview persists only `synthesis_import_previews` records and
  preserves the Phase 11A high-stakes, raw-prose, raw-notes, and
  credential/protected-looking input gates.

Non-goals:

- No scheduler.
- No LaunchAgents.
- No live Gmail send or draft.
- No live Todoist writes.
- No live Calendar writes.
- No live model/API calls.
- No OpenAI/OpenRouter/Anthropic integration.
- No PersonalOS Markdown writes.
- No `.openclaw` integration.
- No full PersonalOS vault access.
- No apply/save import flow.
- No dashboard mutation routes.
- No server bind for `dashboard render`.
- No production DB path activation.
- No repo-local `var/` output.

## Phase 12B: Side-Effect and Idempotency Ledger Foundation

Status: complete.

Scope:

- Add local SQLite ledgers for `external_write_intents`,
  `external_write_attempts`, and `idempotency_records`.
- Generate deterministic idempotency keys from stable source, target,
  operation, dedupe, and payload fields.
- Generate deterministic payload fingerprints from canonical JSON payloads.
- Validate future external write intents for Todoist, Calendar, Gmail,
  PersonalOS Markdown, and other rails without executing them.
- Detect duplicate intents by idempotency key or target/operation/dedupe key.
- Record dry-run, simulated, or live-blocked attempts only as local ledger
  rows.
- Expose read-only side-effect ledger counts in status, Today View, and the
  dashboard.
- Add minimal CLI support for read-only summary and dry-run record insertion.

Permission keys:

- `side_effect_ledger_dev_test_read`
- `side_effect_ledger_dev_test_write`
- `side_effect_ledger_dev_test_record_attempt`

Safety behavior:

- Completion reports must expose `no_external_writes=true`,
  `no_send_mode=true`, `live_write=false`, and
  `simulated_or_dry_run=true`.
- High-risk objects cannot be auto-allowed.
- The database schema rejects `live_write=1`, `no_external_writes=0`, and
  `no_send_mode=0`.
- CLI dry-run recording reads only explicit safe input files and performs only
  local dev/test SQLite writes after explicit dev/test permissions are enabled.

Non-goals:

- No live Todoist writes.
- No live Calendar writes.
- No Gmail send or draft.
- No PersonalOS Markdown writes.
- No `.openclaw` integration.
- No scheduler or LaunchAgents.
- No live model/API calls.
- No OpenAI/OpenRouter/Anthropic integration.
- No production DB activation.
- No apply/save synthesis import flow.
- No dashboard mutation forms or execute/apply command.
- No public/LAN dashboard exposure, auth/login, Apple Health/wearables,
  Notion, TradingView, or market-data integration.

## Phase 13A: Approval-Gated Synthesis Apply Flow

Status: merged baseline.

Scope:

- Add local SQLite apply audit tables for `synthesis_apply_runs` and
  `synthesis_apply_items`.
- Apply existing `synthesis_import_previews` only after an explicit approval
  JSON file references the same `preview_id`.
- Require candidate-by-candidate approval by candidate type and index.
- Re-run candidate validation at apply time before any internal state write.
- Apply only safe internal core-state candidates for priorities, projects, and
  follow-ups.
- Record every candidate outcome with approval status, apply status, target
  table/ID when relevant, validation report, and rollback metadata.
- Safely skip duplicate internal state records on repeated apply attempts.
- Surface read-only apply history counts and latest safety flags in status,
  Today View, and the static dashboard.
- Add CLI support through `personalos synthesis apply --db <path>
  --preview-id <id> --approval-file <safe_json_path>`.

Permission keys:

- `synthesis_apply_dev_test_read`
- `synthesis_apply_dev_test_write`
- `synthesis_apply_dev_test_apply`

Safety behavior:

- Apply fails closed unless read, write, and apply permissions are explicitly
  enabled for dev/test use.
- Completion reports expose `no_external_writes=true`, `no_send_mode=true`,
  `live_write=false`, and an `internal_state_mutation` flag.
- Approval files must be explicit safe input files and must not live under
  protected PersonalOS, `.openclaw`, repo-local `var/`, credential/OAuth, or
  production-looking paths.
- Unsupported targets are recorded as unsupported, skipped, review-required,
  blocked, or failed at item level and are not executed.
- High-stakes execution candidates and manual-only candidates remain blocked
  or review-required instead of applied.

Non-goals:

- No live Todoist writes.
- No live Calendar writes.
- No Gmail send or draft.
- No PersonalOS Markdown writes.
- No external write intent creation.
- No `.openclaw` integration.
- No scheduler or LaunchAgents.
- No live model/API calls.
- No OpenAI/OpenRouter/Anthropic integration.
- No production DB activation.
- No dashboard Apply button, mutation form, or POST apply route.
- No public/LAN dashboard exposure, auth/login, Apple Health/wearables,
  Notion, TradingView, or market-data integration.

## Phase 13B: Synthesis Apply Atomicity / Recovery Hardening

Status: complete.

Scope:

- Keep the Phase 13A CLI, approval file, permission keys, supported targets,
  and candidate-level outcomes unchanged.
- Plan candidate outcomes before mutation where possible.
- Execute internal core-state inserts, `synthesis_apply_runs`,
  `synthesis_apply_items`, and `synthesis_import_previews` apply status updates
  inside one explicit SQLite transaction.
- Prevent committed priorities, projects, or follow-ups from drifting away from
  their apply audit trail.
- Preserve duplicate/idempotent reruns as no-op audit records with
  `skipped_duplicate` item outcomes.
- If an in-transaction write fails, roll back the whole apply transaction and
  write a failed recovery audit only after verifying that planned core-state
  inserts did not persist.

Recovery behavior:

- Successful applies set `internal_state_mutation=true` only when core rows are
  actually created.
- No-op duplicate, blocked, validation-failed, unsupported-only, and rollback
  recovery reports set `internal_state_mutation=false`.
- Rollback recovery reports set `rolled_back=true`, `rollback_verified=true`,
  and do not leave any apply item with `apply_status=applied`.
- Failed rollback recovery updates the preview status to `apply_failed` with the
  failed audit run/items in the same recovery transaction.

Safety behavior:

- Completion reports continue to expose `no_external_writes=true`,
  `no_send_mode=true`, `live_write=false`, `no_todoist_writes=true`,
  `no_calendar_writes=true`, `no_gmail_send=true`,
  `no_personalos_writes=true`, and `no_live_model_call=true`.
- No migration is required; recovery metadata is stored in the existing apply
  run/item JSON fields and the existing `internal_state_mutation` column already
  accepts `0`.
- No live Todoist, Calendar, Gmail, PersonalOS Markdown, model/API, scheduler,
  LaunchAgent, `.openclaw`, dashboard mutation, production DB activation,
  Phase 13C, or live-rail work is included.

Likely next phase:

- Phase 13C no-send scheduler/runtime-loop foundation, without live activation.

## Phase 13C: No-Send Scheduler / Runtime Loop Foundation

Status: complete.

Scope:

- Add local SQLite `scheduler_jobs` records for dev/test scheduler job
  definitions.
- Add local SQLite `scheduler_runs` records for foreground/manual simulated
  run attempts.
- Validate scheduler job definitions, cadence settings, timezone/date/window
  inputs, and fail-closed no-send/no-external-write flags.
- Support simulated job types for status summary, Today View summary,
  no-send briefing preview, side-effect ledger summary, synthesis apply
  history summary, and static dashboard render preview.
- Add CLI support through `personalos scheduler jobs`, `personalos scheduler
  preview`, `personalos scheduler run`, and `personalos scheduler seed-dev`.
- Surface read-only scheduler job/run counts, latest simulated status,
  warnings, and safety flags in status, Today View, and dashboard summaries.

Safety behavior:

- `enabled=true` means enabled for dev/test simulation only.
- All runs are synchronous, foreground, and manually invoked through the CLI.
- Completion reports expose `no_send_mode=true`, `no_external_writes=true`,
  `fake_model_only=true`, `live_write=false`, `external_mutation=false`,
  `scheduler_activation=false`, and `launch_agent_installed=false`.
- The schema rejects live-write, external-mutation, scheduler-activation, and
  LaunchAgent-installed values.
- Dashboard render preview requires an explicit safe `--output-file`.

Non-goals:

- No LaunchAgents.
- No crontab.
- No daemon/background process.
- No production runtime activation.
- No live Gmail send/draft.
- No live Todoist writes.
- No live Calendar writes.
- No PersonalOS Markdown writes.
- No `.openclaw` integration.
- No live model/API calls.
- No OpenAI/OpenRouter/Anthropic integration.
- No dashboard Run button, scheduler enable button, mutation form, or POST
  scheduler route.
- No public/LAN dashboard exposure, auth/login, Apple Health/wearables,
  Notion, TradingView, market-data integration, Phase 14, or live-rail work.

## Phase 13D: Checkpoint Hardening / Permission and Status Cleanup

Status: complete.

Scope:

- Add explicit project and followup status vocabularies in helpers and schema.
- Revalidate project/followup statuses during synthesis import and apply.
- Require side-effect ledger read permission on operator-facing summary paths.
- Preserve internal Today/status/dashboard read summaries as no-write helpers.
- Clarify dashboard wording as read-only except explicit local synthesis
  preview creation.
- Clean up practical SQLite ResourceWarnings around DB-path render helpers and
  direct connection-owner tests.
- Make the runtime bootstrap known-permission registry explicit and seed newer
  module permissions disabled by default.
- Document current idempotency scope and the pre-live collision-posture
  decision.
- Document the canonical full-suite test command:
  `PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py"`.

Non-goals:

- No scheduler activation, LaunchAgents, crontab, daemons, or background
  workers.
- No live Gmail send/draft, Todoist writes, Calendar writes, PersonalOS
  Markdown writes, live model/API calls, `.openclaw` integration, production
  DB activation, public/LAN dashboard exposure, auth/login, dashboard Apply
  button, Phase 13E, Phase 14, or live-rail work.

Likely next phase:

- Phase 13F-A docs-only pre-live readiness gate.

## Phase 13E-A: Operator Status Vocabulary And Report Shape

Status: complete.

Scope:

- Add a unified operator status report shape for existing inert readiness and
  status surfaces.
- Make `personalos readiness status` and `personalos status --db <safe_db>`
  human-readable enough for immediate operator review.
- Preserve JSON output for copy/paste audit by ChatGPT.
- Surface current mode, safe local actions, blocked live actions, and evidence
  that Personal OS remains inert/report-only.
- Keep readiness at `not_ready`, `inert_report_only=true`,
  `live_rails_activated=false`, live rails disabled, scheduler inactive,
  production DB inactive, credentials not loaded/read, external writes as
  none, and OpenClaw uncalled.

Non-goals:

- No live Gmail send/draft.
- No live Todoist writes.
- No live Calendar writes.
- No PersonalOS Markdown writes.
- No OpenClaw runtime operation.
- No scheduler activation, LaunchAgents, crontab, daemons, or background
  workers.
- No live model/API calls.
- No credentials or OAuth loading.
- No production DB activation or production ledger mutation.
- No migrations.
- No protected PersonalOS or `.openclaw` access.
- No Phase 14 or live-rail implementation.

## Phase 13E-B: CLI No-Send Workflow Polish

Status: complete.

Scope:

- Improve CLI help text for existing inert/no-send workflows.
- Add `personalos workflows` and `personalos workflows --json` as a
  report-only command catalog.
- List safe local workflows, the exact commands to run, local effects, output
  targets, and blocked live actions.
- Improve human-readable completion summaries for preview, export, approved
  local apply, ledger, status, readiness, and simulated scheduler commands.
- Preserve existing JSON output fields while adding stable workflow context for
  ChatGPT audit.
- Improve plain-English fail-closed errors for missing safe DB/input/output
  arguments, malformed JSON, and unsafe local workflow mistakes.
- Reuse `operator_status.v1`, `readiness_status`, `inert_report_only`,
  `live_rails_activated`, safe local actions, blocked actions, credentials,
  external-write, scheduler, and production DB status vocabulary.

Non-goals:

- No live Gmail send/draft.
- No live Todoist writes.
- No live Calendar writes.
- No PersonalOS Markdown writes.
- No OpenClaw runtime operation.
- No scheduler activation, LaunchAgents, crontab, daemons, or background
  workers.
- No live model/API calls.
- No credentials or OAuth loading.
- No production DB activation or production ledger mutation.
- No migrations.
- No protected PersonalOS or `.openclaw` access.
- No Phase 14 or live-rail implementation.

## Phase 13E-C: Dashboard Safe-Action/Status Polish

Status: current.

Scope:

- Improve the local dashboard/status display for existing inert/no-send
  workflows.
- Reuse `operator_status.v1` and the existing `operator_status_summary`
  emitted by Today View JSON.
- Add a visible NOT READY, inert/no-send/report-only dashboard posture banner.
- Show safe local actions, blocked live actions, and inert evidence on the
  dashboard.
- Clarify dashboard wording for synthesis previews, approved local apply
  history, no-send briefing output, and simulated scheduler summaries.
- Preserve dashboard JSON compatibility while making
  `operator_status_summary.safe_local_actions`, `blocked_actions`, and
  `evidence` useful for ChatGPT audit.

Non-goals:

- No live Gmail send/draft.
- No live Todoist writes.
- No live Calendar writes.
- No PersonalOS Markdown writes.
- No OpenClaw runtime operation.
- No scheduler activation, LaunchAgents, crontab, daemons, or background
  workers.
- No live model/API calls.
- No credentials or OAuth loading.
- No credential/OAuth setup UI.
- No production DB activation or production ledger mutation.
- No dashboard activation controls, scheduler controls, or production runtime
  toggles.
- No migrations.
- No protected PersonalOS or `.openclaw` access.
- No Phase 13E-D, Phase 14, or live-rail implementation.

## Phase 13F-A: Pre-Live Readiness Gate Docs

Status: complete.

Scope:

- Add [Pre-Live Readiness Gate](PRE_LIVE_READINESS.md) as the master gate
  before any Phase 14/live-rail work.
- Add [Live Rail Activation Policy](LIVE_RAIL_ACTIVATION_POLICY.md) for Gmail,
  Todoist, Google Calendar, PersonalOS Markdown, OpenClaw runtime workflows,
  scheduler/LaunchAgent/background loop activation, live model/API calls, and
  production SQLite state.
- Add [Operator Handoff Contract](OPERATOR_HANDOFF_CONTRACT.md) for the
  boundary between ChatGPT, Codex/Fable, OpenClaw, and Chris.
- Add [Production DB Policy](PRODUCTION_DB_POLICY.md) for production SQLite
  path approval, migration, backup, restore verification, locking, integrity,
  rollback, audit logging, and repo-local artifact prohibition.
- Link the new policies from the existing safety, workflow, architecture,
  roadmap, and README docs.

Non-goals:

- No source code.
- No tests.
- No migrations.
- No configs.
- No scripts.
- No runtime state.
- No live Gmail send/draft.
- No live Todoist writes.
- No live Calendar writes.
- No PersonalOS Markdown writes.
- No OpenClaw runtime operation.
- No scheduler activation, LaunchAgents, crontab, daemons, or background
  workers.
- No live model/API calls.
- No production DB activation.
- No protected PersonalOS or `.openclaw` access.
- No Phase 13E, Phase 14, or live-rail implementation.

Likely next phase:

- Phase 13F-B inert pre-live readiness gate config/schema/tests.

## Phase 13F-B: Inert Pre-Live Readiness Gate

Status: complete.

Scope:

- Add an inert readiness model and evaluator for the Phase 13F-A policy gates.
- Represent live rail statuses for Gmail, Todoist, Google Calendar,
  PersonalOS Markdown writes, OpenClaw runtime workflows, scheduler/
  LaunchAgent/background loop activation, live model/API calls, and production
  SQLite state.
- Default every live rail to disabled and fail closed when config is missing
  or required approval markers are absent.
- Keep readiness evaluation pure/read-only: no external services, credential
  loading, scheduler activation, OpenClaw operation, production DB mutation, or
  runtime-state mutation.
- Add focused unit tests for default blocked/not-ready behavior, missing
  config, dry-run/apply/live terminology, protected path rejection, Chris
  approval, kill switch, idempotency, side-effect ledger, completion report,
  and first-live pilot gates.

Non-goals:

- No live Gmail send/draft.
- No live Todoist writes.
- No live Calendar writes.
- No PersonalOS Markdown writes.
- No OpenClaw runtime operation.
- No scheduler activation, LaunchAgents, crontab, daemons, or background
  workers.
- No live model/API calls.
- No credentials or OAuth loading.
- No production DB activation or production ledger mutation.
- No protected PersonalOS or `.openclaw` access.
- No Phase 13E, Phase 14, or live-rail implementation.

Likely next phase:

- Phase 13F-C read-only CLI/dashboard readiness status surface.

## Phase 13F-C: Read-Only Readiness Status Surface

Status: complete.

Scope:

- Expose the Phase 13F-B inert pre-live readiness evaluator through local
  operator/status surfaces.
- Add `personalos readiness status` as a no-DB, no-write, inert readiness
  report command.
- Surface the same default readiness report in existing read-only status,
  Today View, and dashboard render summaries.
- Display overall readiness, gate results, live rail statuses, missing or
  blocked reasons, and explicit no-activation safety flags.
- Keep the readiness report informational only: it does not enable live
  permissions, call adapters, mutate state, load credentials, or activate
  runtime systems.

Non-goals:

- No live Gmail send/draft.
- No live Todoist writes.
- No live Calendar writes.
- No PersonalOS Markdown writes.
- No OpenClaw runtime operation.
- No scheduler activation, LaunchAgents, crontab, daemons, or background
  workers.
- No live model/API calls.
- No credentials or OAuth loading.
- No production DB activation or production ledger mutation.
- No migrations.
- No protected PersonalOS or `.openclaw` access.
- No Phase 13E, Phase 14, or live-rail implementation.

Likely next phase:

- Phase 13F-D activation checklist and first-live pilot protocol.

## Phase 13F-D: Activation Checklist And First-Live Pilot Protocol

Status: complete.

Scope:

- Add [Activation Checklist](ACTIVATION_CHECKLIST.md) as the final future
  checklist before any live rail can be activated.
- Add [First-Live Pilot Protocol](FIRST_LIVE_PILOT_PROTOCOL.md) to define how
  the first live pilot will eventually be selected, rehearsed, approved, run,
  audited, and halted or expanded.
- Update the existing pre-live readiness, live rail activation, operator
  handoff, production DB, safety, and architecture docs to reference the new
  gates.
- Keep Phase 13F-D protocol/checklist only. It does not execute the checklist,
  complete the pilot protocol, approve Phase 14, or activate live systems.

Non-goals:

- No live Gmail send/draft.
- No live Todoist writes.
- No live Calendar writes.
- No PersonalOS Markdown writes.
- No OpenClaw runtime operation.
- No scheduler activation, LaunchAgents, crontab, daemons, or background
  workers.
- No live model/API calls.
- No credentials or OAuth loading.
- No production DB activation, creation, migration, or production ledger
  mutation.
- No migrations.
- No source activation controls.
- No protected PersonalOS or `.openclaw` access.
- No Phase 13E, Phase 14, or live-rail implementation.

Likely next phase:

- Separate review or follow-on readiness hardening only after explicit
  approval. Live rails, scheduler activation, production DB activation, and
  OpenClaw runtime operation remain separate future approvals.
