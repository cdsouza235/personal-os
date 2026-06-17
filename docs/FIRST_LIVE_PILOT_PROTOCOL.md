# First-Live Pilot Protocol

## Purpose

This protocol defines how the first Personal OS live pilot will eventually be
selected, rehearsed, approved, run, audited, and either halted or used as the
basis for later expansion.

Phase 13F-D only defines this protocol. It does not select a pilot, execute a
pilot, activate live rails, configure credentials, create production
databases, start schedulers, call live APIs, run OpenClaw, or approve Phase 14.

## Selection Criteria

A first-live pilot candidate must be:

- Low risk and reversible or recoverable.
- Single rail only.
- One-shot or a narrow bounded batch.
- Self-only unless Chris separately approves otherwise.
- Based on one approved input fixture or one approved real input.
- Supported by preview or dry-run evidence from the same input.
- Covered by deterministic idempotency and duplicate prevention.
- Recorded in a side-effect ledger before any live attempt.
- Covered by a completion report and rollback/undo plan.
- Small enough that Chris can inspect expected and actual output directly.

The pilot must not depend on background execution, broad folder scans,
unbounded inference, scheduler activation, or OpenClaw discretion.

## Recommended First Pilot Candidates

Preferred first pilot candidates are low-risk, self-only, and easy to undo or
discard:

- Self-only Todoist routine task creation from one validated task candidate.
- Self-only Calendar block creation with no external attendees and one
  approved calendar ID.
- Local no-send briefing export to an approved safe path, with no Gmail send
  and no production PersonalOS Markdown write unless backup/restore proof and
  explicit approval exist.

Gmail sending is not a preferred first pilot. Gmail draft creation or sending
must be treated as higher risk, requires stronger approval, and should not be
selected first while lower-risk reversible rails remain available.

## Excluded First Pilots

The first live pilot must not be any of the following:

- Relationship messages.
- Tax, legal, or estate messages or tasks.
- Investment, crypto, trading, or financial execution.
- Health or medical decisions.
- External calendar events with other people.
- Gmail sending to other people.
- Production PersonalOS Markdown writes without backup and restore proof.
- Scheduler, LaunchAgent, crontab, daemon, or background loop activation.
- Multi-rail automation.
- Live model/API calls that can trigger downstream side effects.
- Broad ingestion, broad search, or unbounded operation over protected files.

## Single-Rail Principle

The first pilot may use exactly one live rail. Supporting preview, validation,
ledger, and report code may run, but only the selected rail may perform a live
side effect.

Non-selected rails must remain disabled and must not load credentials, create
clients, create production state, or perform live writes.

## One-Shot Or Narrow-Batch Principle

The first pilot should be one live operation. If a narrow batch is approved, it
must have:

- A fixed maximum item count.
- A reviewed item list before execution.
- A stop-on-first-error rule.
- A duplicate-prevention check per item.
- A completion report that lists every item outcome.

Open-ended loops, recurring jobs, and opportunistic extra work are not allowed.

## No Background Daemon

The first pilot must run from an explicit foreground command or approved
manual operator action. It must not use a daemon, LaunchAgent, crontab,
scheduler, always-on loop, watch process, or background worker.

## Scheduler Approval Boundary

No scheduler may be activated during the first pilot unless scheduler
activation itself is the separately approved selected rail. Even then, the
pilot must be one narrow foreground-validated scheduler activation with a
tested disable/unload path.

The default first pilot should avoid scheduler activation entirely.

## Dry-Run Rehearsal

Before the live run, the operator must produce a dry-run or preview rehearsal
from the exact candidate input. The rehearsal must show:

- Input reference.
- Selected rail and operation.
- Normalized payload.
- Validation result.
- Permission result.
- Idempotency key and payload fingerprint.
- Ledger intent that would be used or proof that the dry-run did not mutate.
- Expected completion report fields.
- Rollback or undo plan.
- Confirmation of no external write.

If the live input differs from the rehearsed input, the rehearsal is stale and
must be repeated.

## Required Preview Artifact

The preview artifact must be reviewable by Chris before approval. It must
include the final candidate payload, target surface label, risk level,
approval mode, expected side effect, duplicate-prevention result, and safety
flags.

For message-like or note-like output, the preview must show the exact content
or a clearly redacted representation approved by Chris.

## Required Approval Artifact

The approval artifact must name:

- Chris as approver.
- Selected rail.
- Exact operation.
- Operator.
- Runtime host.
- Repo commit.
- Input reference.
- Preview/dry-run artifact.
- Credential label if any.
- Production DB path label if any.
- Permission names.
- Stop condition.
- Rollback/undo plan.
- Post-run audit requirement.

Approval for development, PR merge, tests, a previous dry-run, or a different
rail does not approve the first live pilot.

## Required Operator Handoff Packet

If OpenClaw or any runtime operator is involved, the handoff packet must
satisfy [Operator Handoff Contract](OPERATOR_HANDOFF_CONTRACT.md) and include:

- Objective.
- Allowed files and systems.
- Forbidden files and systems.
- Exact commands or workflow names.
- Mode for each action.
- Required permissions.
- Expected inputs.
- Expected outputs.
- Credential boundary.
- Production DB boundary.
- Logs, ledgers, and completion report target.
- Stop condition.
- Rollback/undo instructions.
- Escalation instructions.

Phase 13F-D does not invoke OpenClaw. A future handoff packet is only an input
to a later explicit runtime/operator approval.

## Required Completion Report

Every pilot attempt, including blocked or failed attempts, must produce a
completion report with:

- Operator.
- Runtime host.
- Repo commit.
- Selected rail and operation.
- Approval artifact reference.
- Input reference.
- Preview/dry-run artifact reference.
- Permission checks.
- Idempotency key and payload fingerprint.
- Ledger IDs.
- Started and completed timestamps.
- Outcome.
- External object ID if a live object was created.
- Safety flags.
- Rollback or undo status.
- Errors, anomalies, and escalation notes.

Reports must not include secrets, raw credentials, OAuth tokens, or broad
unredacted protected content.

## Required Ledger Entry

A side-effect ledger intent must exist before the live attempt. The ledger
entry must include target system, operation, approval reference, risk level,
approval mode, idempotency key, payload fingerprint, validation result,
planned status, attempt status, and final outcome.

The live side effect must not happen first with the ledger filled in later.

## Required Rollback Or Undo Plan

The pilot packet must state how to undo or recover from the live side effect:

- Todoist: delete, close, reopen, annotate, or create a corrective task.
- Calendar: delete, cancel, update, or create a corrective event.
- Local no-send export: delete or move the generated export if approved.
- Gmail draft: delete draft if approved.
- Gmail send: cannot truly be undone; recovery is correction and escalation.
- PersonalOS Markdown write: restore from backup or apply a corrective edit.
- Production SQLite: restore from backup or roll forward under the approved
  production DB policy.

If undo is impossible, the approval artifact must say so explicitly before the
pilot can proceed.

## Required Post-Run Audit

After the pilot, Chris or the approved reviewer must inspect:

- Completion report.
- Ledger record and status.
- External object, if any.
- Rollback/undo evidence, if used.
- Safety flags.
- Unexpected side effects.
- Credential and protected-path boundaries.
- Whether non-selected rails stayed disabled.
- Whether production DB and scheduler boundaries stayed intact.
- Whether the stop condition was honored.

No expansion may happen until the post-run audit is complete.

## Expansion Criteria

Expansion beyond the first pilot may be considered only when:

- The pilot completed inside its approved scope.
- No unexpected live side effects occurred.
- The ledger and completion report are complete.
- Duplicate prevention behaved as designed.
- Rollback or recovery was verified where applicable.
- Non-selected rails remained disabled.
- Credentials, production DB, scheduler, and OpenClaw boundaries were honored.
- Chris approves the next specific expansion.

Expansion must still be incremental: one rail or one narrow capability at a
time.

## Halt Criteria

Live expansion must halt when any of these occur:

- Permission, credential, production DB, scheduler, or OpenClaw ambiguity.
- Missing or stale approval.
- Missing preview, ledger, completion report, or rollback evidence.
- Unexpected external side effect.
- Duplicate prevention failure.
- Kill switch failure.
- Scheduler/background behavior appears without approval.
- Protected path access outside the approval packet.
- Any high-risk candidate is proposed without separate explicit approval.
- Chris requests a pause or review.

When halted, the operator must preserve evidence, avoid retries, and escalate
with the completion report and concise decision needed.
