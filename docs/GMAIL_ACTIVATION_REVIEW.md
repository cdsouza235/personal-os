# Gmail Rail — Post-Live-Period Review Checklist

Fills the gap in `governance/HUMAN_GATES.md`'s activation ladder: adapter packet → soak
evidence → activation packet → **bounded live period → review**. This is that review step,
mirroring `docs/TODOIST_ACTIVATION_REVIEW.md`'s shape for Gmail's specifics.

Owner: Chris, after every bounded live period, before deciding to keep the rail `live`,
extend the soak/live window, or kill it (`docs/GMAIL_KILL_PROCEDURE.md`). Not an agent
deliverable — no agent fills this checklist in or signs it off; it exists so Chris has a
concrete, repeatable list instead of reconstructing one from memory under time pressure at
the end of each live period.

Decision at the end: **keep live** / **extend and re-review** / **kill** (per the
`docs/GMAIL_KILL_PROCEDURE.md` kill procedure). Any single unchecked item below is grounds
for "extend" or "kill" rather than "keep live" by default — this checklist is meant to be
conservative, more so than Todoist's given email is irreversible (`governance/RUNBOOK.md`'s
Incident section: "email cannot be unsent — which is why Gmail soaks longest per the
activation ladder").

## 1. Content correctness
- [ ] Every real email sent during the live period matches what the routine/briefing
      generator intended exactly: same subject, same body content, nothing truncated,
      nothing stale (e.g. a briefing generated for the wrong day).
- [ ] No email is missing content that should have been present, and no email contains
      content that wasn't in the source routine/briefing (no leaked internal state, no
      placeholder/debug text that should never reach a real inbox).
- [ ] No email was sent for the wrong day (timezone/date-boundary bugs are the likeliest
      real-world failure mode for a daily briefing-send rail, same as Todoist's task-date
      risk).

## 2. Recipient control (the gate unique to Gmail — no Todoist equivalent)
- [ ] No unintended recipient ever received anything — every real send's `to_address`
      exactly matched `PERSONALOS_RAIL_GMAIL_CONTROLLED_RECIPIENT`'s configured value for
      the entire live period (spot-check the ledger's `would_write`/`to_address` values
      against the intended controlled recipient, not just that the gate returned "passed").
  - if not: any send that reached an uncontrolled address is an incident per the RUNBOOK's
      Incident section — email cannot be unsent, so this is the single most serious failure
      mode this checklist screens for.
- [ ] The controlled-recipient env var was not changed mid-period without a corresponding,
      explained decision (an unexplained change mid-period is itself worth investigating
      even if no bad send resulted).

## 3. No duplicates
- [ ] No two real emails correspond to the same source intent (i.e. the dedupe gate —
      `idempotency_records`, keyed on target_system/operation_type/source_type/source_id/
      dedupe_key/payload_fingerprint — never let a duplicate live send through).
- [ ] If a retry of an identical input occurred during the period (e.g. a crashed run
      re-executed), confirm it was blocked with `STATUS_BLOCKED_DUPLICATE` and did NOT send
      a second email. This is more important for Gmail than Todoist: a duplicate task is an
      annoyance the user can delete; a duplicate email has already reached the inbox and
      cannot be un-sent.

## 4. Ledger / idempotency accuracy
- [ ] Every real email has a corresponding `idempotency_records` row with
      `status = 'completed_simulated'` (the closest existing enum member; see the docstring
      on `_persist_live_write_idempotency_record` in `src/personalos/rails/gmail.py` for why
      no dedicated "completed_live" value exists yet) and a `linked_intent_id`/
      `linked_attempt_id` consistent with how the send was triggered.
  - if not: a live send happened that the ledger doesn't fully account for — treat as an
      incident per the RUNBOOK's Incident section, not a minor discrepancy.
- [ ] Ledger row count for `target_system = 'gmail'` over the live period matches the actual
      count of real emails sent (spot-check against the sending Gmail account's Sent folder
      directly, not just internal state).
- [ ] No `idempotency_records` row exists for a live send that never actually happened
      (would indicate the record was persisted despite an uncertain/failed client result —
      check `client_result["status"]` handling wasn't bypassed; `send_live_gmail_message`
      only persists after `STATUS_CLIENT_CALL_PASSED`, confirm no code path circumvents
      that ordering).

## 5. Credential hygiene
- [ ] Neither `PERSONALOS_RAIL_GMAIL_SENDER_ADDRESS`'s value nor
      `PERSONALOS_RAIL_GMAIL_APP_PASSWORD`'s value ever appears in any log line, ledger row,
      `STATUS.md`/dashboard output, error message, or committed file, across the entire live
      period (grep logs and the DB for both credential values themselves, not just the
      variable names). The sender address is not secret by itself and may legitimately
      appear in message headers/ledger rows — check specifically for the app password.
- [ ] The controlled-recipient address is likewise absent from any place it shouldn't be
      logged verbatim outside the ledger's own `to_address`/`would_write` fields.
- [ ] No stack trace or error payload from a transport failure (SMTP auth error, network
      error) during the period leaked the app password or SMTP login sequence.

## 6. Kill procedure re-verification
- [ ] The kill procedure was NOT needed during the live period (if it was, that is itself an
      incident — capture per the RUNBOOK's Incident section before continuing this
      checklist).
- [ ] Re-run `python3 tests/gmail_kill_drill.py` after the live period ends and confirm it
      still prints `PASS` for all three mechanisms —
      `rail_state_flip`, `sender_credential_removal` / `app_password_removal` (both halves
      of credential removal), and `controlled_recipient_removal` — proves all three kill
      mechanisms are still live and correct, not just documented.

## 7. Scope discipline
- [ ] The rail only ever called `send_live_gmail_message` for its one supported operation
      (single-recipient message send) — no evidence of scope creep into arbitrary
      recipients, multiple recipients, attachments, or other Gmail/SMTP capabilities not
      implemented by `GmailSmtpClient`.
- [ ] Permission setting `gmail_rail_live_send` was never silently changed away from
      `auto_write` mid-period without a corresponding, explained decision.
- [ ] No caller-supplied `to_address` other than the controlled recipient was ever accepted
      (re-confirms item 2 from the code path's perspective, not just the ledger's).

## Decision
- [ ] All boxes above checked → keep rail `live`, note the decision + date in
      `governance/living/agent-writable/STATUS.md`.
- [ ] Any box unchecked with a benign, understood explanation → extend the live period (or
      revert to soaking) with the specific gap named, and re-run this checklist at the end
      of the extension.
- [ ] Any box unchecked with a real correctness/safety concern — especially any recipient-
      control or duplicate-send finding from sections 2 or 3, given email's irreversibility
      — → kill the rail (`docs/GMAIL_KILL_PROCEDURE.md`) and open a fix packet that
      reproduces the issue from the ledger before any code change, per the RUNBOOK's
      Incident procedure.
