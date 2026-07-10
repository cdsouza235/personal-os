# RUNBOOK.md — Personal OS

## Invariant
**No agent ever holds production credentials.** Live-rail runtime uses credentials from the
host environment under Chris's account; agent sandboxes get name-only preflight.

## Run (current, inert)
```bash
PYTHONPATH=src python3 -m personalos.cli --help        # operator CLI
PYTHONPATH=src python3 -m personalos.cli dashboard serve --db <dev.sqlite>   # localhost only
```
Dev/test DBs are explicit `--db` paths; there is no production DB path configured (and
activating one is G4).

## Backup / restore (production DB, once one exists)
- Backup before every migration (runtime_bootstrap already implements backup-before-migrate).
- Backup = file copy of the SQLite DB with WAL checkpointed; restore = stop everything,
  replace file, run integrity check (`PRAGMA integrity_check`), re-run migrations idempotently.
- A restore drill is part of the production-DB activation packet's acceptance criteria (G4).

## Rollback (code)
Packet = branch; merge commits are `--no-ff`. Rollback = `git revert -m 1 <merge-commit>`
through a normal packet (audited). Never rewrite history on main.

## Kill procedures (live rails, post-activation)
- **Todoist / Gmail / Calendar adapter**: flip the rail's state from `live` in config/STATUS
  (each adapter checks state before every write — acceptance criterion of every P-RAIL
  packet); worst case, remove the credential from the environment — adapters must fail
  closed on missing credentials.

### Todoist rail — exact kill steps (do either one; both are proven independently by
### `scripts/todoist_kill_drill.py`, run it first if unsure either still works)

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
3. Save the file. Because `_RAIL_STATES` is read fresh from the module on every call to
   `create_live_todoist_task` (it reads `RAIL_STATES["todoist"]`, the immutable public view
   of the same dict), the very next invocation anywhere in the process sees the new value
   and refuses with `STATUS_BLOCKED_RAIL_STATE` — no restart required if the process
   re-imports/re-reads the module; if you are not certain the running process will pick up
   the edit without a restart, restart it. There is no config flag or database row to also
   update — the dict literal in this one file is the entire mechanism.
4. Verify: run `python3 scripts/todoist_kill_drill.py` (no arguments, no network, no real
   credential needed) and confirm it prints `PASS` for `kill mechanism: rail_state_flip`.

**Mechanism 2 — remove the credential from the environment** (fastest if you don't have
file-edit access to the host but do control the environment the process reads, e.g. a
process manager, shell profile, or secrets store):
1. Find where `PERSONALOS_RAIL_TODOIST_TOKEN` is set for the process (host environment
   under Chris's account per the invariant above — never in a repo file, per
   `.env.example` and `governance/SECURITY.md`).
2. Unset it (`unset PERSONALOS_RAIL_TODOIST_TOKEN` in the shell that launches the process,
   or remove it from whatever process manager/secrets store injects it) and restart or
   re-launch the process so it reads the environment again.
3. The next `create_live_todoist_task` call reads `os.environ` fresh at call time (it is
   never cached) and finds the variable absent, refusing with
   `STATUS_BLOCKED_CREDENTIAL_MISSING` before constructing any HTTPS client. Setting the
   variable to an empty/whitespace-only value has the same fail-closed effect
   (`STATUS_BLOCKED_CREDENTIAL_EMPTY`) if unsetting it outright isn't convenient.
4. Verify: run `python3 scripts/todoist_kill_drill.py` and confirm it prints `PASS` for
   `kill mechanism: credential_removal`.

Neither mechanism requires touching the SQLite DB, the permission setting, or any ledger
row — the rail-state and credential gates are checked independently of (and after)
permission/dedupe, so killing either one is sufficient regardless of what the permission
setting or idempotency ledger currently say.
- **Scheduler** (post P-SCHED activation): `launchctl unload` the LaunchAgent (exact label
  recorded in the activation packet's sign-off) — unload-proof is part of activation
  acceptance. No other background execution paths are permitted to exist.
- **Everything**: the DB is local; stopping the scheduler + nulling rail states returns the
  system to fully inert. Verify with the status CLI.

## Incident
Wrong external write (bad Todoist task / bad email / bad event): 1) kill the rail (above);
2) manually reverse the external artifact where the rail supports it (Todoist delete,
Calendar delete; email cannot be unsent — which is why Gmail soaks longest per the
activation ladder); 3) capture the ledger row + completion report into `audits/`;
4) the fix packet reproduces the failure from the ledger before changing code.
