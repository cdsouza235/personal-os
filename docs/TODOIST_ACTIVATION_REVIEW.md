# Todoist Rail — Post-Live-Period Review Checklist

Fills the gap in `governance/HUMAN_GATES.md`'s activation ladder: adapter packet → soak
evidence → activation packet → **bounded live period → review**. This is that review step.

Owner: Chris, after every bounded live period, before deciding to keep the rail `live`,
extend the soak/live window, or kill it (`governance/RUNBOOK.md` kill procedure). Not an
agent deliverable — no agent fills this checklist in or signs it off; it exists so Chris
has a concrete, repeatable list instead of reconstructing one from memory under time
pressure at the end of each live period.

Decision at the end: **keep live** / **extend and re-review** / **kill** (per the RUNBOOK
kill procedure). Any single unchecked item below is grounds for "extend" or "kill" rather
than "keep live" by default — this checklist is meant to be conservative.

## 1. Task correctness
- [ ] Every real Todoist task created during the live period matches what the routine/
      priority engine intended: same title, same due date/string, same priority, same
      labels, same project (Inbox, per `_todoist_api_payload`'s deliberate scope).
- [ ] No task is missing content that should have been present, and no task contains
      content that wasn't in the source routine/priority/follow-up.
- [ ] No task was created for the wrong day (timezone/date-boundary bugs are the likeliest
      real-world failure mode for a daily task-creation rail).

## 2. No duplicates
- [ ] No two real Todoist tasks correspond to the same source intent (i.e. the dedupe gate
      — `idempotency_records`, keyed on target_system/operation_type/source_type/source_id/
      dedupe_key/payload_fingerprint — never let a duplicate live write through).
- [ ] If a retry of an identical input occurred during the period (e.g. a crashed run
      re-executed), confirm it was blocked with `STATUS_BLOCKED_DUPLICATE` and did NOT
      create a second Todoist task.

## 3. Ledger / idempotency accuracy
- [ ] Every real Todoist task has a corresponding `idempotency_records` row with
      `status = 'completed_simulated'` (the closest existing enum member; see the docstring
      on `_persist_live_write_idempotency_record` in `src/personalos/rails/todoist.py` for
      why no dedicated "completed_live" value exists yet) and a `linked_intent_id`/
      `linked_attempt_id` consistent with how the write was triggered.
  - if not: a live write happened that the ledger doesn't fully account for — treat as an
      incident per the RUNBOOK's Incident section, not a minor discrepancy.
- [ ] Ledger row count for `target_system = 'todoist'` over the live period matches the
      actual count of real tasks created in the Todoist account for that period (spot-check
      against the Todoist UI/API directly, not just internal state).
- [ ] No `idempotency_records` row exists for a live write that never actually happened in
      Todoist (would indicate the record was persisted despite an uncertain/failed client
      result — check `client_result["status"]` handling wasn't bypassed).

## 4. Credential hygiene
- [ ] `PERSONALOS_RAIL_TODOIST_TOKEN`'s value never appears in any log line, ledger row,
      `STATUS.md`/dashboard output, error message, or committed file, across the entire live
      period (grep logs and the DB for the token value itself, not just the variable name).
- [ ] No stack trace or error payload from a transport failure during the period leaked the
      `Authorization` header or any other credential-bearing request field.

## 5. Kill procedure re-verification
- [ ] The kill procedure was NOT needed during the live period (if it was, that is itself an
      incident — capture per the RUNBOOK's Incident section before continuing this
      checklist).
- [ ] Re-run `python3 tests/todoist_kill_drill.py` after the live period ends and confirm
      it still prints `PASS` for both `rail_state_flip` and `credential_removal` — proves
      both kill mechanisms are still live and correct, not just documented.

## 6. Scope discipline
- [ ] The rail only ever called `create_live_todoist_task` for its one supported operation
      (task creation) — no evidence of scope creep into task updates, deletion, comments, or
      other Todoist endpoints not implemented by `TodoistRailClient`.
- [ ] Permission setting `todoist_rail_live_write` was never silently changed away from
      `auto_write` mid-period without a corresponding, explained decision.

## Decision
- [ ] All boxes above checked → keep rail `live`, note the decision + date in
      `governance/living/agent-writable/STATUS.md`.
- [ ] Any box unchecked with a benign, understood explanation → extend the live period (or
      revert to soaking) with the specific gap named, and re-run this checklist at the end
      of the extension.
- [ ] Any box unchecked with a real correctness/safety concern → kill the rail
      (`governance/living/agent-writable/TODOIST_KILL_PROCEDURE.md`) and open a fix packet
      that reproduces the issue from the ledger before any code change, per the RUNBOOK's
      Incident procedure.
