# Codex/Fable Workflow

Last updated: 2026-06-18

## Required First Reads

Before repo work, Codex/Fable must read:

- [../AGENTS.md](../AGENTS.md)
- [../STATUS.md](../STATUS.md)

Use [../STATUS.md](../STATUS.md) as the current-state snapshot and
[ROADMAP.md](ROADMAP.md) as phase history.

## Role

Codex/Fable works in repository branches. Codex/Fable may edit code, tests,
docs, and migrations inside the repo scope after the appropriate phase gate.
Codex/Fable does not act as production operator.

ChatGPT remains the strategy, synthesis, architecture, and audit layer.
OpenClaw remains a future approved runtime/operator only.

## Allowed Repo Work

Codex/Fable may:

- read repository-local files
- create or switch repo branches
- edit repository code, tests, docs, and migrations within approved scope
- run repo-local tests and hygiene checks
- create commits and PRs when approved
- write completion reports

## Prohibited Work

Codex/Fable must not:

- inspect or mutate `/Users/coldstake/PersonalOS`
- inspect or mutate `/Users/coldstake/.openclaw`
- touch credentials, OAuth files, tokens, or credential stores
- touch production SQLite paths or production ledgers
- send, draft, read, or mutate Gmail
- write or mutate Todoist
- write or mutate Google Calendar
- write PersonalOS Markdown
- load or modify LaunchAgents
- write crontab entries
- start daemons/background loops
- activate schedulers
- activate production DB paths
- call OpenClaw
- call live external services
- perform external writes
- start Phase 14 without explicit approval

## Validation Commands

Run tests with `PYTHONPATH=src`.

```bash
git status --short
git diff --check
git diff --cached --check
PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py"
PYTHONTRACEMALLOC=10 PYTHONPATH=src python3 -W always::ResourceWarning -m unittest discover -s tests -p "test_*.py" -q
find . -maxdepth 2 -name var -print
find . -path ./.git -prune -o \( -name "*.sqlite" -o -name "*.sqlite3" -o -name "*.db" \) -print
```

If a task is docs-only, do not treat that as permission to skip hygiene unless
Chris says to skip it.

## Completion Report

Completion reports must include:

- branch name
- files changed
- summary of changes
- tests run and results
- hygiene results
- safety confirmation
- PR number or URL if opened

Safety confirmation must state whether live rails, credentials, production DB,
scheduler/LaunchAgents/crontab/daemons, external writes, OpenClaw calls, and
protected runtime/personal paths were touched.

## Phase Boundaries

Phase 13E-D is implemented and post-merge validated. Phase 13G is a
planning/control-plane readiness matrix candidate only. Phase 14 is not
started. Docs, readiness reports, checklists, pilot protocols, and readiness
matrices do not activate live rails by themselves.
