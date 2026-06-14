# Codex Workflow

## Role

Codex is the primary coding agent and software development layer for Personal OS. It edits repository code, tests, and documentation after phase gates. It does not act as the production operator.

Fable is an optional or future alternate coding agent for long-horizon software development work. Fable has the same production boundary as Codex unless a future policy says otherwise.

OpenClaw remains the production and runtime operator.

ChatGPT remains the strategy, synthesis, and audit layer.

## Current Work Type

Phase 3 is approved for repo-local code, tests, and documentation. Codex may
implement the dev/test-only routine engine foundation in this repository, run
local tests, push the branch, and open or update the PR. Codex must stop before
merge and must not inspect or mutate protected runtime paths, external systems,
credentials, production ledgers, production SQLite state, or production state.

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

Phase 3 may not start a scheduler, activate recurring automation, wire
OpenClaw, create LaunchAgents, add external API clients, touch Gmail, Todoist,
or Calendar, write production SQLite, add credentials, expose a web surface, or
start Phase 4.

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

First-pass Composer Packet input fields:

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

Composer output schema must include:

- email_briefs
- todoist_tasks
- calendar_blocks
- followups
- warnings
