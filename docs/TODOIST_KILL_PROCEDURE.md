# Todoist rail — exact kill steps

This document supplements `governance/RUNBOOK.md`'s generic "Kill procedures" section
(which stays as-is) with Todoist-specific detail: the exact two kill mechanisms as
concrete, numbered steps a human follows under pressure. Do either one; both are proven
independently by `tests/todoist_kill_drill.py`, run it first if unsure either still works.

Two independent mechanisms stop `create_live_todoist_task` (`src/personalos/rails/todoist.py`)
from making its next real HTTPS call. Either one alone is sufficient; you do not need to do
both, but doing both is not harmful.

**Mechanism 1 — flip the rail state off `"live"`** (fastest if you already have a Python
shell or a REPL open against the running process/host):
1. Open `src/personalos/status.py` and find the `_RAIL_STATES` dict (private literal near
   the top of the file, currently `{"todoist": "inert", "gmail": "inert", "calendar":
   "inert", "model_api": "inert"}`).
2. Change the `"todoist"` value from `"live"` to `"inert"` (or `"soaking"` — anything other
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
   deployment, not because of anything in the code: every Todoist-rail invocation right now
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
4. Verify: run `python3 tests/todoist_kill_drill.py` (no arguments, no network, no real
   credential needed) and confirm it prints `PASS` for `kill mechanism: rail_state_flip`.
   Note what this actually proves: the drill patches `_RAIL_STATES` in-process via
   `mock.patch.dict` and confirms the gate check correctly blocks a write once the value is
   not `"live"` — it proves the GATE LOGIC is correct. It does not and cannot exercise the
   restart/re-import behavior described in step 3 above (whether a real running process
   picks up a real on-disk file edit); that is a deployment/operational property, not
   something an in-process mock can observe. Trust step 3's reasoning for that half, not
   the drill.

**Mechanism 2 — remove the credential from the environment** (fastest if you don't have
file-edit access to the host but do control the environment the process reads, e.g. a
process manager, shell profile, or secrets store):
1. Find where `PERSONALOS_RAIL_TODOIST_TOKEN` is set for the process (host environment
   under Chris's account per `governance/RUNBOOK.md`'s invariant — never in a repo file,
   per `.env.example` and `governance/SECURITY.md`).
2. Unset it (`unset PERSONALOS_RAIL_TODOIST_TOKEN` in the shell that launches the process,
   or remove it from whatever process manager/secrets store injects it) and restart or
   re-launch the process so it reads the environment again.
3. The next `create_live_todoist_task` call reads `os.environ` fresh at call time (it is
   never cached) and finds the variable absent, refusing with
   `STATUS_BLOCKED_CREDENTIAL_MISSING` before constructing any HTTPS client. Setting the
   variable to an empty/whitespace-only value has the same fail-closed effect
   (`STATUS_BLOCKED_CREDENTIAL_EMPTY`) if unsetting it outright isn't convenient.
4. Verify: run `python3 tests/todoist_kill_drill.py` and confirm it prints `PASS` for
   `kill mechanism: credential_removal`.

Neither mechanism requires touching the SQLite DB, the permission setting, or any ledger
row — the rail-state and credential gates are checked independently of (and after)
permission/dedupe, so killing either one is sufficient regardless of what the permission
setting or idempotency ledger currently say.
