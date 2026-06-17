# Operator Handoff Contract

## Purpose

This contract defines the boundary between ChatGPT, Codex/Fable, OpenClaw, and
Chris when work moves from repository development or planning toward runtime
operation. It is documentation and policy design only. It does not authorize
OpenClaw to run live workflows.

## Role Boundaries

Chris is the owner and final approver. Chris decides whether a live operation,
operator smoke test, production DB action, scheduler activation, or external
rail action is allowed.

ChatGPT is the synthesis, planning, architecture, and audit layer. ChatGPT may
draft objectives, handoff text, acceptance criteria, and review questions. It
does not mutate the repo or operate live systems.

Codex and Fable are repository development agents. They may edit repository
documentation, source, and tests only within approved phase gates. They may
open PRs and report validation results when approved. They are not production
runtime operators.

OpenClaw is the local runtime operator only when Chris explicitly selects it
for a narrow runtime/operator task. OpenClaw runs approved local workflows,
records approved runtime outputs, and interacts with live rails only through
validated modules and explicit handoffs.

## Default Boundary

OpenClaw should not perform repo implementation, PR review, merge, test
validation, or live rail activation unless Chris explicitly selects it for a
narrow runtime/operator smoke test. Even then, OpenClaw may operate only the
runtime surface named in the handoff.

OpenClaw must not infer permission from a merged PR, a docs update, a roadmap
entry, a Codex summary, or a prior approval for a different task.

## Approved Handoff Contents

An approved OpenClaw handoff must contain:

- Objective.
- Operator.
- Runtime host.
- Allowed files and systems.
- Forbidden files and systems.
- Exact actions.
- Required permissions.
- Expected inputs.
- Expected outputs.
- Safety constraints.
- Credential boundary.
- Production DB boundary.
- Logs, ledgers, and completion reports.
- Stop condition.
- Rollback or undo instructions.
- Escalation instructions.
- Approval reference.

If any required field is missing or ambiguous, OpenClaw must stop and escalate
instead of guessing.

## Objective

The objective must be a concrete runtime outcome, not a broad product goal.

Acceptable objective style:

- Run one no-send operator smoke test for the scheduler preview command on a
  temp/dev DB.
- Create one Todoist dry-run ledger record from an approved fixture.
- Verify that a LaunchAgent is not installed.

Unacceptable objective style:

- Implement Phase 14.
- Make live rails work.
- Operate Personal OS.
- Fix whatever fails.

## Allowed Files And Systems

The handoff must name allowed files and systems by exact path or approved
label. It must also name protected systems that remain off limits.

Protected by default:

- `/Users/coldstake/PersonalOS`
- `/Users/coldstake/.openclaw`
- LaunchAgents
- Credentials and OAuth material
- Production SQLite state
- Production ledgers
- Gmail
- Todoist
- Google Calendar
- PersonalOS Markdown files
- Live model/API providers

Access to one protected surface does not imply access to any other protected
surface.

## Exact Actions

The handoff must list the exact commands, workflow names, or manual actions
OpenClaw may perform. Open-ended exploration is not allowed for runtime
handoffs.

Each action must identify whether it is:

- Read-only.
- Preview.
- Dry-run.
- Simulated write.
- Internal apply.
- Live write.

If a handoff does not explicitly say live write, OpenClaw must treat it as
not live.

## Permissions

The handoff must name every permission expected to be enabled. Dev/test
permissions do not authorize live systems. Preview, dry-run, simulated-write,
and internal apply permissions do not authorize external writes.

OpenClaw must stop if:

- A required permission is missing.
- A permission is disabled.
- A permission is invalid.
- A permission is approval-only but no current approval is provided.
- A permission name is unknown to the active implementation.

## Inputs And Outputs

Inputs must be explicit and bounded:

- Input file path or approved input label.
- Source record ID.
- Date/timezone.
- Rail-specific target.
- Approval artifact.

Outputs must be explicit:

- Completion report path or DB record.
- Ledger record IDs.
- External object IDs if a live rail is approved.
- Logs to preserve.
- Human-readable summary for Chris.

OpenClaw must not search broad folders, inspect raw notes, or use arbitrary
files as implicit input.

## Safety Constraints

Every handoff must restate the relevant safety constraints:

- No credentials printed.
- No protected path access unless named.
- No production DB mutation unless named.
- No live external write unless named.
- No scheduler activation unless named.
- No background loop unless named.
- No high-stakes action unless explicitly approved.
- No messages to other people unless explicitly approved.
- Stop on ambiguity.

## Logs, Ledgers, And Completion Reports

For every operator task, OpenClaw must preserve evidence appropriate to the
risk level:

- Command or workflow run ID.
- Started/completed timestamps.
- Input reference.
- Permission checks.
- Ledger IDs where applicable.
- Completion report.
- Safety flags.
- Error output.
- Rollback/undo result where applicable.

Reports must not include secrets, raw credentials, OAuth tokens, or broad
unredacted protected content.

## Stop Condition

The handoff must define when OpenClaw stops. Stop conditions may include:

- First successful preview.
- First blocked safety check.
- First failed permission check.
- First live write attempt.
- Completion report written.
- Any unexpected path, credential, or production-state request.

If the stop condition is reached, OpenClaw must stop even if additional work
seems useful.

## Rollback And Escalation

Rollback instructions must state what can be undone and what cannot.

Escalation is required when:

- A permission is missing or ambiguous.
- A protected path is needed but not approved.
- A credential is missing or invalid.
- A live write partially succeeds.
- A scheduler/background process cannot be stopped.
- A production DB integrity check fails.
- Completion report evidence is incomplete.

Escalation goes to Chris with the completion report, logs, and a concise
statement of the decision needed.

## Handoff Template

```text
Objective:
Operator:
Runtime host:
Approval reference:

Allowed files/systems:
Forbidden files/systems:

Exact actions:
Mode for each action:
Required permissions:

Expected inputs:
Expected outputs:

Safety constraints:
Credential boundary:
Production DB boundary:

Logs/ledgers/completion reports:
Stop condition:
Rollback/undo instructions:
Escalation instructions:
```
