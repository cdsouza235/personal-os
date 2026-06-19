# Phase 13G Pre-Live Readiness Matrix

Last updated: 2026-06-19

## Purpose

Phase 13G is a planning and control-plane decision packet. It audits the
current repo readiness posture and translates the existing Phase 13F readiness
policies into a rail-by-rail activation matrix.

This document does not start Phase 14, approve a pilot, configure
credentials, activate production SQLite, start a scheduler, call OpenClaw, call
live model/API providers, contact external services, or perform external
writes.

Phase 14 remains blocked until Chris explicitly approves a specific phase
scope, selected rail, operator, runtime host, input scope, credential boundary,
production DB boundary, stop condition, rollback/recovery plan, and post-pilot
review requirement.

## Current Validated Repo State

- Repo: `cdsouza235/personal-os`
- Local repo: `/Users/coldstake/dev/personal-os`
- Current main checked for this packet:
  `ecfa97c002f3879e9245bef59ec6cd680d1a4b71`
- Latest merged PRs in scope:
  - PR #31: Phase 13E-D synthetic end-to-end no-send demo
  - PR #32: post-merge STATUS refresh after PR #31
- Phase 13E-D: implemented and post-merge validated
- Full suite at the current validated snapshot: 461 tests OK
- ResourceWarning-sensitive suite at the current validated snapshot:
  461 tests OK
- Current readiness state: `not_ready`
- Current mode: `inert_report_only=true`
- Current live rail state: `live_rails_activated=false`
- Current blocked state: Phase 14 is not started

Read-only readiness commands run for this packet reported:

- `personalos readiness status --json`
  - `status=not_ready`
  - `inert_report_only=true`
  - `live_rails_activated=false`
  - `no_credentials_loaded=true`
  - `credentials_read=false`
  - `production_db_path_active=false`
  - `scheduler_activated=false`
  - `openclaw_called=false`
  - `external_services_contacted=false`
  - `external_mutation=false`
  - no DB opened and no files written
- `personalos workflows --json`
  - safe local workflows are report-only, preview, local apply, no-send,
    ledger inspection, scheduler simulation, and synthetic demo workflows
  - blocked actions remain Gmail send/draft, Todoist writes, Calendar writes,
    PersonalOS Markdown writes, credential loading, scheduler/background
    activation, production DB use, live model/API calls, and OpenClaw runtime
    calls

## Rails That Exist

The current control plane names these rails or activation surfaces:

- production SQLite/runtime DB
- PersonalOS Markdown writes
- Todoist
- Google Calendar
- Gmail
- scheduler, LaunchAgent, crontab, daemon, or background loop
- OpenClaw runtime workflows
- live model/API providers
- credentials/OAuth
- external services generally

All are disabled, blocked, not configured for live behavior, or dependency
surfaces only. None are approved for live activation by this packet.

## Rail-By-Rail Readiness Matrix

| Rail | Current status | Current inert evidence | First safe pilot shape | Gates before activation | Required approval | Rollback or kill switch | Post-pilot evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Production SQLite/runtime DB | Disabled; no production path active. | Readiness reports `production_db_path_active=false`; `database_target.access=not_applicable_no_db_opened`; repo-local `var/` and DB artifacts are prohibited. | First safe step is a restore-test and migration rehearsal on an approved copy, not a production mutation. If a live rail later needs durable ledgers, approve one exact production DB path first. | Production DB Policy; exact path approval; backup before mutation; restore verification; migration checksum and integrity checks; file permission and locking plan; completion report. | Chris approval naming exact DB path, host, operator, migration/operation, backup destination, restore-test destination, rollback condition, and evidence. | Global kill switch must keep live rails disabled. DB rollback is restore from backup or roll-forward under the approved plan. | Completion report with commit, DB path label, backup label, restore-test result, integrity checks, migration status, timestamps, outcome, and rollback status. |
| PersonalOS Markdown writes | Disabled; protected path remains off limits. | Readiness reports PersonalOS Markdown rail disabled; protected paths not touched; Phase 13E-D only produced preview/review-only Markdown candidates. | A future approved append-only or patch-preview write to one explicitly approved file/folder class, after backup/restore proof. Not recommended as the first external pilot. | Target class approval; exact write mode; previewed content or patch; backup/recovery proof; ledger before write; idempotency/content hash; completion report. | Chris approval naming target class/path label, operation, input, content preview, operator, host, backup/recovery path, and stop condition. | Global kill switch blocks writes. Rollback is restore from backup, reverse patch, or corrective edit; if not cleanly reversible, approval must say so. | Report with target label, content hash, write mode, approval reference, ledger IDs, backup/reference, outcome, and rollback/corrective evidence. |
| Todoist | Disabled; only dev/test fake or preview paths exist. | Readiness reports Todoist live write rail disabled; workflows list Todoist live write as blocked; Phase 13E-D uses Todoist candidates as preview/simulated only. | Recommended first possible live pilot: create one self-only low-risk routine task from one validated Todoist candidate in a foreground command. | Rail-specific live permission; credential label and scopes; exact task preview; idempotency key and payload fingerprint; ledger intent before attempt; duplicate prevention; global kill switch; completion report; undo plan. | Chris approval naming Todoist rail, create operation, operator, host, commit, input candidate, credential label, permission names, one-task maximum, stop condition, and undo plan. | Global kill switch blocks the command. Undo can delete, close, reopen, annotate, or create a corrective task as approved. | Report with Todoist task ID or blocked/duplicate outcome, ledger IDs, idempotency key, payload fingerprint, permission result, safety flags, undo status, and proof non-selected rails stayed disabled. |
| Google Calendar | Disabled; only dev/test fake or preview paths exist. | Readiness reports Google Calendar live write rail disabled; workflows list Calendar live write as blocked; Phase 13E-D uses Calendar candidates as preview/simulated only. | One self-only calendar block with no external attendees and one approved calendar ID, after Todoist or equivalent controls prove the live-write path. | Rail-specific live permission; credential label and calendar ID approval; timezone-aware event preview; attendee boundary; idempotency; ledger before attempt; duplicate prevention; global kill switch; completion report; rollback plan. | Chris approval naming Calendar rail, create/update operation, operator, host, commit, calendar ID, input candidate, credential label, stop condition, and rollback path. | Global kill switch blocks the command. Undo can delete, cancel, update, or create a corrective event. | Report with event ID or blocked/duplicate outcome, calendar ID, time window, attendee state, ledger IDs, safety flags, rollback status, and disabled non-selected rails. |
| Gmail | Disabled; no Gmail client or credential loading is implemented. | Readiness reports Gmail live draft/send rail disabled; workflows list Gmail send/draft as blocked; Phase 13E-D uses no-send briefing preview/export only. | Not recommended first. Earliest future Gmail pilot should be a draft-only self-review briefing candidate, not send, and only after lower-risk rails prove ledger, idempotency, and kill-switch behavior. | Separate draft/send permissions; credential label and scopes; exact recipients/subject/body preview; high-stakes/person-to-person approval checks; ledger before attempt; idempotency; global kill switch; completion report. | Chris approval naming draft or send explicitly. Send needs stronger approval because sent mail cannot truly be undone. | Global kill switch blocks draft/send. Drafts may be deleted; sent email recovery is correction/escalation, not true rollback. | Report with no-send preview reference, draft/message ID if created, send/draft status, ledger IDs, safety flags, rollback or escalation state, and proof no unintended recipients or non-selected rails were touched. |
| Scheduler/background loop | Disabled; simulated scheduler records only. | Readiness reports `scheduler_activated=false`; workflows list scheduler activation as blocked; scheduler previews are simulated only. | Not recommended first. Earliest scheduler pilot should be one foreground-validated narrow job with tested disable/unload, and only if scheduler activation itself is the selected rail. | Separate scheduler activation permission; exact job/cadence/timezone/host; foreground dry-run; global kill switch checked before every run; completion report per run; disable/unload proof; no multi-rail automation. | Chris approval naming job, cadence, host, operator, selected rail, stop condition, and disable/unload path. | Global kill switch plus OS-level disable/unload/stop procedure. Verify no further runs. | Report with job label, host, cadence, run IDs, kill-switch checks, side effects blocked or recorded, disable/unload result, and proof no background work continued. |
| OpenClaw runtime workflows | Disabled; no OpenClaw operation implemented. | Readiness reports `openclaw_called=false`; OpenClaw runtime calls are blocked; protected `.openclaw` path not inspected or touched. | Not recommended first. Earliest safe step is a handoff-only packet or no-send operator smoke test after the Operator Handoff Contract is complete. | Approved handoff; exact workflow/action; allowed and forbidden files/systems; credential and production DB boundaries; stop condition; ledgers/logs/completion report; rollback/escalation plan. | Chris approval selecting OpenClaw as operator for one workflow, one host, one objective, exact actions, and exact stop condition. | Stop workflow, preserve logs, and undo downstream rail actions where possible. Global kill switch must block downstream rails. | Report with handoff reference, workflow name/ID, inputs, outputs, ledger IDs, logs preserved, stop condition honored, rollback/undo state, and proof OpenClaw stayed inside scope. |
| Live model/API providers | Disabled; no provider client is implemented for live calls. | Readiness reports live model/API rail disabled; workflows list live model/API calls as blocked; Composer behavior remains fake/local for no-send flows. | Not recommended first. Earliest pilot should be one bounded model packet with no downstream live side effect and no protected-file access. | Provider/model approval; bounded prompt/input packet; redaction and protected data exclusion; credential label; cost/rate-limit policy; idempotency/replay behavior where practical; report without secrets. | Chris approval naming provider/model, model role, input packet, operator, host, credential label, cost/rate bounds, and stop condition. | Global kill switch blocks calls. The call cannot be undone; recovery is prevent retries, discard unsafe output, preserve metadata, and escalate. | Report with provider/model, packet/output IDs, token/cost metadata if available, safety flags, no-secret confirmation, retry prevention, and proof no downstream rail executed. |
| Credentials/OAuth | Dependency surface, not an executable rail; currently not loaded/read. | Readiness reports `credentials_loaded=false`, `credentials_read=false`, `credentials=not_loaded`; repo agents did not inspect credentials. | First safe step is a label-only credential readiness packet. Any real validation must be done by an approved runtime operator without printing or exposing secrets. | Credential owner; storage label; scopes; revocation and rotation path; operator allowed to use it; no repo secrets; completion reports redacted; fail closed when missing or ambiguous. | Chris approval naming credential label, rail, scopes, operator, host, allowed validation/use, and revocation path. | Disable environment/config, revoke token, rotate credential, and keep global kill switch off until reapproved. | Report with credential label only, scope summary, validation outcome, no-secret assertion, revocation/rotation path, and proof no secret was stored in repo output. |
| External services generally | Blocked except for explicitly approved repo/GitHub development operations. Runtime external services remain disabled. | Readiness reports `external_services_contacted=false`, `external_mutation=false`, `no_external_writes=true`, and write clients not initialized. | No generic external-service pilot. Select one named rail/provider and apply its rail-specific packet. | Selected service, purpose, credential label, network boundary, rate/cost policy, ledger/report evidence, rollback/recovery, and kill-switch coverage. | Chris approval naming exact service, operation, operator, host, input, credential label if any, and stop condition. | Global kill switch and provider-specific disable/revoke path. External contact cannot always be undone; prevent retries and preserve evidence. | Report with service, operation, request metadata without secrets, outcome, external object IDs if any, safety flags, rollback/recovery state, and proof non-selected services stayed disabled. |

## Readiness Gates Still Missing Or Blocked

Current read-only readiness output fails closed because the following gates are
missing or not yet approved:

- selected pilot readiness configuration
- mode separation confirmation
- credentials policy acknowledgement for a selected pilot
- production DB path approval
- production migration policy approval
- backup and restore verification
- idempotency policy approval
- side-effect ledger requirement approval
- completion report requirement approval
- rollback and recovery requirement approval
- global kill switch or disable mechanism
- scheduler activation requirement approval
- operator handoff approval, if any runtime operator is involved
- first-live pilot approval or scope
- current implementation/test/documentation evidence for the selected pilot
- explicit Chris approval marker for the selected pilot

Until those are satisfied for one selected pilot, the expected status remains
`not_ready`.

## Human Approval Gate

Before any Phase 14 implementation or pilot activation, Chris approval must be
written, current, and specific. It must name:

- selected rail or production surface
- exact operation
- operator
- runtime host
- repo commit or release label
- approved input scope
- credential label and scopes, if any
- production DB path label, if any
- required permission names
- preview/dry-run artifact
- side-effect ledger target
- completion report target
- stop condition
- rollback or recovery plan
- post-pilot review requirement
- non-selected rails that must remain disabled

General approval to continue development, merge a PR, run tests, create a
readiness document, or complete a previous phase does not approve a live pilot.

## Recommended Activation Order

Phase 14 should not begin from this packet alone. If Chris later approves a
Phase 14 design phase, the safest order is:

1. Implement or complete missing selected-pilot control gates without live
   writes: selected readiness config, global kill switch, rail-specific
   permission key, preview/dry-run, idempotency, side-effect ledger, completion
   report, and rollback reporting.
2. Decide whether the selected pilot needs production SQLite. If yes, approve
   and verify the production DB path, backup, restore-test, integrity, and
   migration plan before the rail pilot.
3. Rehearse the exact selected pilot input in dry-run/preview mode and produce
   the activation packet.
4. Only after explicit Chris approval, run one foreground live pilot for one
   selected rail.
5. Complete post-pilot review before any expansion.

For the first possible live rail, this packet recommends Todoist before
Calendar, Gmail, scheduler, OpenClaw, PersonalOS Markdown, or live model/API
providers.

## First Possible Phase 14 Pilot Recommendation

Recommended first possible live pilot, if Chris later approves Phase 14:

Create one self-only, low-risk Todoist routine task from one already validated
Todoist candidate, using one explicit foreground command, one approved Todoist
credential label, one approved permission, one ledger intent before the
attempt, deterministic idempotency, duplicate detection, a completion report,
and an undo path.

This is the safest first candidate because:

- Todoist task creation is narrow and visible.
- A single low-risk task is easy for Chris to inspect.
- Undo is practical: delete, close, reopen, annotate, or create a corrective
  task.
- It does not require external attendees, message recipients, background
  execution, or OpenClaw discretion.
- It can prove the shared controls needed by later rails: approval,
  credential label handling, idempotency, ledger-first behavior, kill switch,
  completion report, and post-pilot audit.

This recommendation does not authorize the pilot. It only identifies the
lowest-risk candidate for a future approval packet.

## Why Not Gmail First

Gmail is not a preferred first pilot because:

- sent email cannot truly be undone
- message-like output can affect other people
- relationship, legal, financial, medical, tax, family-sensitive, and other
  high-stakes content requires stronger review
- draft and send permissions must be separate
- lower-risk reversible rails can prove the shared live-write controls first

If Gmail is considered later, draft-only should precede send, and send should
require stronger explicit approval.

## Why Not Scheduler First

Scheduler/background activation is not a preferred first pilot because:

- background jobs can repeat without immediate foreground inspection
- scheduler activation is a separate live rail
- kill-switch, disable/unload, logging, idempotency, and completion-report
  behavior must be proven before any recurring behavior
- a scheduler pilot can accidentally become multi-rail automation if the job
  performs downstream writes

The first live pilot should use an explicit foreground command.

## Why Not OpenClaw First

OpenClaw is not a preferred first pilot because:

- OpenClaw is the future runtime/operator layer, not the repo implementation
  layer
- it requires a complete operator handoff packet before any runtime work
- it may need access to protected runtime surfaces that are currently off
  limits
- it should not infer scope, inputs, outputs, permissions, stop conditions, or
  rollback actions from repo docs alone

OpenClaw should remain blocked until a narrow handoff is approved after the
selected pilot controls are already clear.

## Phase 14 Block

Phase 14 remains blocked. This packet is ready for Chris/ChatGPT review as a
decision aid, but it does not authorize:

- live Gmail
- live Todoist
- live Google Calendar
- PersonalOS Markdown writes
- credentials or OAuth configuration
- production DB activation
- scheduler, LaunchAgent, crontab, daemon, or background-loop activation
- OpenClaw runtime workflows
- live model/API calls
- external runtime writes
- protected path inspection or mutation
