# Agent Work Packet Protocol

Protocol version: v1

## Purpose

This protocol defines how Personal OS uses bounded work packets for ChatGPT,
Codex/Fable, Claude Code, and OpenClaw coordination.

It allows longer Codex/Fable repo-development runs across multiple approved
inert subphases while preserving the hard safety gates that protect live rails,
credentials, production state, protected paths, and human decision authority.

This protocol does not start Phase 14, authorize live rails, authorize
credentials/OAuth work, activate production SQLite, activate schedulers, call
OpenClaw, call live model/API providers, inspect protected paths, or perform
external runtime writes.

This protocol is not Watch Tower adoption. It does not authorize `.agent/`,
`CLAUDE.md`, runtime/operator scaffolding, OpenClaw invocation, live
Todoist/Gmail/Calendar access, credential handling, scheduler/background
activation, or Watch Tower file adoption or merge.

## Actor Roles

### Chris

Chris is the owner, final approver, and source of judgment. Chris approves
product direction, live rails, credential use, production DB use, protected
path access, scheduler/background activation, OpenClaw runtime handoffs,
high-stakes execution, major product decisions, PR merges, and any exception
to a normal stop boundary.

### ChatGPT

ChatGPT is the strategy, synthesis, instruction-writing, architecture, and
audit layer. ChatGPT may define work packets, acceptance criteria, review
questions, and audit prompts. ChatGPT does not operate live systems.

### Codex/Fable

Codex/Fable is the repository implementation layer. Codex/Fable may work
inside approved repo-local branches on docs, tests, migrations, fixtures,
fake/local adapters, inert evaluators, read-only/report-only surfaces, and
safe dev/test workflows.

When long-run mode is approved, Codex/Fable may continue across multiple
approved inert subphases until the packet is complete, the PR or PR stack is
ready, a mandatory stop boundary is reached, or validation fails in a way that
requires human judgment.

### Claude Code

Claude Code may be used as an external auditor for PRs that need an
independent repo review before merge. Claude Code fits between Codex/Fable PR
opening and Chris merge approval. Claude Code does not replace Chris approval
and does not operate live systems.

### OpenClaw

OpenClaw is the future runtime/operator layer only after explicit Chris
approval and an approved operator handoff. OpenClaw is not the repo
implementation, PR review, merge, or validation layer unless Chris explicitly
approves a narrow runtime/operator task.

## Work Packet Sizes

### Small Packet

A small packet is one tightly scoped repo task, usually one doc update, one
test-only adjustment, one small code fix, or one narrow validation pass. It
normally ends with one commit or one PR update.

### Medium Packet

A medium packet spans several related files or substeps inside one approved
inert envelope. It may include docs plus tests, a small local-only feature
slice, or a focused safety/readiness improvement. It should still fit in one
PR unless Chris approves a PR stack.

### Large Packet

A large packet spans multiple approved inert subphases, broad documentation
alignment, shared contracts, migrations, or several repo-local modules. A large
packet may produce a PR stack when that is clearer than one PR. Large packets
need explicit scope, stop boundaries, validation expectations, and an audit
decision before merge.

## When Long-Run Codex/Fable Work Is Allowed

Long-run Codex/Fable work is allowed only when Chris or the current prompt
authorizes a bounded packet and the work stays inside the approved envelope.

Allowed long-run envelopes include:

- repo-local documentation and control-plane updates
- repo-local tests
- fake/local adapters
- inert evaluators
- read-only or report-only surfaces
- no-send workflows
- preview or dry-run behavior
- simulated writes using fake adapters
- local dev/test SQLite with explicit safe paths
- branch, commit, PR, and validation work

Long-run mode is not permission to cross a safety boundary. It is permission
to keep working through approved inert substeps without stopping after every
small milestone.

Examples of acceptable larger packets include repo instruction updates plus
documentation invariant tests, fake/local adapter work with inert fixtures,
read-only or report-only surface improvements, no-send preview behavior,
validation cleanup, folding checkpoint/status refreshes into the next
substantive safe packet, and preparing, validating, committing, pushing, and
opening a PR for an approved repo-local docs/test packet.

## Checkpoint Refresh Rule

Post-merge verification is normally sufficient. Codex/Fable must not create a
standalone checkpoint/status refresh PR after every merge by default. A separate
checkpoint/status refresh PR is allowed only when:

- stale status docs would materially mislead the next work packet
- stale checkpoint docs would block safe validation or handoff
- the repo is being left at a longer-term stopping point
- Chris explicitly asks for a checkpoint refresh
- a safety, audit, or governance change requires a canonical checkpoint before
  further work

Otherwise, fold checkpoint/status refreshes into the next substantive safe
repo-local packet.

Codex/Fable should prefer larger bounded packets that combine adjacent safe
work, such as checkpoint refresh, docs discoverability updates, invariant test
hardening, small consistency fixes, audit follow-up nits, and
validation/reporting updates. Do not stop after every small milestone unless a
real gate is reached.

## Mandatory Stop Boundaries

Codex/Fable must stop and ask Chris before crossing any of these boundaries:

- live Gmail, Todoist, Google Calendar, or PersonalOS Markdown behavior
- credentials, secrets, OAuth files, API keys, tokens, or credential stores
- production SQLite paths, production ledgers, or production runtime state
- protected paths, including `/Users/coldstake/PersonalOS` and
  `/Users/coldstake/.openclaw`
- scheduler, background, LaunchAgent, crontab, daemon, watcher, or service
  activation
- OpenClaw runtime handoff or invocation
- external runtime writes or live external runtime services
- live model/API providers
- high-stakes execution involving legal, tax, medical, health, investment,
  portfolio, crypto, relationship, external-message, external-meeting, family,
  or large-financial-commitment decisions
- major product direction decisions that change phase goals or safety posture
- merge approval
- any scope ambiguity that could weaken safety rules

Validation failures that require judgment are also stop boundaries. Examples
include safety-regression test failures, unexpected runtime artifact creation,
credential/protected-path ambiguity, live-service contact, or an unclear PR
scope change.

## Real Human Gates

A real human gate is a decision that changes authorization, safety posture, or
product direction. Real gates include live Gmail/Todoist/Calendar writes,
credential/API/OAuth/secrets/token handling, production DB activation,
protected path access, OpenClaw runtime handoff or invocation,
scheduler/background/LaunchAgent/crontab/daemon/watcher/service activation,
high-stakes execution, major product direction choices, merge approval, and
test failures that require architectural or product judgment.

Real gates also include human merge approval, required Claude Code audit, live
activation, Phase 14-C authorization, candidate approval, candidate
authorization, candidate activation or execution, external-service access or
writes, credentials/auth handling, production DB activation,
scheduler/background activation, OpenClaw invocation, protected path access,
live model/API calls, dynamic cleaning implementation, high-stakes execution
boundaries, and test failures requiring architectural, product, safety, or
workflow judgment.

Local branch creation, repo-local edits, inert tests, validation runs, commits,
PR body drafting, and PR opening are not separate human gates when they are
already inside an approved repo-local inert packet.

## Merge Rule

Codex/Fable may prepare branches, commits, PRs, PR stacks, validation evidence,
and final reports when approved. Codex/Fable must not merge without explicit
Chris approval for that merge.

Claude Code audit does not approve a merge. ChatGPT audit does not approve a
merge. A green suite does not approve a merge. A completed checklist,
readiness matrix, or work packet report does not approve a merge.

## Claude Code Audit Triage

Every PR-opening Codex/Fable final report must include:

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

ChatGPT triages the Claude Code audit need after Codex/Fable opens the PR. The
triage categories are:

- `Required`
- `Recommended`
- `Not needed`

If Claude Code audit is required or recommended, the PR must not be merged
until Claude Code audit is complete and Chris has reviewed the audit result.

### Claude Code Audit Required Before Merge

Claude Code audit should be required before merge for PRs that affect:

- safety policy
- readiness posture
- live rails
- Phase 14 or future live-pilot preparation
- candidate selection or candidate tracking
- Todoist/Gmail/Calendar boundaries
- OpenClaw boundaries
- credential, secret, OAuth, API-key, or token boundaries
- production DB paths
- protected paths
- scheduler, background, LaunchAgent, crontab, daemon, watcher, or service
  boundaries
- live model/API-call boundaries
- agent workflow, Codex workflow, ChatGPT workflow, or repo governance
- broad architecture or runtime boundaries
- high-stakes execution boundaries involving tax, legal/estate,
  portfolio/crypto, health/medical, relationship, or external-message
  workflows
- test failures requiring architectural or product judgment
- authorization wording that could be misread as approval, activation, or live
  execution

### Claude Code Audit Recommended

Claude Code audit should be recommended, but not automatically required, for:

- medium-sized docs/test PRs with safety-adjacent wording
- new tests that enforce safety or workflow invariants
- broad documentation reorganizations
- non-runtime refactors that touch multiple policy docs
- PRs where Chris wants an independent check before merge

### Claude Code Audit Usually Not Needed

Claude Code audit may be skipped for:

- typo fixes
- formatting-only changes
- narrow checkpoint/status refreshes that satisfy the checkpoint refresh rule
  after already-audited work
- small docs-only updates that do not affect safety, authorization, runtime
  behavior, or agent workflow
- mechanical line, hash, or status updates with clean Codex/Fable validation
  and a clear human-review excerpt

### Read-Only Audit Boundary

Claude Code audits are read-only by default:

- no file modifications
- no commits
- no pushes
- no PR approval, close, or merge
- no live services
- no credentials, secrets, OAuth files, API keys, or token handling
- no OpenClaw invocation
- no protected path access

### Examples

Required: a docs/test PR that changes agent workflow, Codex workflow, ChatGPT
workflow, safety policy, live-rail boundaries, readiness posture, candidate
tracking, or pre-merge audit routing.

Recommended: a medium-sized docs/test PR that adds safety-adjacent invariant
tests or reorganizes multiple control-plane docs without changing
authorization.

Not needed: a typo-only PR, formatting-only PR, narrow post-merge status refresh
that satisfies the checkpoint refresh rule after already-audited work, or
mechanical hash/status update that does not affect safety, authorization,
runtime behavior, or agent workflow.

Claude Code audits are repo/PR audits only unless Chris explicitly approves a
different narrow scope. Claude Code must not inspect protected paths, load
credentials, operate live rails, call OpenClaw, activate production DB paths,
or perform external runtime writes.

## Running Implementation Log

During medium and large packets, Codex/Fable should keep a running
implementation log in status updates, PR notes, a packet document, or the final
report. The log should track:

- approved packet scope
- subphases completed
- files changed
- validation run
- deviations from the packet
- open decisions
- safety assertions

The log is evidence for review. It is not approval to continue past a mandatory
stop boundary.

## Final Report Format

Final reports for work packets must include:

- branch name
- PR number or link, if opened
- commit hash or hashes
- work packet size
- scope completed
- subphases completed
- files changed
- summary of implementation or documentation changes
- validation commands and results
- test counts
- Unicode, bidi, or artifact-scan results when requested
- safety assertions covering live rails, credentials, production DB,
  scheduler/background work, OpenClaw, external writes, and protected paths
- deviations
- open questions
- Claude Code audit recommendation: `Required`, `Recommended`, or
  `Not needed`
- reason for the Claude Code audit recommendation
- next required human decision

For PR-opening packets, final reports should include a short human-review
excerpt so Chris does not need a separate read-only extraction packet just to
understand the PR. The excerpt should include:

- what changed
- what files changed
- what safety boundaries remain true
- what approval or merge would mean
- what approval or merge would not mean
- anything Chris should double-check

## Conflict Rule

Prompts may narrow safety rules, add additional stop conditions, or require
extra validation. Prompts may not weaken `SAFETY_POLICY.md`, `AGENTS.md`, this
protocol, `CODEX_WORKFLOW.md`, or explicit Chris safety boundaries.

When instructions conflict, fail closed and ask Chris. Do not infer permission
from silence, prior phases, prior PRs, merged docs, test success, or an
external audit.

## Source-Of-Truth Priority

For work-packet scope and safety interpretation, use this priority order:

1. `docs/SAFETY_POLICY.md`
2. `AGENTS.md`
3. `docs/AGENT_WORK_PACKET_PROTOCOL.md`
4. `docs/CODEX_WORKFLOW.md`
5. `STATUS.md`
6. `docs/ROADMAP.md` and `docs/PRD.md`
7. current prompt

The current prompt may narrow or specialize the higher-priority rules for the
current task, but it may not weaken them. If a prompt appears to authorize a
weaker safety posture, Codex/Fable must stop and ask Chris.
