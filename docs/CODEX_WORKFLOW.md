# Codex/Fable Workflow

Last updated: 2026-06-26

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

## Long-Run Mode

Long-run mode is the preferred workflow for larger bounded Personal OS repo
work when the work is:

- repo-local
- inert
- testable
- inside an approved scope
- docs-only, test-only, fake/local, read-only, report-only, no-send, preview,
  dry-run, or otherwise non-live
- not touching credentials, secrets, OAuth files, API keys, tokens, or
  credential stores
- not activating production DB paths
- not touching protected paths
- not invoking OpenClaw
- not activating schedulers, background loops, LaunchAgents, crontab, daemons,
  watchers, or services
- not making external runtime writes
- not performing live Gmail, Todoist, or Calendar actions
- not making live model/API calls

When those conditions hold, Codex/Fable may complete multiple approved
repo-local substeps before returning. Codex/Fable should not stop after every
small milestone when the approved work envelope is clear and safety assertions
remain clean.

After Chris approves a safe long-run envelope, the default unit of work is the
completed bounded packet. Codex/Fable should bundle adjacent safe repo-local
substeps and return one PR/audit packet for the completed bounded packet, not
one PR or Claude Code audit after every micro-invariant, tiny doc edit, or
narrow test assertion. Claude Code audit should happen after the bundled
packet is ready unless the scope becomes ambiguous, a real human gate appears,
Chris narrows the scope, or a real audit boundary is reached.

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

For the current non-human MVP closure loop, Codex/Fable may target three to
five large repo-local, inert, deterministic packets, each followed by Claude
Code read-only audit before delegated merge conditions are evaluated. The
canonical plan is [NON_HUMAN_CLOSURE_PLAN.md](NON_HUMAN_CLOSURE_PLAN.md).
That plan does not include human decisions, live-service access, credential
handling, production DB activation, scheduler/background activation, OpenClaw
invocation, protected path access, dynamic cleaning implementation, Watch
Tower adoption, `.agent/`, `CLAUDE.md`, or runtime/operator scaffolding.

In long-run mode, Codex/Fable should continue until:

- the packet is complete
- the PR or approved PR stack is ready
- a safety boundary is reached
- a human decision is required
- validation fails in a way that needs judgment
- the approved envelope becomes ambiguous

Codex/Fable should keep a running implementation log in status updates, PR
notes, a packet document, or the final report.

### Mandatory Stop Gates

Codex/Fable must stop and request human review before:

- live Gmail/Todoist/Calendar writes
- credential/API/OAuth/secrets/token handling
- production DB activation
- protected path access
- OpenClaw runtime handoff or invocation
- scheduler/background activation
- LaunchAgent, crontab, daemon, watcher, or service changes
- high-stakes execution involving tax, legal/estate, portfolio/crypto,
  health/medical, relationship, external-message, external-meeting, family, or
  large-financial-commitment decisions
- major product direction choices
- merge approval unless a current explicit delegated repo-merge instruction
  applies and all delegated merge conditions pass
- product, safety, scope, or design choices that cannot be resolved from
  repo-local evidence
- actual live-service testing, live-service access, or live-service writes
- any test failure requiring architectural or product judgment

### Real Human Gates

A real human gate is a decision Chris must make, not a small repo milestone.
Real gates include live rail authorization, credential or production state
handling, protected path access, OpenClaw runtime handoff, scheduler or
background activation, high-stakes execution, major product direction changes,
merge approval, and judgment-heavy failures.

Real gates also include human merge approval, required Claude Code audit, live
activation, Phase 14-C authorization, candidate approval, candidate
authorization, candidate activation or execution, external-service access or
writes, credentials/auth handling, production DB activation,
scheduler/background activation, OpenClaw invocation, protected path access,
live model/API calls, dynamic cleaning implementation, high-stakes execution
boundaries, and test failures requiring architectural, product, safety, or
workflow judgment.

Local branch creation, repo-local edits, test additions, validation runs,
commits, PR body drafting, and PR opening are not separate human gates when
they are already inside the approved inert packet.

Human judgment conditions include any product, safety, scope, or design choice
that cannot be resolved from repo-local evidence; secrets, credentials, OAuth,
API keys, tokens, or credential stores; actual live-service testing; and any
failed validation that requires architectural, product, safety, or workflow
judgment. Codex/Fable must stop and ask Chris when those conditions appear.

## Default PR Flow

The normal non-delegated long-run repo workflow is:

1. Codex/Fable completes one larger bounded repo-local packet.
2. Codex/Fable validates, commits, opens a PR, and includes a human-review
   excerpt.
3. Codex/Fable stops.
4. ChatGPT triages Claude Code audit need as `Required`, `Recommended`, or
   `Not needed`.
5. If audit is required or recommended, Claude Code audits the PR before human
   merge approval.
6. Chris reviews the PR and any audit report.
7. Chris approves, requests changes, or closes.
8. Codex/Fable merges and verifies only after explicit Chris approval.

If Claude Code audit is required or recommended, the PR must not be merged
until the Claude Code audit is complete and Chris has reviewed the audit
result, unless Chris has granted a current explicit delegated repo-merge
instruction for the audited PR loop and all delegated merge conditions pass.
Claude Code audit does not approve a merge by itself.

When Chris grants delegated repo-merge authority for a current long-run loop,
Codex/Fable may merge and verify a PR without asking for rubber-stamp merge
approval only when the work is repo-local, inert, deterministic, testable, and
inside the approved envelope; the PR is still at the audited head commit; the
PR is mergeable/clean; changed files have no unexpected drift; validation
passes; there is a clean worktree; Claude Code audit is absent by policy or
returns `Pass` or `Pass with notes` with no required fixes; and no unresolved
deviations, open questions, ambiguous authorization wording, or real human
gate remains. Delegated repo-merge authority is repo merge authority only and
does not mean product approval, Phase 14-C authorization, candidate approval,
candidate authorization, candidate activation or execution, live-service
access, live activation, credential handling, production DB activation,
scheduler/background activation, OpenClaw invocation, protected-path access,
dynamic cleaning implementation, Watch Tower adoption, `.agent/`,
`CLAUDE.md`, or runtime/operator scaffolding.

Codex/Fable PR-opening final reports must include:

```text
Claude Code audit recommendation:
Required / Recommended / Not needed
Reason:
...
```

If Codex/Fable says audit is not needed, it must explain why. If Codex/Fable
says audit is required or recommended, it must stop after opening the PR and
must not merge.

The report must include the reason. If the recommendation is `Not needed`, the
report must explain why the PR is narrow enough to skip Claude Code audit.

### Acceptable Larger Packets

Acceptable larger packets include:

- updating repo instructions plus docs plus matching documentation invariant
  tests
- folding checkpoint/status refreshes into the next substantive safe packet
- adding fake/local adapters with tests and safety docs
- completing a read-only or report-only surface with validation
- adding no-send preview behavior with fake adapters and inert fixtures
- preparing, validating, committing, pushing, and opening a PR for an approved
  repo-local docs/test packet

### Stop Condition Examples

Stop instead of continuing when a task would require:

- live Todoist, Gmail, or Calendar access or mutation
- credential setup, token inspection, OAuth troubleshooting, or secret
  handling
- production SQLite activation or production runtime state mutation
- access to `/Users/coldstake/PersonalOS` or `/Users/coldstake/.openclaw`
- OpenClaw invocation or runtime/operator handoff execution
- scheduler, LaunchAgent, crontab, daemon, watcher, service, or background
  loop activation
- a merge that is not covered by a current explicit delegated repo-merge
  instruction, even when tests pass and the PR is open
- product, safety, scope, or design judgment that cannot be resolved from
  repo-local evidence
- actual live-service testing, access, or writes

Long-run mode never authorizes live rails, credentials, production DB paths,
protected path access, scheduler/background activation, OpenClaw runtime,
external runtime writes, high-stakes execution, major product decisions, or
merges.

This workflow is not Watch Tower adoption. It does not authorize `.agent/`,
`CLAUDE.md`, runtime/operator scaffolding, OpenClaw invocation, live
Todoist/Gmail/Calendar access, credential handling, scheduler/background
activation, or any Watch Tower file adoption or merge.

The canonical packet rules live in
[AGENT_WORK_PACKET_PROTOCOL.md](AGENT_WORK_PACKET_PROTOCOL.md).

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
- commit hash or hashes
- PR number or URL if opened
- scope completed
- subphases completed
- files changed
- summary of changes
- validation commands and results
- test counts
- hygiene and artifact-scan results
- safety assertions
- deviations
- open questions
- next human decision required

Safety confirmation must state whether live rails, credentials, production DB,
scheduler/LaunchAgents/crontab/daemons, external writes, OpenClaw calls, and
protected runtime/personal paths were touched.

Every PR-opening final report must also include a Claude Code audit
recommendation of `Required`, `Recommended`, or `Not needed`, plus a reason.
For a `Not needed` recommendation, Codex/Fable must explain why the PR is
narrow enough to skip Claude Code audit.

For PR-opening packets, the final report should also include a short
human-review excerpt so Chris does not need a separate read-only extraction
packet just to understand the PR. The excerpt should include:

- what changed
- what files changed
- what safety boundaries remain true
- what approval or merge would mean
- what approval or merge would not mean
- anything Chris should double-check

## Phase Boundaries

Phase 13E-D is implemented and post-merge validated. Phase 13G is implemented
and post-merge validated as a planning/control-plane readiness matrix. Phase
14-A/B preparation may define a proposed pilot envelope and fail-closed
scaffolding only. Pre-Phase-14-C candidate-selection preparation may define an
inert selection process, blank template, and fail-closed validator only. Phase
14-C live pilot activation has not started. Docs, readiness reports,
checklists, pilot protocols, readiness matrices, and preparation artifacts do
not activate live rails by themselves.
