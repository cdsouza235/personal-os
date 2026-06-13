# Codex Workflow

## Current Phase

Phase -1 is setup only. Codex may create repository structure, inert placeholders, and documentation.

Codex must stop before live-system inventory, runtime inspection, or automation.

## Responsibilities

Codex may:

- Edit code and documentation in this repository.
- Add tests for repository code.
- Create inert scaffolding for future modules.
- Document assumptions, safety boundaries, and acceptance criteria.

Codex must not:

- Mutate Gmail, Todoist, Calendar, LaunchAgents, production ledgers, production SQLite state, OpenClaw runtime config, credentials, or production state without explicit approval.
- Inspect `/Users/coldstake/PersonalOS`.
- Inspect `/Users/coldstake/.openclaw`.
- Create scripts that run live workflows during Phase -1.
- Proceed from scaffolding to inventory without a separate approval.

## Development Flow

1. Read repository-local context only.
2. Make focused changes in Git-tracked project files.
3. Add or update tests when executable behavior is introduced.
4. Summarize files changed, assumptions, verification, and the recommended next step.
5. Stop at the approved phase boundary.

## Runtime Boundary

OpenClaw remains the runtime and operator. Codex prepares code and documentation, but does not operate approved workflows unless a later phase explicitly grants that authority.

## External Systems
