# Pre-Live Readiness Gate

## Purpose

Phase 13F-A defines the mandatory readiness gate before any Phase 14 or live
rail work. Phase 13F-B encodes that policy as inert repo-level readiness
structures and tests. Phase 13F-D adds the future
[Activation Checklist](ACTIVATION_CHECKLIST.md) and
[First-Live Pilot Protocol](FIRST_LIVE_PILOT_PROTOCOL.md). These documents do
not implement live rails, add migrations, activate a scheduler, activate a
production database, call live APIs, load credentials, or authorize OpenClaw
runtime operation.

No live rail may move from preview/dry-run behavior to live behavior until
Chris explicitly approves the specific rail, specific production surface,
specific operator, and specific first-live pilot. Before Phase 14 or any live
activation, the activation checklist and first-live pilot protocol must be
completed as future human approval artifacts.

## Scope

This gate applies before any live behavior for:

- Gmail send or draft creation.
- Todoist task creation or mutation.
- Google Calendar event creation or mutation.
- PersonalOS Markdown writes.
- OpenClaw runtime workflows.
- Scheduler, LaunchAgent, daemon, crontab, or background loop activation.
- Live model/API calls.
- Production SQLite state.

## Default State

All live permissions are disabled by default. Missing, disabled, invalid,
unknown, approval-only, or undocumented permissions must fail closed. A
dev/test permission, simulated-write permission, preview permission, dry-run
permission, or internal SQLite apply permission must never be interpreted as a
live permission.

No new live permission exists until a later implementation phase adds it in
source code, tests it, documents it, and Chris approves it by name.

Phase 13F-B adds only an inert readiness evaluator. The evaluator may return
machine-readable gate and rail status, but it must not contact external
services, load credentials, create runtime files, mutate production state,
activate schedulers, or call OpenClaw.

Phase 13F-C exposes that evaluator through local read-only status surfaces.
The CLI/status/dashboard report is informational only. It may show readiness
status, gate results, live rail statuses, and missing or blocked reasons, but
it must not turn a ready, not-ready, or blocked report into live activation.

Phase 13E-A adds a unified operator status report shape on top of the same
inert readiness evaluator. The report is for human review and JSON audit
copy/paste only. It summarizes the current mode, safe local actions, blocked
live actions, and evidence fields such as `inert_report_only=true`,
`live_rails_activated=false`, `readiness_status=not_ready`, no credentials
loaded/read, inactive scheduler, inactive production DB, and no external
writes. It does not inspect credentials, initialize external clients, activate
schedulers, create production databases, call OpenClaw, or start Phase 14.

Phase 13E-B improves CLI discovery and completion summaries for the same
inert/no-send workflows. `personalos workflows` lists safe local commands and
blocked live actions without opening a DB. Existing no-send command summaries
must make local SQLite reads, local SQLite changes, output targets,
credentials, external writes, and blocked live actions explicit while
preserving the `operator_status.v1` vocabulary.

Phase 13E-C improves dashboard/status visibility for the same posture. The
dashboard and static dashboard render show NOT READY, inert/no-send/report-only
mode, live rails disabled, external writes as none, safe local actions,
blocked live actions, and inert evidence from `operator_status_summary`.
These panels are informational only; no dashboard control activates live
rails, loads credentials, starts a scheduler, switches to production SQLite,
calls OpenClaw, or writes externally.

## Terminology

- Preview: validates and reports what would happen without mutating state or
  calling an adapter.
- Dry-run: records local dev/test evidence about an intended side effect, but
  does not perform the side effect.
- Simulated write: uses fake/recording adapters only and may update local
  dev/test rows with fake IDs.
- Internal apply: mutates approved internal SQLite state only, such as
  priorities, projects, or followups, and does not touch external systems.
- Live write: mutates Gmail, Todoist, Google Calendar, PersonalOS Markdown,
  OpenClaw runtime state, production SQLite, a live scheduler, a live model/API
  provider, or any other production runtime system.

Only live write behavior requires the pre-live gate to pass. Preview, dry-run,
simulated write, and internal apply behavior remain governed by their existing
phase-specific dev/test policies.

## Operator Status Reports

`personalos readiness status` prints a no-DB, no-write readiness and operator
status report. `personalos readiness status --json` emits the same data as
stable JSON for ChatGPT audit.

`personalos workflows` prints a no-DB, no-write catalog of safe local
workflows and blocked live actions. `personalos workflows --json` emits the
same command inventory, safe local workflow list, blocked action list, and
operator status evidence as JSON for ChatGPT audit.

`personalos status --db <safe_temp_or_repo_dev_db>` reads an explicit
validated local SQLite database and includes the same operator status model in
the status summary. `personalos status --db <safe_db> --json` is the preferred
copy/paste form when ChatGPT needs machine-readable evidence.

`personalos dashboard render --db <safe_db> --output-file <safe_html_file>`
writes a static dashboard HTML file to an explicit safe path. It includes the
same `operator_status_summary` safe local actions, blocked actions, and
evidence in dashboard form, and `today.json` exposes the underlying JSON for
audit. Rendering does not bind a server, activate a scheduler, load
credentials, use production SQLite, or perform external writes.

`not_ready` means Personal OS is not approved for live operation. In the
current baseline, `not_ready` is expected because the Phase 14/live approval
markers, selected pilot scope, production DB approval, kill switch evidence,
and other pre-live gates have not all been satisfied.

`inert_report_only` means the report is informational. It may read local
dev/test SQLite state when an explicit safe `--db` is supplied, but it must not
send Gmail, write Todoist or Google Calendar, write PersonalOS Markdown, load
credentials, activate a scheduler, use production SQLite, call live model/API
providers, or call OpenClaw.

Currently allowed safe local actions are readiness reports, local status
inspection, ChatGPT synthesis import previews, explicitly approved synthesis
apply into local SQLite state only, no-send briefing previews,
side-effect/idempotency ledger inspection, and simulated scheduler previews.
The CLI workflow catalog maps these actions to the concrete commands and
output locations a human operator can run locally.

Blocked actions remain Gmail send/draft, Todoist writes, Google Calendar
writes, PersonalOS Markdown writes, credential loading, scheduler/LaunchAgent/
crontab/daemon/background activation, production DB use, live model/API calls,
and OpenClaw runtime calls.

## Credential Boundary

Credentials, OAuth tokens, API keys, refresh tokens, service account material,
browser sessions, keychains, and provider-specific auth files remain protected
runtime assets. Codex and Fable may not inspect, print, copy, modify, rotate,
or validate credentials unless a future policy explicitly approves a narrow
credential-read or credential-validation task.

Any live rail that needs credentials must document:

- Credential owner.
- Credential storage location by label, not by printing secret contents.
- Read-only versus write-capable scopes.
- Token rotation and revocation path.
- Operator allowed to use the credential.
- Confirmation that repository files do not contain the secret.

## Production DB Approval

Production SQLite activation requires a separate explicit approval under
[Production DB Policy](PRODUCTION_DB_POLICY.md). Approval must name the
production DB path, runtime host, owner, backup location, migration plan,
restore verification method, and rollback condition.

Dev/test/local preview DB approval does not authorize production DB use.
Repo-local runtime artifacts remain prohibited.

## Migration Workflow

Before production migration:

- The target DB path must be explicitly approved.
- The exact repo commit and migration set must be identified.
- Checksums for already-applied migrations must be verified.
- A backup must be created before migration.
- Restore verification must be performed on a copy before live migration.
- A rollback plan must exist before mutation.
- A completion report must be written after the migration attempt.

No migration may be applied to production SQLite from an implicit path, a
repo-local `var/` path, an unreviewed script, or an operator guess.

## Backup And Restore Verification

Backups are not sufficient until restore has been verified. Before a first
production activation, the operator must prove that a backup can be restored
into a separate safe location and passes integrity checks.

The evidence must include:

- Source DB path label and hash or size/timestamp metadata.
- Backup path label.
- Restore test path.
- `PRAGMA integrity_check` result.
- Migration metadata consistency result.
- Table/count sanity checks.
- Confirmation that the restore test did not touch production state.

## Idempotency

Every live write rail must have deterministic idempotency before activation.
The idempotency design must state:

- The idempotency key source fields.
- Payload fingerprint behavior.
- Duplicate detection behavior.
- Retry behavior after partial failure.
- Collision posture for live rails.
- Whether full digest material is stored for live writes.
- How stale or superseded intents are handled.

Current dev/test ledger keys are not automatically approved for live rails.
The live collision posture must be decided before any external write is
enabled.

## Side-Effect Ledgers

Every live side effect must be represented in a side-effect ledger before it
is attempted. The ledger record must include target system, operation, risk,
approval mode, idempotency key, payload fingerprint, validation report, run
status, and final outcome.

Live rails must never mutate an external system first and backfill the ledger
later. The ledger is the evidence layer for retries, duplicate prevention,
audits, rollback planning, and incident review.

## Completion Reports

Every live attempt must produce a completion report that includes:

- Operator.
- Repo commit or runtime version.
- Target rail and operation.
- Input reference and approval reference.
- Permissions checked.
- Idempotency key and ledger IDs.
- Preview/dry-run evidence reference.
- Started and completed timestamps.
- Outcome status.
- External object IDs when relevant.
- Safety flags.
- Rollback or undo status.
- Errors and escalation notes.

Reports must avoid secret values and must not include raw credential material.

## Rollback And Recovery

Every live rail must define rollback or recovery before activation:

- Gmail: whether drafts can be deleted, sent email cannot be unsent, and
  recovery is correction/escalation.
- Todoist: whether tasks can be deleted, closed, reverted, or annotated.
- Google Calendar: whether events can be deleted, canceled, or restored.
- PersonalOS Markdown: whether writes are append-only, reversible from backup,
  or repaired by a follow-up edit.
- OpenClaw runtime workflows: how to stop the workflow and preserve logs.
- Scheduler activation: how to unload, disable, or stop the job.
- Production SQLite: how to restore from backup or roll forward.
- Live model/API calls: how to prevent repeated calls and preserve request
  metadata without exposing secrets.

If rollback cannot truly undo the action, the policy must say so explicitly
before approval.

## Global Kill Switch

Before live activation, the system must define a global kill switch that stops
all live rails. The kill switch must fail closed and be easy for Chris or the
approved operator to verify.

The kill switch policy must cover:

- Where the disabled state lives.
- Which rails it disables.
- Whether scheduler/background loops check it before every run.
- Whether live model/API calls check it before every call.
- What completion report is produced when the kill switch blocks work.
- How activation is restored after Chris approval.

## Scheduler Activation

Scheduler, LaunchAgent, crontab, daemon, and background loop activation are
separate live rails. A scheduler record in SQLite is not scheduler activation.

Before scheduler activation:

- The exact job, cadence, timezone, and host must be approved.
- The operator must prove foreground/manual dry-run behavior.
- The job must check permissions, the global kill switch, idempotency, and
  side-effect ledgers before any side effect.
- Logs and completion reports must be written for every run.
- The disable/unload path must be tested.
- A first-live pilot must start with one narrow job and one narrow rail.

## Operator Handoff

OpenClaw may operate live workflows only after a handoff satisfies
[Operator Handoff Contract](OPERATOR_HANDOFF_CONTRACT.md). Handoffs must name
the objective, allowed files/systems, exact actions, permissions, inputs,
outputs, safety constraints, logs, ledgers, completion reports, stop
conditions, and rollback/escalation instructions.

OpenClaw is not a substitute for repository implementation, PR review, merge,
or test validation.

## First-Live Pilot Scope

The first live pilot must be deliberately small:

- One rail only.
- One operator only.
- One runtime host only.
- One approved production DB path if a DB is involved.
- One explicit input fixture or approved real input.
- One bounded operation.
- One success criterion.
- One rollback/escalation path.

High-stakes actions, messages to other people, financial/legal/tax/medical
actions, external meetings, broad scheduler loops, and multi-rail automation
are excluded from the first-live pilot.

## Test Requirements

Before any live rail activation, the implementation PR must include tests for:

- Permission fail-closed behavior.
- Kill switch blocking.
- Preview or dry-run behavior.
- Idempotency and duplicate prevention.
- Side-effect ledger creation and attempt recording.
- Completion report fields.
- Rollback/recovery planning or execution where practical.
- Production DB path rejection or explicit approval handling.
- Protected path rejection.
- No credential leakage in reports/logs.

Docs-only PRs do not need full test runs unless they change executable
behavior. Implementation PRs for live behavior require the full suite and
targeted tests.

## Documentation Requirements

Before live activation, documentation must be current for:

- User-facing operational workflow.
- Rail-specific activation policy.
- Activation checklist.
- First-live pilot protocol.
- Permission names and default states.
- Dry-run/apply/live semantics.
- Credential and production DB boundaries.
- Backup, restore, rollback, and recovery.
- Scheduler activation and disable procedure.
- Operator handoff contract.
- Completion report and ledger evidence expectations.

## Chris Approval Requirements

Chris approval must be explicit, specific, and current. Approval must state:

- Rail or production surface.
- Operator.
- Runtime host.
- Exact allowed action.
- Input scope.
- Permission to use credentials, if applicable.
- Permission to use production DB, if applicable.
- Permission to activate scheduler/background behavior, if applicable.
- First-live pilot bounds.
- Stop condition.

General approval to continue development, merge a docs PR, run tests, open a
PR, or inspect repo-local files does not approve live rail activation.

## Phase 14 Gate

Before Phase 14 or any live rail implementation can begin, the future
activation packet must include:

- A readiness report showing the selected pilot is ready under the approved
  configuration.
- A completed [Activation Checklist](ACTIVATION_CHECKLIST.md).
- A completed
  [First-Live Pilot Protocol](FIRST_LIVE_PILOT_PROTOCOL.md) packet.
- Chris approval for the selected rail, operator, runtime host, production
  surface, input scope, stop condition, and rollback/recovery plan.
- A post-pilot review plan that blocks expansion until the first pilot is
  reviewed.

Phase 13F-D creates these documents only. It does not complete the checklist
or protocol and does not start Phase 14.
