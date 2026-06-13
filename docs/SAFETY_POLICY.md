# Safety Policy

## Phase -1 Boundary

Phase -1 is repository setup only. Work is limited to scaffolding, placeholder documentation, and inert directory structure.

Codex must stop after scaffolding and must not proceed to inventory.

## Protected Systems

Codex must not inspect or mutate the following without explicit approval:

- Live Gmail state
- Live Todoist state
- Live Calendar state
- LaunchAgents
- Production ledgers
- Production SQLite state
- OpenClaw runtime config
- Credentials
- Any other production state

Codex must not inspect:

- `/Users/coldstake/PersonalOS`
- `/Users/coldstake/.openclaw`

## Mutation Rule

Codex must not mutate live Gmail, Todoist, Calendar, LaunchAgents, production ledgers, production SQLite state, OpenClaw runtime config, credentials, or any production state without explicit approval.

## First Live-System Interaction

The first live-system interaction phase is read-only inventory only. It requires explicit approval and must produce an inventory plan before execution.

## Runtime Operator

OpenClaw remains the runtime and operator. Codex may build repository code and documentation, but OpenClaw is responsible for approved local runtime workflows.

## Scripts

During Phase -1, the repository must not contain scripts that run live workflows.

Scripts may be added in later phases only after the intended behavior, safety boundary, and approval gate are documented.
