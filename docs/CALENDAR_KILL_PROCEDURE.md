# Calendar rail — exact kill steps

This document supplements `governance/RUNBOOK.md`'s generic "Kill procedures" section
(which stays as-is) with Calendar-specific detail: the exact FIVE kill mechanisms as
concrete, numbered steps a human follows under pressure. Do any one of them; all five are
proven independently by `tests/calendar_kill_drill.py`, run it first if unsure any still
works.

Calendar has one more independent kill mechanism than Gmail
(`docs/GMAIL_KILL_PROCEDURE.md`, three mechanisms): FIVE independent mechanisms stop
`create_live_calendar_event` (`src/personalos/rails/calendar.py`) from making its next real
call to either the Google OAuth token endpoint or the Calendar API. Any one alone is
sufficient; you do not need to do more than one, but doing more than one is not harmful.
This is more than Gmail because the Calendar rail's OAuth refresh-token flow needs THREE
secrets instead of two (client ID, client secret, refresh token — any one of which
independently gates the write), plus the same controlled-calendar-id safety gate shape that
Gmail has for its controlled recipient.

**Mechanism 1 — flip the rail state off `"live"`** (fastest if you already have a Python
shell or a REPL open against the running process/host):
1. Open `src/personalos/status.py` and find the `_RAIL_STATES` dict (private literal near
   the top of the file, currently `{"todoist": "inert", "gmail": "inert", "calendar":
   "inert", "model_api": "inert"}`).
2. Change the `"calendar"` value from `"live"` to `"inert"` (or `"soaking"` — anything other
   than the literal string `"live"` blocks the rail; `"inert"` is the correct choice for a
   real kill, not `"soaking"`).
3. Save the file. **A running process does not automatically pick up this edit.** Python
   loads `_RAIL_STATES` into memory once, at import time; a process that already has
   `status.py` imported keeps the OLD dict in memory regardless of what the file on disk
   now says, until that process either re-imports the module (which does not happen on its
   own) or is restarted. Saving the file alone does not flip anything live — restart the
   process (or, equivalently, make sure no invocation is already in flight) for the edit to
   take effect.

   This is safe to do with a plain file save today only because of a fact about the current
   deployment, not because of anything in the code: every Calendar-rail invocation right
   now is a fresh, short-lived CLI process (e.g. `personalos run morning`) — there is no
   long-running daemon or background process holding a stale import. So the very next
   invocation, whenever it happens, naturally starts a new process, imports the file fresh,
   and sees the edited value — there is nothing to restart because nothing long-running is
   running. **If a background/daemon mode has since landed (see `P-SCHED-02` in
   `governance/ROADMAP.md`), re-verify this assumption before relying on it** — a genuinely
   long-running process would need an explicit restart, and this paragraph would need to be
   updated to say so plainly rather than silently going stale.

   There is no config flag or database row to also update — the dict literal in this one
   file is the entire mechanism.
4. Verify: run `python3 tests/calendar_kill_drill.py` (no arguments, no network, no real
   credential or real calendar ID needed) and confirm it prints `PASS` for
   `kill mechanism: rail_state_flip`. Note what this actually proves: the drill patches
   `_RAIL_STATES` in-process via `mock.patch.dict` and confirms the gate check correctly
   blocks a create once the value is not `"live"` — it proves the GATE LOGIC is correct. It
   does not and cannot exercise the restart/re-import behavior described in step 3 above
   (whether a real running process picks up a real on-disk file edit); that is a
   deployment/operational property, not something an in-process mock can observe. Trust
   step 3's reasoning for that half, not the drill.

**Mechanism 2 — remove `PERSONALOS_RAIL_CALENDAR_CLIENT_ID` from the environment** (fastest
if you don't have file-edit access to the host but do control the environment the process
reads, e.g. a process manager, shell profile, or secrets store). The OAuth refresh flow
needs all three credential env vars, not one — `create_live_calendar_event` checks all three
every call and fails closed if any is missing or empty, so removing just this one is
enough:
1. Find where `PERSONALOS_RAIL_CALENDAR_CLIENT_ID` is set for the process (host environment
   under Chris's account per `governance/RUNBOOK.md`'s invariant — never in a repo file, per
   `.env.example` and `governance/SECURITY.md`).
2. Unset it (`unset PERSONALOS_RAIL_CALENDAR_CLIENT_ID` in the shell that launches the
   process, or remove it from whatever process manager/secrets store injects it) and
   restart or re-launch the process so it reads the environment again.
3. The next `create_live_calendar_event` call reads `os.environ` fresh at call time (never
   cached) and finds the variable absent, refusing with `STATUS_BLOCKED_CREDENTIAL_MISSING`
   before constructing any HTTPS client — the token-refresh call is never attempted. Setting
   the variable to an empty/whitespace-only value has the same fail-closed effect
   (`STATUS_BLOCKED_CREDENTIAL_EMPTY`) if unsetting it outright isn't convenient.
4. Verify: run `python3 tests/calendar_kill_drill.py` and confirm it prints `PASS` for both
   `kill mechanism: client_id_removal` (absence sub-case) and
   `kill mechanism: client_id_empty_value` (empty-value sub-case) — the drill proves each
   sub-case independently so that a regression in the empty-value check alone (leaving
   absence-handling intact) cannot slip through undetected.

**Mechanism 3 — remove `PERSONALOS_RAIL_CALENDAR_CLIENT_SECRET` from the environment**
(same shape as Mechanism 2, proven independently sufficient — either credential alone kills
the rail):
1. Find where `PERSONALOS_RAIL_CALENDAR_CLIENT_SECRET` is set for the process (same
   host-environment location as above).
2. Unset it and restart or re-launch the process so it reads the environment again.
3. The next `create_live_calendar_event` call finds the variable absent, refusing with
   `STATUS_BLOCKED_CREDENTIAL_MISSING` (or `STATUS_BLOCKED_CREDENTIAL_EMPTY` if set to an
   empty/whitespace-only value instead) before any HTTPS client is constructed.
4. Verify: run `python3 tests/calendar_kill_drill.py` and confirm it prints `PASS` for both
   `kill mechanism: client_secret_removal` (absence sub-case) and
   `kill mechanism: client_secret_empty_value` (empty-value sub-case), for the same reason
   given under Mechanism 2.

**Mechanism 4 — remove `PERSONALOS_RAIL_CALENDAR_REFRESH_TOKEN` from the environment**
(same shape again — proven independently sufficient):
1. Find where `PERSONALOS_RAIL_CALENDAR_REFRESH_TOKEN` is set for the process (same
   host-environment location as above).
2. Unset it and restart or re-launch the process so it reads the environment again.
3. The next `create_live_calendar_event` call finds the variable absent, refusing with
   `STATUS_BLOCKED_CREDENTIAL_MISSING` (or `STATUS_BLOCKED_CREDENTIAL_EMPTY` if set to an
   empty/whitespace-only value instead) before any HTTPS client is constructed.
4. Verify: run `python3 tests/calendar_kill_drill.py` and confirm it prints `PASS` for both
   `kill mechanism: refresh_token_removal` (absence sub-case) and
   `kill mechanism: refresh_token_empty_value` (empty-value sub-case), for the same reason
   given under Mechanism 2.

**Mechanism 5 — remove or change `PERSONALOS_RAIL_CALENDAR_CONTROLLED_CALENDAR_ID`**
(unique to Calendar and Gmail-shaped rails; no Todoist equivalent). This is a fifth safety
check layered after the four fixed gates (see the "Calendar-scoping" section of
`src/personalos/rails/calendar.py`'s module docstring): `create_live_calendar_event` only
ever writes to the single calendar named by
`PERSONALOS_RAIL_CALENDAR_CONTROLLED_CALENDAR_ID`, and refuses if that env var is absent,
empty, or doesn't exactly match the event's `calendar_id`. A MISMATCH is just as effective
as absence — the gate checks exact equality against the caller-supplied `calendar_id`, not
merely whether the env var is set, so changing it to any other value blocks the write just
as surely as unsetting it does:
1. Find where `PERSONALOS_RAIL_CALENDAR_CONTROLLED_CALENDAR_ID` is set for the process
   (same host-environment location as the credentials above).
2. Unset it, or change its value to anything other than the calendar ID the rail is
   currently configured to write to, and restart or re-launch the process so it reads the
   environment again.
3. The next `create_live_calendar_event` call reads the env var fresh at call time and
   either finds it absent/empty or finds it no longer matches the outgoing `calendar_id`,
   refusing with `STATUS_BLOCKED_CALENDAR_NOT_CONTROLLED` before constructing any HTTPS
   client. This works even if all three credentials from Mechanisms 2-4 are still valid and
   present — it is a fully independent gate, not a fallback of the credential check.
4. Verify: run `python3 tests/calendar_kill_drill.py` and confirm it prints `PASS` for
   both `kill mechanism: controlled_calendar_id_removal` (absence sub-case) and
   `kill mechanism: controlled_calendar_id_mismatch` (mismatch sub-case) -- the drill
   proves each sub-case independently so that a regression in the equality check alone
   (leaving absence-handling intact) cannot slip through undetected.

None of the five mechanisms requires touching the SQLite DB, the permission setting, or any
ledger row — the rail-state, credential, and calendar-scoping gates are all checked
independently of (and after) permission/dedupe, so killing any one of them is sufficient
regardless of what the permission setting or idempotency ledger currently say.

## Why Calendar needs a fifth mechanism that Gmail's shape only has as a fourth

Gmail SMTP auth needs two secrets (sender address, app password); Calendar's OAuth
refresh-token flow needs three (client ID, client secret, refresh token), each of which
independently gates the call to `GoogleCalendarClient.refresh_access_token`. On top of
that, exactly like Gmail's recipient-scoping gate, Calendar has its own controlled-calendar-
id gate: a calendar event is hard to fully undo — it can be deleted after creation, but an
attendee/notification recipient may already have seen it, which is the same one-way-door
concern the Gmail packet's recipient-scoping check exists for. That gate gets its own
independent kill switch (Mechanism 5) in addition to the rail-state and three credential
gates.
