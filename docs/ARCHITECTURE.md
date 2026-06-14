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

## Briefing Architecture

Timezone: America/Chicago.

America/Chicago is Chris's operating timezone for briefings and routines. The Mac Mini system timezone may differ. Scheduler code must explicitly use the configured operating timezone and must not assume the host timezone.

- 8am Morning Brief.
- 12pm Midday Reset.
- 4pm Afternoon Checkpoint.
- 8pm Evening Shutdown.

The daily plan is generated once in the morning. Each email is generated just-in-time before its briefing window. Todoist and Calendar baseline writes happen in the morning. Later windows use updated state, including completed tasks and schedule changes.

## Composer Model Architecture

The strong composer model receives only a dedicated Composer Packet.

It must not receive broad filesystem access, raw notes, the full PersonalOS vault, credentials, legal/tax source documents, or unrestricted files.

First-pass Composer Packet input:

- date
- timezone
- briefing_window
- routines_due
- routines_completed
- missed_routines
- active_priorities
- followups
- calendar_summary
- todoist_summary
- routine_rules
- permissions
- model_instructions
- excluded_sensitive_context_note

Required output:

- Structured JSON.
- Readable text.

Required output sections:

- email_briefs
- todoist_tasks
- calendar_blocks
- followups
- warnings

No prose-only output may be used for execution.

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

Reports are coded jobs, not a separate analyst persona. Chris and ChatGPT define requirements. Codex builds jobs. OpenClaw runs jobs and delivers outputs.

Examples include macro calendar, earnings calendar, TradingView alert digest, priority status report, routine adherence report, Todoist completion report, and calendar utilization report.

## Weekly Chart Pack Hook

The weekend workflow reminds Chris to produce chart packs. Chris sends chart packs and TradingView alerts to ChatGPT. ChatGPT synthesizes. OpenClaw stores the synthesis and updates weekly chart review notes. The system tracks week-over-week changes. OpenClaw does not independently analyze investments.

## Fitness Hook

V1 preserves the existing CSV-based local fitness tracker and exposes a shell, link, and status. V1.5 may integrate routine prompts and recovery/training state.

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
