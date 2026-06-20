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

Claude Code may be used as an external auditor for larger work packets,
especially when a packet changes shared contracts, safety policy, migrations,
operator-facing surfaces, or a broad PR stack. Claude Code does not replace
Chris approval and does not operate live systems.

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

## Mandatory Stop Boundaries

Codex/Fable must stop and ask Chris before crossing any of these boundaries:

- live Gmail, Todoist, Google Calendar, or PersonalOS Markdown behavior
- credentials, secrets, OAuth files, API keys, tokens, or credential stores
- production SQLite paths, production ledgers, or production runtime state
- protected paths, including `/Users/coldstake/PersonalOS` and
  `/Users/coldstake/.openclaw`
- scheduler, LaunchAgent, crontab, daemon, or background-loop activation
- OpenClaw runtime operation or handoff execution
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

## Merge Rule

Codex/Fable may prepare branches, commits, PRs, PR stacks, validation evidence,
and final reports when approved. Codex/Fable must not merge without explicit
Chris approval for that merge.

External audit does not approve a merge. A green suite does not approve a
merge. A completed checklist, readiness matrix, or work packet report does not
approve a merge.

## External Audit Rule

Large packets require an explicit audit decision before merge. The decision may
be:

- Claude Code audit required
- ChatGPT audit sufficient
- Chris waives external audit for this packet

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
- work packet size and scope
- subphases completed
- files changed
- summary of implementation or documentation changes
- validation commands and results
- Unicode, bidi, or artifact-scan results when requested
- safety assertions covering live rails, credentials, production DB,
  scheduler/background work, OpenClaw, external writes, and protected paths
- deviations or unresolved questions
- next required human decision

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
