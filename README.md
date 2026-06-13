# Personal OS

Personal OS is a modular, local-first productivity, routine, priority, and execution operating system. It is designed to coordinate strategy, software, local automation, durable notes, and external execution systems behind explicit safety gates.

## Operating Model

- ChatGPT owns strategy, synthesis, PRDs, architecture review, acceptance criteria, and audit.
- Codex owns the software development layer in this repository.
- OpenClaw remains the approved local runtime and operator on the Mac Mini.
- The Mac Mini is the runtime and deployment host.
- GitHub is the source of truth for code.
- SQLite will hold structured runtime state when the project reaches an approved runtime phase.
- Markdown and Obsidian will hold Clarity Notes, Follow-Up Notes, logs, and protocols.

## Phase

This repository is currently in Phase -1 setup. The only permitted work is repository scaffolding, documentation, and inert placeholders.

No live workflows should run from this scaffold.

## Safety Boundary

Codex must not mutate live Gmail, Todoist, Calendar, LaunchAgents, production ledgers, production SQLite state, OpenClaw runtime config, credentials, or any production state without explicit approval.

The first live-system interaction phase is read-only inventory only.

See [docs/SAFETY_POLICY.md](docs/SAFETY_POLICY.md) for the working safety policy.

## Repository Layout

```text
docs/          Product, architecture, safety, roadmap, and Codex workflow docs.
app/           Future application surfaces such as dashboard and APIs.
personalos/    Future domain modules for routines, priorities, composer, integrations, reports, and evidence.
scripts/       Inert helper scripts only when explicitly approved in a later phase.
tests/         Test suites for repository code.
.codex/        Codex-local project guidance and metadata.
```

## Next Step

Review and approve the Phase 0 inventory plan before any interaction with live local systems.
