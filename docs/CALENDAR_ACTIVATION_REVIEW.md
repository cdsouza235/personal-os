# Calendar Rail — Post-Live-Period Review Checklist

Fills the gap in `governance/HUMAN_GATES.md`'s activation ladder: adapter packet → soak
evidence → activation packet → **bounded live period → review**. This is that review step,
mirroring `docs/TODOIST_ACTIVATION_REVIEW.md`'s and `docs/GMAIL_ACTIVATION_REVIEW.md`'s
shape for Calendar's specifics.

Owner: Chris, after every bounded live period, before deciding to keep the rail `live`,
extend the soak/live window, or kill it (`docs/CALENDAR_KILL_PROCEDURE.md`). Not an agent
deliverable — no agent fills this checklist in or signs it off; it exists so Chris has a
concrete, repeatable list instead of reconstructing one from memory under time pressure at
the end of each live period.

Decision at the end: **keep live** / **extend and re-review** / **kill** (per the
`docs/CALENDAR_KILL_PROCEDURE.md` kill procedure). Any single unchecked item below is
grounds for "extend" or "kill" rather than "keep live" by default — this checklist is meant
to be conservative, in the same spirit as Gmail's given a calendar event is also hard to
fully undo (`src/personalos/rails/calendar.py`'s own module docstring: an attendee/
notification recipient may already have seen it, even if the event is deleted afterward).

## 1. Event correctness
- [ ] Every real event created during the live period matches what the routine/briefing
      generator intended exactly: same `summary`, same `start_time`/`end_time`, same
      `description`, same `calendar_id`, nothing truncated, nothing stale (e.g. an event
      generated for the wrong day).
- [ ] No event is missing content that should have been present, and no event contains
      content that wasn't in the source routine/briefing (no leaked internal state, no
      placeholder/debug text that should never reach a real calendar).
- [ ] No event was created for the wrong day or with a start/end time off by a timezone
      offset (timezone/date-boundary bugs are the likeliest real-world failure mode for a
      daily event-creation rail, same as Todoist's task-date risk and Gmail's send-day
      risk).
- [ ] No event has `end_time` at or before `start_time` (should be structurally impossible
      per `_build_calendar_event_record`'s own validation, but confirm no real event
      violated this — a violation would indicate the validation was bypassed somehow).

## 2. Calendar scoping (the gate unique to Calendar and Gmail — no Todoist equivalent)
- [ ] No event was ever written to an uncontrolled calendar — every real create's
      `calendar_id` exactly matched `PERSONALOS_RAIL_CALENDAR_CONTROLLED_CALENDAR_ID`'s
      configured value for the entire live period (spot-check the ledger's
      `would_write`/`calendar_id` values against the intended controlled calendar, not just
      that the gate returned "passed").
  - if not: any create that reached an uncontrolled calendar is an incident per the
      RUNBOOK's Incident section — an attendee/notification recipient may already have seen
      the event, so this is the single most serious failure mode this checklist screens
      for.
- [ ] The controlled-calendar-id env var was not changed mid-period without a
      corresponding, explained decision (an unexplained change mid-period is itself worth
      investigating even if no bad create resulted).

## 3. No duplicates
- [ ] No two real calendar events correspond to the same source intent (i.e. the dedupe
      gate — `idempotency_records`, keyed on target_system/operation_type/source_type/
      source_id/dedupe_key/payload_fingerprint — never let a duplicate live write through).
- [ ] If a retry of an identical input occurred during the period (e.g. a crashed run
      re-executed), confirm it was blocked with `STATUS_BLOCKED_DUPLICATE` and did NOT
      create a second event.

## 4. Token-refresh vs. event-create failure discipline (unique to Calendar's two-call flow)
- [ ] Check whether any `STATUS_TOKEN_REFRESH_FAILED` occurred during the period, and if
      so, confirm it was correctly distinguished from `STATUS_EVENT_CREATE_FAILED` — the
      two are never collapsed into one generic error, per `rails/calendar.py`'s own module
      docstring. A `STATUS_TOKEN_REFRESH_FAILED` result means no external state changed and
      `create_event` was never invoked (`event_create_result` stayed `None`); a
      `STATUS_EVENT_CREATE_FAILED` result means the credential chain was valid but the
      specific write did not land.
- [ ] For every `STATUS_TOKEN_REFRESH_FAILED` occurrence, confirm `event_create_attempted`
      is `false` and `event_create_result` is `None` in the returned/logged result — this is
      the concrete signal that the short-circuit actually happened, not just that the status
      string looks right.
- [ ] For every `STATUS_EVENT_CREATE_FAILED` occurrence, confirm `token_refresh_result`
      shows a passed refresh (i.e. the failure genuinely happened on call (b), not a
      mislabeled call (a) failure).

## 5. Ledger / idempotency accuracy
- [ ] Every real calendar event has a corresponding `idempotency_records` row with
      `status = 'completed_simulated'` (the closest existing enum member; see the docstring
      on `_persist_live_write_idempotency_record` in `src/personalos/rails/calendar.py` for
      why no dedicated "completed_live" value exists yet) and a `linked_intent_id`/
      `linked_attempt_id` consistent with how the create was triggered.
  - if not: a live write happened that the ledger doesn't fully account for — treat as an
      incident per the RUNBOOK's Incident section, not a minor discrepancy.
- [ ] Ledger row count for `target_system = 'calendar'` over the live period matches the
      actual count of real events created on the controlled calendar (spot-check against the
      calendar UI/API directly, not just internal state).
- [ ] No `idempotency_records` row exists for a live write that never actually happened
      (would indicate the record was persisted despite an uncertain/failed client result —
      confirm the record is only ever persisted after a confirmed
      `STATUS_EVENT_CREATE_PASSED`, never after a mere `STATUS_TOKEN_REFRESH_PASSED`).

## 6. Credential hygiene
- [ ] None of `PERSONALOS_RAIL_CALENDAR_CLIENT_ID`'s, `PERSONALOS_RAIL_CALENDAR_
      CLIENT_SECRET`'s, or `PERSONALOS_RAIL_CALENDAR_REFRESH_TOKEN`'s values ever appear in
      any log line, ledger row, `STATUS.md`/dashboard output, error message, or committed
      file, across the entire live period (grep logs and the DB for all three credential
      values themselves, not just the variable names).
- [ ] `PERSONALOS_RAIL_CALENDAR_CONTROLLED_CALENDAR_ID`'s value is not secret (it is a
      calendar address, not a credential) — no need to grep for it under this item, but it
      is covered separately under item 2 (calendar scoping) for correctness, not secrecy.
- [ ] No stack trace or error payload from a transport failure (token-refresh error,
      event-create error, network error) during the period leaked the client secret or
      refresh token, or the short-lived access token obtained from a successful refresh
      (confirm `token_refresh_result` in any logged output was redacted — no raw
      `access_token` field — per `_redact_token_result` in `rails/calendar.py`).

## 7. Kill procedure re-verification
- [ ] The kill procedure was NOT needed during the live period (if it was, that is itself an
      incident — capture per the RUNBOOK's Incident section before continuing this
      checklist).
- [ ] Re-run `python3 tests/calendar_kill_drill.py` after the live period ends and confirm
      it still prints `PASS` for all five mechanisms — `rail_state_flip`,
      `client_id_removal`, `client_secret_removal`, `refresh_token_removal`, and
      `controlled_calendar_id_removal` — proves all five kill mechanisms are still live and
      correct, not just documented.

## 8. Scope discipline
- [ ] The rail only ever called `create_live_calendar_event` for its one supported
      operation (single-event creation) — no evidence of scope creep into event updates,
      deletion, recurrence, attendees, reminders, conferencing, or other Calendar API
      capabilities not implemented by `GoogleCalendarClient`.
- [ ] The rail only ever wrote to the ONE controlled calendar ID, never an arbitrary
      caller-supplied one (per D-PO-013 / `rails/calendar.py`'s own calendar-scoping safety
      check — re-confirms item 2 from the code path's perspective, not just the ledger's).
- [ ] Permission setting `calendar_rail_live_write` was never silently changed away from
      `auto_write` mid-period without a corresponding, explained decision.

## Decision
- [ ] All boxes above checked → keep rail `live`, note the decision + date in
      `governance/living/agent-writable/STATUS.md`.
- [ ] Any box unchecked with a benign, understood explanation → extend the live period (or
      revert to soaking) with the specific gap named, and re-run this checklist at the end
      of the extension.
- [ ] Any box unchecked with a real correctness/safety concern — especially any calendar-
      scoping or duplicate-create finding from sections 2 or 3, given a calendar event's
      partial irreversibility (an attendee/notification recipient may already have seen it)
      — → kill the rail (`docs/CALENDAR_KILL_PROCEDURE.md`) and open a fix packet that
      reproduces the issue from the ledger before any code change, per the RUNBOOK's
      Incident procedure.
