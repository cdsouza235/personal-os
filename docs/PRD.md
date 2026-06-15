# Personal OS Master PRD v0.1

## Product Definition

Personal OS is a modular, local-first productivity, routine, priority, and execution operating system. It helps Chris think clearly, maintain routines, manage high-value priorities, generate briefings, create Todoist tasks, schedule Calendar blocks, preserve durable notes, and run reports through OpenClaw on the Mac Mini.

## Product Principles

- Chris remains the owner, final approver, and source of judgment.
- Todoist and Calendar are execution rails, not the brain.
- Obsidian and Markdown stay minimal and high-signal.
- SQLite holds structured runtime state.
- OpenClaw operates approved local workflows.
- ChatGPT synthesizes and audits.
- Codex is the primary coding agent and builds repository code.
- Fable is an optional or future alternate coding agent for long-horizon work.
- Safety should be light in the user experience and explicit in the architecture.

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

V1 should deliver a local-first operating shell and the core routines, priorities, briefings, and integration boundaries needed for daily use.

- Local dashboard shell.
- Routine editor.
- Today view.
- Priority registry.
- ChatGPT synthesis import box.
- SQLite runtime state store.
- 8am Morning Brief, 12pm Midday Reset, 4pm Afternoon Checkpoint, and 8pm Evening Shutdown.
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

The dashboard must be local-network only. It must not be exposed to the public internet. V1 does not require login or password protection by choice.

The dashboard should be mobile-friendly for iPhone and usable from Windows and Mac browsers.

Threat model:

- Risks include accidental local network access, stale browser sessions, and exposure from trusted devices on the network.
- Future security options may include a password, device allowlist, Tailscale/VPN access, or local-only binding.

Required sections:

- Today View
- Routine Editor
- Priority Editor
- Todoist/Calendar Preview
- System Status/Logs
- Settings/Permissions
- Reports/Jobs shell

## Routine Defaults

- Cleaning: 1 task/day, Monday-Friday.
- Reading: 4x/week.
- Prayer / Meditation: 2x/week.
- Grease-the-Groove: rotating exercises as needed, target 45 reps per exercise per week.
- Fitness / Strength: separate from Grease-the-Groove; the existing fitness tracker should be preserved and integrated later.
- Shutdown / Review: daily evening.

## Routine Engine Requirements

Routines must be data-driven, not hardcoded. The routine editor must allow add, edit, disable, and delete operations.

Supported cadence rules:

- daily
- weekdays
- x_times_per_week
- weekly
- every_n_days
- specific_days
- rotating_sequence
- manual_only

Supported missed behavior options:

- combine_with_next
- bump_schedule_by_one_day
- carry_forward_within_week
- skip_and_continue
- escalate_to_review

## Todoist Requirements

Todoist is the action rail, not the brain.

- Low-risk routine tasks can auto-write.
- High-value review and follow-up tasks can auto-write.
- High-stakes execution actions require approval.
- Vague thoughts and raw emotional notes must not become Todoist tasks.
- Completed Todoist tasks should be removed from later briefings.

## Calendar Requirements

- Preferred windows should be used first.
- Availability-aware scheduling can be added later.
- Self-only review, deep work, admin, and routine blocks may auto-write once validated.
- Events involving other people or high-stakes appointments require review.

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

## Briefing Cadence

Timezone: America/Chicago.

America/Chicago is Chris's operating timezone for briefings and routines. The Mac Mini system timezone may differ. Scheduler code must explicitly use the configured operating timezone and must not assume the host timezone.

- 8am: Morning Brief.
- 12pm: Midday Reset.
- 4pm: Afternoon Checkpoint.
- 8pm: Evening Shutdown.

Daily plan generation happens once in the morning. Each email is generated just-in-time before its window. Todoist and Calendar baseline writes happen in the morning. Later windows adjust based on completed tasks and updated state.

## Composer Packet Schema

Composer Packet `composer_packet.v1` is the only input surface for the
composer model. It contains `packet_id`, `packet_type`, `briefing_window`,
`source_date`, `timezone`, `generated_at`, `inputs`, `omissions`, and
`warnings`.

Allowed packet inputs are routine state, priority summaries, selected
follow-up summaries, Todoist task summaries, Calendar block summaries,
Calendar availability summary, today's schedule summary, WSP/routine rules,
prior briefing summaries, and completion status.

Forbidden composer inputs include broad filesystem access, raw notes, the full
PersonalOS vault, protected runtime paths, Gmail bodies, live Todoist API data,
live Calendar API data, legal/tax source documents, credentials, secrets,
OAuth tokens, unrestricted file access, raw journal archives, and arbitrary
filesystem paths.

Composer output `composer_output.v1` must include structured JSON plus
non-empty readable text. Required sections are:

- `email_briefs`
- `todoist_tasks`
- `calendar_blocks`
- `followups`
- `warnings`

Todoist and Calendar candidates must satisfy the existing execution-rail
schema and risk rules. Medium-risk and high-risk objects cannot be marked
`auto_allowed`. Candidate routing is a preview/report step only and must
include `no_external_writes: true`.

## Notes

Obsidian and PersonalOS should stay minimal.

Clarity Notes are durable, high-signal synthesis after ChatGPT processing. General Follow-Up Notes capture things to revisit, open questions, admin reminders, and project reminders.

Notes become Todoist tasks only if they meet the task schema.

## ChatGPT Synthesis Import Preview

Phase 11A supports importing already-synthesized ChatGPT material into a local
preview report. It is not raw-note ingestion and not an apply/save flow.

Accepted formats are canonical JSON, Markdown with one fenced JSON block, and
a small structured Markdown heading/bullet subset. Accepted source types are
`chatgpt_synthesis`, `manual_structured_import`, and `fake_fixture`. Raw notes,
raw journals, full vault dumps, legal/tax source documents, credential dumps,
unrestricted file input, unsupported prose, and credential-like input are
rejected.

Canonical imports use `synthesis_import.v1` with summary, warnings, and
candidate lists for priorities, projects, follow-ups, routine changes,
Todoist tasks, Calendar blocks, clarity notes, and review questions. Todoist
and Calendar candidates must pass the existing Phase 5 preview validators, but
Phase 11A does not create Todoist or Calendar records and does not call
adapters.

Preview reports must include candidate counts, accepted candidates, rejected
candidates, blocked candidates, review-required candidates, manual-only
candidates, questions for review, warnings, and safety flags for no external
writes, no state mutation, no PersonalOS writes, no Todoist writes, no
Calendar writes, no Gmail send, and no live model call.

High-stakes items covering tax, legal, estate, portfolio, crypto,
investments, health, medical, relationship messages, family-sensitive
communication, or large financial commitments must require approval or manual
handling. Portfolio/crypto/investment execution language and legal/tax/medical
directives must not be low risk or `auto_allowed`.

Phase 11A may persist only local preview records in
`synthesis_import_previews`. It does not apply/save candidates into core state,
write PersonalOS Markdown, write Todoist, write Calendar, send or draft Gmail,
call live model APIs, add a scheduler or LaunchAgents, activate production
runtime, access `.openclaw`, access the full PersonalOS vault, add dashboard
mutation/edit forms, add a paste box UI, expose public internet access, read
credentials/OAuth, or perform live external writes.

## Weekly Chart Pack Workflow

- Weekend reminder to produce chart packs.
- Chris sends chart packs and TradingView alerts to ChatGPT.
- ChatGPT synthesizes.
- OpenClaw stores synthesis and updates weekly chart review notes.
- The system tracks week-over-week changes.
- OpenClaw does not independently analyze investments.

Phase 7 implements only the repository foundation for this workflow. Chart
packs and TradingView alerts are manually supplied by Chris, stored as
validated JSON, and paired with ChatGPT-provided synthesis markdown. ChatGPT is
the interpretation layer for market and thesis synthesis. OpenClaw stores
approved workflow outputs and tracks week-over-week changes later; it does not
analyze investments independently.

Chart pack reviews must include structured summary sections for market
context, BTC context, ETH context, miner/HPC context, portfolio watch items,
week-over-week changes, follow-up candidates, and warnings. Follow-up
candidates are review/logging candidates only. The workflow must not produce
autonomous buy, sell, hold, rebalance, trade, or portfolio execution tasks.

## Fitness Integration

Phase 8 Fitness Integration Foundation preserves the existing CSV-based local
fitness tracker and adds only a dev/test contract/status shell. The existing
CSV-based local fitness tracker is preserved. V1 does not rebuild the tracker,
migrate its data, or replace it with Notion.

Fitness/strength is separate from Grease-the-Groove. The Phase 8 contract is
local CSV-based, library-first, and minimally verbose. It recognizes expected
tracker files:

- `workout_sessions.csv`
- `workout_exercises.csv`
- `weekly_recovery.csv`
- `exercise_library.csv`

Phase 8 validates contract objects and fixture CSV headers supplied by tests or
callers. It produces deterministic validation reports with
`no_external_writes: true` and `no_live_personalos_access: true`.

Phase 8 has no Notion dependency, no live PersonalOS CSV reads or writes, no
Apple Health or wearable API integration, no live fitness data import, no
workout recommendation engine, no medical/health advice engine, no
Todoist/Calendar/Gmail writes, no live model/API calls, no credentials or
OAuth, no scheduler or LaunchAgents, no production SQLite/runtime state, no
dashboard UI yet, no full PersonalOS vault access, and no unrestricted
filesystem access.

V1.5 may later add deeper recovery/training context in briefings after
separate approval.

## Runtime Bootstrap

Phase 9B creates the local/dev-preview runtime DB bootstrap foundation needed
before the usable MVP daily operating loop. It is a bridge from tested modules
to a local runtime database; it is not production activation and not a live
runtime launch.

The bootstrap profile requires explicit `dev_runtime` or
`local_runtime_preview` mode, an explicit SQLite DB path, backup enabled,
`no_external_writes: true`, `no_send_mode: true`, a seed profile name, and a
creator label. Protected PersonalOS, OpenClaw, LaunchAgents,
credential/OAuth-looking, and production-looking paths are rejected.

The bootstrap preview is non-mutating and reports the target DB path, pending
migrations, backup path that would be used if the DB exists, seed profile, and
safety flags. Bootstrap execution creates a backup before migrating an
existing explicit temp/dev DB, applies repository migrations, keeps SQLite
foreign keys enabled, and records local bootstrap evidence.

The MVP preview seed profile writes only local SQLite state. It disables
external/live-facing permissions, creates paused disabled preview routines,
creates a fake paused preview priority, and creates no-send draft briefing
window definitions. Briefing windows are inert definitions only; there is no
scheduler, web server, dashboard UI, or daily briefing generation loop in
Phase 9B.

Phase 9B adds no live Todoist writes, live Calendar writes, Gmail send, live
model/API calls, Notion, Apple Health, TradingView/API calls, credentials,
OAuth, LaunchAgents, production SQLite/runtime state mutation, protected
PersonalOS or OpenClaw access, or production runtime activation.

## No-Send Briefing Loop

Phase 10B adds a no-send daily briefing loop foundation for local/manual
previews. It builds daily plans from existing runtime state and Today View
summaries, selects inert briefing windows, uses the fake Composer path only,
stores local `daily_plans` and `briefing_outputs`, and returns readable text,
manual export only markdown, and a completion report.

Phase 10B permission keys are `briefing_loop_dev_test_read`,
`briefing_loop_dev_test_write`, and `briefing_loop_dev_test_run`. They fail
closed by default. Generating and storing a no-send preview requires explicit
dev/test write and run permission.

Phase 10B adds no Gmail sending, no Gmail drafts, no live Todoist writes, no
live Calendar writes, no Todoist/Calendar writes, no live model calls, no
scheduler or LaunchAgents, no credentials/OAuth, no production SQLite/runtime
state mutation, no protected PersonalOS or OpenClaw access, and no external
writes of any kind.

## Dashboard Briefing Integration

Phase 10C dashboard briefing integration makes existing Phase 10B no-send
briefing outputs visible in Today View and the read-only dashboard shell. It
adds a Briefing Outputs section, latest output status, manual export preview,
completion report safety flags, warnings/failures, and the same summary in
the existing JSON render path.

The manual export preview is read-only. Phase 10C adds no generation button,
no dashboard mutation, no scheduler, no Gmail/model/Todoist/Calendar writes,
no Gmail drafts, no live model/API calls, no credentials/OAuth, no
LaunchAgents, no production SQLite/runtime state mutation, no protected
PersonalOS or OpenClaw access, no public internet exposure, no routine or
priority editor, no synthesis import, and no external writes of any kind.

Phase 10B manual exports are local fake/no-send content. Future real-content
redaction or review may be needed before broader network exposure or any
non-local dashboard access is considered.

## Reports and Jobs

Reports are coded jobs, not a separate analyst persona. Chris and ChatGPT
define requirements. Codex builds job definitions, schemas, validation,
deterministic local runners, tests, and documentation. OpenClaw runs approved
jobs and delivers outputs later through validated runtime modules.

Example jobs:

- Weekly chart pack index.
- Macro calendar.
- Earnings calendar.
- TradingView alert digest.
- Priority status report.
- Routine adherence report.
- Todoist completion report.
- Calendar utilization report.

Phase 7 adds dev/test-only `report_jobs`, `report_runs`, and
`chart_pack_reviews` tables. It supports manual, daily, weekly, and monthly
job cadences; draft, active, paused, and disabled job states; preview, dry-run,
and simulated run types; and draft, validated, stored, and rejected chart pack
review states.

Phase 7 does not add live market data fetching, TradingView API access,
investment recommendations, portfolio execution, Todoist writes, Calendar
writes, Gmail send, live model/API calls, credentials, OAuth, scheduler
activation, LaunchAgents, production SQLite access, dashboard UI, protected
PersonalOS vault access, or unrestricted filesystem access.

## Evidence Standard

Development work should produce a diff summary, test logs, unit or integration output when applicable, and a brief implementation note.

Runtime or live operations should produce a persisted completion report, ledger or log snapshot, and safety flags.

Forensic bundles are reserved for incidents, production activation, high-stakes operations, or duplicate/mutation anomalies.

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

## Protected Non-Goals

- No live-system inventory.
- No Gmail, Todoist, Calendar, LaunchAgent, production ledger, credential, runtime, or production SQLite mutation.
- No inspection of `/Users/coldstake/PersonalOS`.
- No inspection of `/Users/coldstake/.openclaw`.
- No live workflow scripts.
