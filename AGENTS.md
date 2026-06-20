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

<!-- WATCH_TOWER_BUILDER_PROTOCOL v1 -->

## Watch Tower Builder Protocol

This repository participates in the Watch Tower puck-tracking workflow.

At the end of any bounded builder work packet, leave the project in a legible state.

Required final artifacts:

1. Update or create `.agent/status.yaml`.
2. Create a final report under `.agent/runs/`.
3. Produce a `WATCH_TOWER_HANDOFF.md` in the final response, or write it to `.agent/outbox/WATCH_TOWER_HANDOFF.md`.

The handoff must start with this front matter:

---
event_type: handoff
project_id: short_snake_case_id
project_name: Human Readable Project Name
source_agent: codex_or_claude_code
puck_with: one_allowed_value
next_action: "One concrete next action."
human_attention: none
---

Allowed `puck_with` values:

- me
- chatgpt
- claude
- codex
- claude_code
- openclaw
- none

Allowed `human_attention` values:

- none
- dispatch_only
- decision_required
- approval_required
- unblock_required
- review_required

Rules:

- Set `puck_with` to the actual next owner of the project action.
- Use `puck_with: me` only when the user must make a real decision, approve something, unblock something, or personally do the next action.
- If the user only needs to carry a packet to another tool, set `puck_with` to that destination tool and use `human_attention: dispatch_only`.
- Use `puck_with: none` only when the project has no next action or is complete.
- Do not directly ingest into Watch Tower unless explicitly authorized.
- Do not inspect unrelated folders.
- Do not access credentials, secrets, OAuth tokens, API keys, or protected paths.
- Do not activate live external writes.
- Do not touch production databases.
- Do not activate schedulers, daemons, LaunchAgents, crontabs, background loops, or automations.

Final report must include:

- scope completed
- files changed
- validation results
- safety assertions
- deviations
- open questions
- next recommended owner
- next recommended action

<!-- /WATCH_TOWER_BUILDER_PROTOCOL v1 -->
