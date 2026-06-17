# Activation Checklist

## Purpose

This checklist is the final pre-live checklist that must be completed before
any Personal OS live rail, production database, scheduler, live model/API call,
or OpenClaw runtime workflow can be activated.

Phase 13F-D only defines this future checklist. It does not execute the
checklist, approve activation, configure credentials, create production
databases, start schedulers, run OpenClaw, or activate any live rail.

Completing this checklist is a future human approval process. Every item must
be answered with concrete evidence, reviewed by Chris, and bound to a specific
rail, operator, runtime host, commit, and pilot scope.

## Phase 13F-D Baseline

This checklist was drafted from the Phase 13F-D starting point:

- Baseline repo commit: `bfeb90346798fa5aa14bd2be00058a3397f3fa07`.
- Baseline validation state: 445 tests OK after the Phase 13F-C merge.
- Baseline readiness state: `not_ready`.
- Baseline mode: `inert_report_only: true`.
- Baseline live rail state: `live_rails_activated: false`; all live rails
  disabled.
- Baseline production state: no credentials loaded, no production DB active,
  no scheduler activation, no OpenClaw call, and no credentials read.

Future activation must restate the exact repo commit and validation evidence
used for activation. This baseline is historical evidence for the checklist
definition, not approval to run live systems.

## Checklist Rules

- All answers must be explicit. Unknown, omitted, stale, or ambiguous answers
  fail closed.
- Approval must be current and specific to the selected pilot.
- Dev/test, preview, dry-run, simulated-write, and internal-apply evidence do
  not authorize live writes by themselves.
- One completed checklist covers one selected pilot only.
- Non-selected rails remain disabled even when one rail is approved.
- OpenClaw is not involved unless a later explicit handoff approves a narrow
  runtime/operator task.

## Required Checklist

| Item | Required evidence | Stop condition |
| --- | --- | --- |
| Current repo commit and validation state | Exact commit hash, branch or release label, full test result, ResourceWarning-sensitive test result when required, readiness CLI output, and diff/artifact hygiene evidence. | Stop if the commit is unreviewed, tests failed, validation is missing, or the working tree contains unexplained changes. |
| Readiness CLI status requirement | `personalos readiness status` and `personalos readiness status --json` outputs showing the expected gate state before activation review. | Stop if readiness is not understood, reports unexpected active rails, reports credential loading, reports scheduler activation, reports OpenClaw calls, or reports production DB activation before approval. |
| Chris approval requirement | Written approval from Chris naming the rail, operator, host, commit, input scope, permission, credential use if any, production DB use if any, pilot bounds, stop condition, and rollback/recovery plan. | Stop if approval is general, stale, inherited from a prior phase, or does not name the selected pilot. |
| Role-boundary confirmation | Confirmation that ChatGPT is planning/audit, Codex/Fable are repo-development agents, OpenClaw is only a future runtime/operator after handoff, and Chris is final approver. | Stop if a repo agent is being asked to operate live systems or OpenClaw is being invoked without handoff. |
| Live rail selected for pilot | One selected rail, one operation, one operator, one host, one input fixture or approved real input, and one success criterion. | Stop if the pilot requires multiple rails, broad automation, unbounded inputs, or multiple operators. |
| Explicit non-selected rails remain disabled | List of all non-selected rails and confirmation that their permissions, clients, credentials, scheduler paths, and runtime workflows remain disabled. | Stop if any non-selected rail is enabled, partially configured for live use, or ambiguous. |
| Credentials/secrets review | Credential owner, storage label, required scopes, revocation path, rotation path, operator allowed to use the credential, and confirmation that secrets are not in repo files or reports. | Stop if credentials must be inspected by Codex/Fable, printed, copied, broadened, or used without approval. |
| Production DB path approval | Exact approved production DB path, runtime host, owner/operator, allowed commands, and proof that repo-local runtime artifacts remain prohibited. | Stop if the DB path is implicit, guessed, repo-local, unreviewed, or outside the approved surface. |
| Production DB backup/restore plan | Backup path label, backup creation procedure, restore-test path, restore verification procedure, retention expectation, and evidence fields. | Stop if backup has no restore test, restore test touches production state, or evidence would expose protected data. |
| Migration plan | Exact migration set, checksum verification plan, foreign-key/integrity checks, transaction behavior, concurrency expectation, and completion report fields. | Stop if migrations are ad hoc, unreviewed, cannot be previewed, or lack rollback/recovery criteria. |
| Idempotency and duplicate-prevention plan | Idempotency key source fields, payload fingerprint behavior, duplicate-detection behavior, retry behavior, collision posture, and stale-intent handling. | Stop if duplicate prevention is undefined or relies only on manual memory. |
| Side-effect ledger plan | Ledger schema/table or approved evidence store, pre-attempt intent recording, attempt/outcome recording, idempotency fields, validation report, and final status. | Stop if the external side effect can occur before the ledger intent exists. |
| Completion report requirement | Report location, required fields, timestamps, operator, commit, permission checks, input and approval references, ledger IDs, safety flags, outcome, and rollback/undo status. | Stop if the report would omit side-effect IDs, rollback evidence, safety flags, or error/escalation notes. |
| Rollback/recovery plan | Rail-specific undo or recovery path, what can be undone, what cannot be undone, verification step, and escalation path. | Stop if rollback is assumed but not actually possible or if unrecoverable behavior is not acknowledged. |
| Kill switch / disable mechanism | Global disable location, rails covered, check timing, scheduler/model/API coverage, verification command, and restoration approval path. | Stop if the kill switch is missing, does not fail closed, or is not checked before the selected live behavior. |
| Scheduler activation policy | Confirmation that scheduler, LaunchAgent, crontab, daemon, and background loop activation are separate rails and remain disabled unless separately approved. | Stop if the first pilot needs background execution or if scheduler disable/unload is untested. |
| Operator handoff packet requirement | Handoff packet satisfying the Operator Handoff Contract when OpenClaw or any runtime operator is involved. | Stop if the operator is asked to infer files, systems, commands, permissions, stop conditions, or rollback steps. |
| First-live pilot scope | Confirmation that the pilot follows the First-Live Pilot Protocol: one rail, one-shot or narrow batch, no background daemon, bounded input, preview, approval, report, ledger, and post-run audit. | Stop if the pilot is high-risk, irreversible without acknowledgement, or broader than the approved scope. |
| Test requirements | Full test command, targeted rail tests, fail-closed permission tests, kill-switch tests, idempotency tests, ledger tests, completion-report tests, rollback tests where practical, and readiness CLI checks. | Stop if tests do not cover the selected live path and its block/fail-closed states. |
| Dry-run rehearsal requirement | Dry-run or preview evidence generated from the exact candidate input, with no external write and no production mutation. | Stop if dry-run evidence is missing, stale, uses different inputs, or already performed a live side effect. |
| Post-pilot review requirement | Review plan covering actual outcome, ledger/report evidence, rollback/undo status, anomalies, user-visible effects, and decision on whether to halt or expand. | Stop further live work until the review is complete. |
| Stop condition | Exact stop condition for the pilot and for the operator, including first success, first blocked safety check, first failed permission check, first error, or first completed report. | Stop if the operator has discretion to continue beyond the named condition without fresh approval. |

## Selected-Rail Addendum

The activation packet must add a selected-rail addendum before review:

- Rail:
- Operation:
- Operator:
- Runtime host:
- Repo commit:
- Input reference:
- Approval artifact:
- Required credential label, if any:
- Required production DB path label, if any:
- Required permission names:
- Preview/dry-run artifact:
- Ledger target:
- Completion report target:
- Rollback/undo procedure:
- Stop condition:
- Non-selected rails confirmed disabled:

## Final Gate

No live rail can move from disabled or inert to live unless all of these are
true:

- The readiness gate is satisfied for the selected pilot.
- This activation checklist is completed with evidence.
- The [First-Live Pilot Protocol](FIRST_LIVE_PILOT_PROTOCOL.md) is completed
  for the selected pilot.
- Chris explicitly approves the selected pilot.
- The first-live pilot completes and receives post-pilot review before any
  expansion.
