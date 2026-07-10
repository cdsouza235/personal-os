# Gmail rail — exact kill steps

This document supplements `governance/RUNBOOK.md`'s generic "Kill procedures" section
(which stays as-is) with Gmail-specific detail: the exact THREE kill mechanisms as
concrete, numbered steps a human follows under pressure. Do any one of them; all three are
proven independently by `tests/gmail_kill_drill.py`, run it first if unsure any still
works.

Gmail has a different kill-mechanism shape than Todoist (`docs/TODOIST_KILL_PROCEDURE.md`,
two mechanisms): THREE independent mechanisms stop `send_live_gmail_message`
(`src/personalos/rails/gmail.py`) from making its next real SMTP call. Any one alone is
sufficient; you do not need to do more than one, but doing more than one is not harmful.
This is one more than Todoist because Gmail SMTP auth needs two secrets instead of one
(sender address + app password, either of which independently gates the send), and because
Gmail has a fifth safety gate — the controlled-recipient check — that Todoist has no
equivalent of.

**Mechanism 1 — flip the rail state off `"live"`** (fastest if you already have a Python
shell or a REPL open against the running process/host):
1. Open `src/personalos/status.py` and find the `_RAIL_STATES` dict (private literal near
   the top of the file, currently `{"todoist": "inert", "gmail": "inert", "calendar":
   "inert", "model_api": "inert"}`).
2. Change the `"gmail"` value from `"live"` to `"inert"` (or `"soaking"` — anything other
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
   deployment, not because of anything in the code: every Gmail-rail invocation right now
   is a fresh, short-lived CLI process (e.g. `personalos run morning`) — there is no
   long-running daemon or background process holding a stale import. So the very next
   invocation, whenever it happens, naturally starts a new process, imports the file fresh,
   and sees the edited value — there is nothing to restart because nothing long-running is
   running. **If a background/daemon mode has since landed (see `P-SCHED-02` in
   `governance/ROADMAP.md`), re-verify this assumption before relying on it** — a genuinely
   long-running process would need an explicit restart, and this paragraph would need to be
   updated to say so plainly rather than silently going stale.

   There is no config flag or database row to also update — the dict literal in this one
   file is the entire mechanism.
4. Verify: run `python3 tests/gmail_kill_drill.py` (no arguments, no network, no real
   credential or real email address needed) and confirm it prints `PASS` for
   `kill mechanism: rail_state_flip`. Note what this actually proves: the drill patches
   `_RAIL_STATES` in-process via `mock.patch.dict` and confirms the gate check correctly
   blocks a send once the value is not `"live"` — it proves the GATE LOGIC is correct. It
   does not and cannot exercise the restart/re-import behavior described in step 3 above
   (whether a real running process picks up a real on-disk file edit); that is a
   deployment/operational property, not something an in-process mock can observe. Trust
   step 3's reasoning for that half, not the drill.

**Mechanism 2 — remove EITHER credential from the environment** (fastest if you don't have
file-edit access to the host but do control the environment the process reads, e.g. a
process manager, shell profile, or secrets store). Gmail SMTP auth needs two secrets, not
one — `send_live_gmail_message` checks both env vars every call and fails closed if either
is missing or empty, so removing just one is enough:
1. Find where `PERSONALOS_RAIL_GMAIL_SENDER_ADDRESS` and/or
   `PERSONALOS_RAIL_GMAIL_APP_PASSWORD` are set for the process (host environment under
   Chris's account per `governance/RUNBOOK.md`'s invariant — never in a repo file, per
   `.env.example` and `governance/SECURITY.md`).
2. Unset either one (`unset PERSONALOS_RAIL_GMAIL_SENDER_ADDRESS` or
   `unset PERSONALOS_RAIL_GMAIL_APP_PASSWORD` in the shell that launches the process, or
   remove it from whatever process manager/secrets store injects it) and restart or
   re-launch the process so it reads the environment again. You do not need to remove both.
3. The next `send_live_gmail_message` call reads `os.environ` fresh at call time (never
   cached) and finds the variable absent, refusing with `STATUS_BLOCKED_CREDENTIAL_MISSING`
   before constructing any SMTP client. Setting either variable to an empty/whitespace-only
   value has the same fail-closed effect (`STATUS_BLOCKED_CREDENTIAL_EMPTY`) if unsetting it
   outright isn't convenient.
4. Verify: run `python3 tests/gmail_kill_drill.py` and confirm it prints `PASS` for both
   `kill mechanism: sender_credential_removal` and `kill mechanism: app_password_removal`
   (the drill proves each credential independently sufficient).

**Mechanism 3 — remove or change the controlled-recipient env var** (unique to Gmail; no
Todoist equivalent). This is a fifth safety check layered after the four fixed gates (see
the "Recipient scoping" section of `src/personalos/rails/gmail.py`'s module docstring):
`send_live_gmail_message` only ever sends to the single address named by
`PERSONALOS_RAIL_GMAIL_CONTROLLED_RECIPIENT`, and refuses if that env var is absent, empty,
or doesn't exactly match the message's `to_address`.
1. Find where `PERSONALOS_RAIL_GMAIL_CONTROLLED_RECIPIENT` is set for the process (same
   host-environment location as the credentials above).
2. Unset it, or change its value to anything other than the address the rail is currently
   configured to send to, and restart or re-launch the process so it reads the environment
   again.
3. The next `send_live_gmail_message` call reads the env var fresh at call time and either
   finds it absent/empty or finds it no longer matches the outgoing `to_address`, refusing
   with `STATUS_BLOCKED_RECIPIENT_NOT_CONTROLLED` before constructing any SMTP client. This
   works even if both credentials from Mechanism 2 are still valid and present — it is a
   fully independent gate, not a fallback of the credential check.
4. Verify: run `python3 tests/gmail_kill_drill.py` and confirm it prints `PASS` for
   `kill mechanism: controlled_recipient_removal`.

None of the three mechanisms requires touching the SQLite DB, the permission setting, or
any ledger row — the rail-state, credential, and recipient-scoping gates are all checked
independently of (and after) permission/dedupe, so killing any one of them is sufficient
regardless of what the permission setting or idempotency ledger currently say.

## Why email needs a third mechanism that Todoist doesn't

Todoist task creation is at least manually reversible (delete the bad task after the fact).
Email is not — once `GmailSmtpClient.send_message` returns a confirmed success, the message
cannot be unsent. The controlled-recipient gate (Mechanism 3) exists specifically because a
stray outbound email to an uncontrolled address is the one failure mode this rail cannot
recover from after the fact, so it gets its own independent kill switch in addition to the
rail-state and credential gates that Todoist also has.
