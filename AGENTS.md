# Personal OS Agent Instructions

Personal OS is Chris's private, local-first productivity, routine, priority,
briefing, and execution operating system. This GitHub repository is the source
of truth for repo code, tests, migrations, and Markdown documentation.

Before starting repo work, read `STATUS.md`, this `AGENTS.md`, and the
relevant docs under `docs/`.

## Role Boundaries

- Chris: owner, final approver, and source of judgment.
- ChatGPT: strategy, synthesis, PRD, architecture, and audit layer.
- Codex/Fable: repository implementation, tests, docs, migrations, and PRs.
- OpenClaw: approved runtime/operator only; not repo implementation.

## Long-Run Work Packets

Long-run Codex/Fable work packets are allowed for repo-local, inert,
fake/local, docs-only, test-only, read-only, report-only, no-send, preview, or
dry-run work inside an approved envelope. When long-run mode is authorized,
Codex/Fable should not stop after every small milestone; it should continue
until the packet is complete, the PR or PR stack is ready, validation fails in
a way that needs judgment, or a mandatory stop boundary is reached.

Codex/Fable must stop before live rails, credentials/secrets/OAuth/API
keys/tokens, production DB paths, protected paths, scheduler/background/
LaunchAgent/crontab/daemon work, OpenClaw runtime, external runtime writes,
high-stakes execution, major product decisions, and merge approval.

See [docs/AGENT_WORK_PACKET_PROTOCOL.md](docs/AGENT_WORK_PACKET_PROTOCOL.md)
and [docs/CODEX_WORKFLOW.md](docs/CODEX_WORKFLOW.md).

## Source Of Truth

- GitHub repo: code, tests, migrations, and docs.
- SQLite: structured runtime state.
- PersonalOS/Obsidian/Markdown: durable notes later, behind explicit gates.
- Todoist/Calendar/Gmail/OpenClaw: gated live rails only.

## Hard Safety Boundaries

Codex/Fable must not inspect or mutate protected runtime or personal paths,
including `/Users/coldstake/PersonalOS`, `/Users/coldstake/.openclaw`,
LaunchAgents, credential stores, production ledgers, production SQLite paths,
or other production runtime state.

Codex/Fable must not send Gmail, write Todoist, write Google Calendar, load or
read credentials, activate production DB paths, install or activate schedulers,
write crontab entries, start daemons/background loops, call OpenClaw, call live
external services, or perform external writes unless Chris explicitly approves
that narrow work.

## Required Validation

Use the repo's canonical Python path:

```bash
git status --short
git diff --check
git diff --cached --check
PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py"
PYTHONTRACEMALLOC=10 PYTHONPATH=src python3 -W always::ResourceWarning -m unittest discover -s tests -p "test_*.py" -q
find . -maxdepth 2 -name var -print
find . -path ./.git -prune -o \( -name "*.sqlite" -o -name "*.sqlite3" -o -name "*.db" \) -print
```

## Core Docs

- [STATUS.md](STATUS.md): canonical current project snapshot.
- [docs/PRD.md](docs/PRD.md): product truth.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): system and role topology.
- [docs/SAFETY_POLICY.md](docs/SAFETY_POLICY.md): safety and activation gates.
- [docs/AGENT_WORK_PACKET_PROTOCOL.md](docs/AGENT_WORK_PACKET_PROTOCOL.md):
  long-run Codex/Fable packet rules.
- [docs/ROADMAP.md](docs/ROADMAP.md): phase history and next phase.
- [docs/CODEX_WORKFLOW.md](docs/CODEX_WORKFLOW.md): repo workflow.

## Stop Conditions

- Do not start Phase 14.
- Do not involve OpenClaw.
- Do not touch live rails.
- Do not touch protected runtime or personal paths.
- Stop and ask Chris when requested work would cross these boundaries.
