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
