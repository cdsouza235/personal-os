# Safety Policy

## Purpose

Personal OS should feel lightweight to use while remaining safety-aware, configurable, logged, and reversible. This policy defines which systems are protected, how execution gates work, and what evidence is required.

## Current Boundary

Phase 3 implementation is repository-code-only and dev/test-only. It may edit
repo-local code, tests, and documentation, and may create temporary dev/test
SQLite databases during tests. It must not inspect or mutate live runtime files,
credentials, external systems, production ledgers, production SQLite state, or
any production state.

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

The composer model receives only a dedicated Composer Packet. It must not receive broad filesystem access, raw notes, the full PersonalOS vault, credentials, legal/tax source documents, or unrestricted files.

Composer Packet input fields:

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

Composer output must include structured JSON plus readable text. Required sections are email_briefs, todoist_tasks, calendar_blocks, followups, and warnings.

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
