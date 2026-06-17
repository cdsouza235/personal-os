# Live Rail Activation Policy

## Purpose

This policy defines the activation requirements for live rails in Personal OS.
It is policy design plus the Phase 13F-B inert readiness model/tests. It does
not add live permission keys, implement live adapters, activate a scheduler,
activate production SQLite, call live APIs, load credentials, or authorize
OpenClaw runtime operation.

All live rails remain disabled until a later implementation phase adds the
rail, tests it, documents it, and Chris explicitly approves activation.
Phase 13F-B rail statuses are descriptive only; a disabled, blocked,
not-configured, or requires-approval status is not an activation path.

## Shared Activation Rules

Every live rail must satisfy the master
[Pre-Live Readiness Gate](PRE_LIVE_READINESS.md) before activation. No rail
can move from disabled or inert to live unless the readiness gate is satisfied,
the [Activation Checklist](ACTIVATION_CHECKLIST.md) is completed, the
[First-Live Pilot Protocol](FIRST_LIVE_PILOT_PROTOCOL.md) is completed, Chris
approves the specific pilot, and the first pilot receives post-pilot review
before expansion.

Shared rules:

- Default state: disabled.
- Permission behavior: fail closed when missing, disabled, invalid, unknown,
  approval-only, or not documented.
- Preview/dry-run: required before first live attempt.
- Idempotency: required before external mutation.
- Ledger: required before and during every live attempt.
- Completion report: required after every attempt, including blocked attempts.
- Rollback/undo: documented before activation.
- Approval: explicit Chris approval for the specific rail, operator, runtime
  host, permission, and pilot scope.
- Post-pilot review: required before expanding beyond the first approved
  pilot.

Dev/test, preview, simulated-write, and internal apply permissions do not
authorize live behavior.

## Rail Activation Matrix

| Rail | Default state | Required permission class | Preview/dry-run behavior | Idempotency behavior | Ledger behavior | Completion report | Rollback/undo expectation | Approval level |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Gmail send/draft | Disabled | Rail-specific Gmail live draft/send permission; not yet implemented | Generate no-send preview first; draft/send must be separately selected | Idempotency key from source item, recipient set, subject, body fingerprint, and operation | Intent before attempt; attempt row for blocked, draft, or send outcome | Must record no-send preview reference, Gmail operation, external message/draft ID when available, and send/draft status | Drafts may be deleted; sent email cannot be truly undone, so recovery is correction/escalation | Chris explicit per pilot; send requires stronger approval than draft |
| Todoist live write | Disabled | Rail-specific Todoist live write permission; not yet implemented | Validate task preview and dry-run ledger entry before live create/update | Idempotency key from source, target, operation, dedupe key, and task payload fingerprint | Intent before attempt; attempt row with Todoist object ID on success | Must record task ID, operation, risk, approval mode, duplicate outcome, and safety flags | Delete, close, reopen, annotate, or create corrective task as approved | Chris explicit per rail and first pilot |
| Google Calendar live write | Disabled | Rail-specific Calendar live write permission; not yet implemented | Validate event preview and dry-run ledger entry before live create/update | Idempotency key from source, calendar ID, time window, operation, dedupe key, and event payload fingerprint | Intent before attempt; attempt row with Calendar event ID on success | Must record event ID, calendar, time window, attendees if any, duplicate outcome, and safety flags | Delete/cancel/update event, or create corrective event as approved | Chris explicit; external-attendee events need separate approval |
| PersonalOS Markdown write | Disabled | Rail-specific PersonalOS Markdown write permission; not yet implemented | Render proposed markdown patch/export first; no direct write from preview | Idempotency key from source, target note label/path, operation, and content fingerprint | Intent before attempt; attempt row with file path label and content hash | Must record target label, operation, content hash, backup/reference, and safety flags | Prefer append-only or backup-backed restore; otherwise corrective edit | Chris explicit for target folder/file class |
| OpenClaw runtime workflow | Disabled | Narrow OpenClaw workflow permission plus approved handoff; not yet implemented in repo | Operator smoke must run with dry-run/no-send flags unless explicitly selected for live pilot | Workflow must consume existing ledger/idempotency records for every side effect | Workflow must write/read ledger records and preserve logs | Must record handoff reference, workflow ID/name, inputs, outputs, stop condition, and side effects | Stop workflow, preserve logs, undo downstream rail actions where possible | Chris explicit handoff for one workflow |
| Scheduler/LaunchAgent/background loop | Disabled | Scheduler activation permission plus OS-level approval; not yet implemented | Foreground/manual run first; launchd/crontab/daemon activation stays blocked | Each scheduled unit must use idempotency before side effects | Every run must write completion report and ledger attempts for side effects | Must record job, host, cadence, timezone, pid/job label when relevant, and disable path | Unload/disable job, stop process, and verify no further runs | Chris explicit for exact host/job/cadence |
| Live model/API call | Disabled | Rail-specific live model/API permission; not yet implemented | Fake/local model path first; live call requires bounded packet and redaction review | Idempotency/replay key from packet ID, model role, operation, and payload fingerprint where practical | Model run ledger must record provider/model metadata without secrets | Must record model role, provider/model, packet/output IDs, token/cost metadata if available, and safety flags | Cannot undo call; recovery is prevent retry, discard unsafe output, and escalate | Chris explicit for provider/model/use case |
| Production SQLite state | Disabled | Production DB activation permission plus approved DB path; not yet implemented | Migrate/operate on dev or restore-test copy first | DB writes must use transaction boundaries and duplicate prevention appropriate to module | System events, migration metadata, and side-effect ledgers where relevant | Must record DB path label, migration/version, backup, integrity check, and operation status | Restore from backup or roll forward according to approved plan | Chris explicit for path, migration, and operator |

## Gmail Activation Requirements

Gmail remains protected. A Gmail live rail must distinguish draft creation from
send. Send-enabled behavior requires explicit approval above draft-enabled
behavior because sent messages cannot be truly undone.

Before activation:

- No-send preview must exist.
- Recipients, subject, body, and attachments if any must be validated.
- High-stakes or person-to-person messages must require approval.
- Ledger and idempotency checks must happen before draft/send.
- Completion reports must not include credential material.

## Todoist Activation Requirements

Todoist is the action rail, not the brain. Live Todoist writes must come from
validated task candidates, not vague notes or raw emotional material.

Before activation:

- Task schema validation must pass.
- Risk and approval mode must be valid.
- Duplicate detection must be proven.
- Dry-run ledger evidence must exist.
- Live result must record the Todoist task ID or blocked/duplicate outcome.

## Google Calendar Activation Requirements

Calendar is for real time-bound blocks and commitments. Self-only blocks are
lower risk than events involving other people.

Before activation:

- Timezone-aware start/end validation must pass.
- Calendar ID must be explicit and approved.
- Attendee behavior must be documented.
- External-attendee events require separate approval.
- Rollback/cancel behavior must be documented before first write.

## PersonalOS Markdown Activation Requirements

PersonalOS Markdown writes are protected live filesystem writes. A renderer,
patch, or export preview is not a live write.

Before activation:

- Target file/folder class must be approved.
- The exact write mode must be documented: append, create, replace, or patch.
- Backup or recovery path must be documented.
- Content must avoid credentials and raw protected material.
- The rail must record content hashes and target labels in completion reports.

## OpenClaw Activation Requirements

OpenClaw is the runtime operator, not a repo implementation or review agent.
Any OpenClaw live workflow requires a handoff that satisfies
[Operator Handoff Contract](OPERATOR_HANDOFF_CONTRACT.md).

Before activation:

- Handoff must name exact actions and stop conditions.
- OpenClaw must not exceed allowed files/systems.
- Logs, ledgers, and completion reports must be preserved.
- OpenClaw must not merge PRs, validate tests, or approve live rails.

## Scheduler Activation Requirements

Scheduler activation includes LaunchAgents, crontab, daemons, background
workers, always-on loops, and any process that can run without an immediate
foreground command from Chris or the approved operator.

Before activation:

- The manual foreground run must pass.
- The global kill switch must be checked before every run.
- Disable/unload must be tested.
- Cadence and timezone must be explicit.
- The first pilot must be one narrow job.

## Live Model/API Activation Requirements

Live model/API calls include OpenAI, OpenRouter, Anthropic, market data,
fitness APIs, Google APIs, Todoist APIs, Gmail APIs, Calendar APIs, and any
other network provider.

Before activation:

- Prompt/input scope must be bounded.
- Protected files and credentials must be excluded.
- Provider/model must be approved.
- Cost and rate-limit handling must be documented.
- Output must remain non-executable until validated by downstream gates.

## Production SQLite Activation Requirements

Production SQLite state is governed by
[Production DB Policy](PRODUCTION_DB_POLICY.md). Production DB activation is
not implied by local/dev preview DB use.

Before activation:

- Production path must be explicitly approved.
- Backup and restore verification must pass.
- Migration checksum and integrity checks must pass.
- File permissions and locking/concurrency expectations must be documented.
- Repo-local runtime artifacts must remain prohibited.
