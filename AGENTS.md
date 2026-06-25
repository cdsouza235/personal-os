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

For Personal OS repo work, Codex/Fable should prefer larger bounded work
packets over repeated micro-checkpoint loops when the work is repo-local,
inert, testable, inside an approved scope, and docs-only, test-only,
fake/local, read-only, report-only, no-send, preview, dry-run, or otherwise
non-live. In those conditions, Codex/Fable may complete multiple approved
repo-local substeps before returning.

After Chris approves a safe long-run envelope, the default unit of work is the
completed bounded packet, not an individual micro-invariant, one small doc
edit, or one narrow test tweak. Codex/Fable should bundle adjacent safe
repo-local substeps and return one PR/audit packet for the completed bounded
packet, rather than forcing a Claude Code audit after every micro-invariant,
unless the scope becomes ambiguous, a required audit boundary is reached, or a
real human gate appears.
Claude Code audit should happen after the bundled packet is ready unless a
real gate requires earlier review.

When the approved work envelope is clear and safety assertions remain clean,
Codex/Fable should not stop after every small milestone. It should continue
until the packet is complete, the PR or approved PR stack is ready, validation
fails in a way that needs judgment, the scope becomes ambiguous, or a
mandatory stop boundary is reached.

Post-merge verification is normally sufficient. Codex/Fable must not create a
standalone checkpoint/status refresh PR after every merge by default. A
separate checkpoint/status refresh PR is allowed only when stale status docs
would materially mislead the next work packet, stale checkpoint docs would block
safe validation or handoff, the repo is being left at a longer-term stopping
point, Chris explicitly asks for a checkpoint refresh, or a safety, audit, or
governance change requires a canonical checkpoint before further work.
Otherwise, fold checkpoint/status refreshes into the next substantive safe
repo-local packet.

Codex/Fable should prefer larger bounded packets that combine adjacent safe
work, such as checkpoint refresh, docs discoverability updates, invariant test
hardening, small consistency fixes, audit follow-up nits, and
validation/reporting updates. Do not stop after every small milestone unless a
real gate is reached.

Codex/Fable must stop before live Gmail/Todoist/Calendar writes,
credential/API/OAuth/secrets/token handling, production DB activation,
protected path access, scheduler/background/LaunchAgent/crontab/daemon/
watcher/service changes, OpenClaw runtime handoff or invocation, external
runtime writes, live model/API calls, high-stakes execution, major product
direction choices, and any merge that is not covered by a current explicit
delegated repo-merge instruction.

Real gates include human merge approval, required Claude Code audit, live
activation, Phase 14-C authorization, candidate approval, candidate
authorization, candidate activation or execution, external-service access or
writes, credentials/auth handling, production DB activation,
scheduler/background activation, OpenClaw invocation, protected path access,
live model/API calls, dynamic cleaning implementation, high-stakes execution
boundaries, and test failures requiring architectural, product, safety, or
workflow judgment.

Human judgment conditions include any product, safety, scope, or design choice
that cannot be resolved from repo-local evidence; any secrets, credentials,
OAuth, API keys, tokens, or actual live-service testing; and any failed
validation that requires architectural, product, safety, or workflow judgment.
When one of those conditions appears, Codex/Fable must stop and ask Chris
instead of guessing.

Delegated repo-merge authority, when Chris grants it for a current long-run
loop, is limited to repo-local, inert, deterministic, testable work after the
audited head commit, mergeable/clean state, validation, clean worktree, and
Claude Code `Pass` or `Pass with notes` gates all pass. It is repo merge
authority only and must not be read as product approval, Phase 14-C
authorization, candidate approval, candidate authorization, candidate
activation or execution, live-service access, live activation, credential
handling, production DB activation, scheduler/background activation, OpenClaw
invocation, protected-path access, dynamic cleaning implementation, Watch Tower
adoption, `.agent/`, `CLAUDE.md`, or runtime/operator scaffolding.

This protocol is not Watch Tower adoption and does not authorize `.agent/`,
`CLAUDE.md`, runtime/operator scaffolding, OpenClaw invocation, live
Todoist/Gmail/Calendar access, credential handling, or scheduler/background
activation.

For every PR-opening packet, Codex/Fable final reports must include a Claude
Code audit recommendation:

- `Required`
- `Recommended`
- `Not needed`

The report must include the reason. If the recommendation is `Not needed`, the
report must explain why the PR is narrow enough to skip Claude Code audit. If
the recommendation is `Required` or `Recommended`, Codex/Fable must stop after
opening the PR and must not merge. ChatGPT and Chris route the PR through any
needed Claude Code audit before human merge approval.

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
