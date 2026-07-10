# Production DB restore drill

This document is P-SCHED-02's own acceptance criterion per D-PO-011
(`governance/living/agent-writable/DECISIONS.md`): concrete, numbered steps a human
follows to back up and restore the production Personal OS database at
`/Users/coldstake/PersonalOS/personal_os.db`. It supplements
`governance/RUNBOOK.md`'s generic "Backup / restore (production DB, once one exists)"
section (which stays as-is) with the exact commands.

**Nothing in this document has been run against the real production path.** No production
database exists yet at the time this document was written (HI-10, Mac Mini launchd
authorization, is still pending — see `audits/human-input-manifest.md`). This is a
procedure for Chris to follow once the database exists and the scheduler is loaded for
real, not something any packet or test executes.

## Why the SQLite Online Backup API, not a filesystem copy

Per D-PO-011: a raw filesystem copy (`cp`, `shutil.copyfile`, etc.) risks capturing a
torn/inconsistent snapshot if a write is in progress when the copy happens (SQLite may
have a WAL file with uncommitted or partially-committed pages at that instant). SQLite's
own Online Backup API produces a byte-consistent copy regardless of concurrent activity,
because it copies through SQLite's own page-level machinery rather than the filesystem.
Time Machine (or an equivalent Mac backup) remains a *secondary* safety net for
catastrophic disk loss, not the primary defense against backup corruption — use the
Online Backup API as the primary mechanism.

## Taking a backup

Run this on a schedule (e.g. before every scheduled `run morning` invocation touches the
database, and/or on its own daily/weekly cadence — exact cadence is Chris's operational
choice, not fixed by this packet). Two equivalent invocations; pick whichever is more
convenient at the time.

**Command-line (`sqlite3` shell), using its built-in `.backup` dot-command:**

```bash
sqlite3 /Users/coldstake/PersonalOS/personal_os.db \
  ".backup '/Users/coldstake/PersonalOS/backups/personal_os-$(date -u +%Y%m%dT%H%M%SZ).backup'"
```

The destination directory (`/Users/coldstake/PersonalOS/backups/` above, or wherever
Chris chooses to keep backups) must exist first — `.backup` does not create parent
directories.

**Python (`sqlite3.Connection.backup()`), equivalent invocation:**

```python
import sqlite3
from datetime import UTC, datetime

source_path = "/Users/coldstake/PersonalOS/personal_os.db"
backup_path = (
    "/Users/coldstake/PersonalOS/backups/"
    f"personal_os-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.backup"
)

source_connection = sqlite3.connect(source_path)
destination_connection = sqlite3.connect(backup_path)
try:
    source_connection.backup(destination_connection)
finally:
    destination_connection.close()
    source_connection.close()
```

`Connection.backup()` is the Python standard library's binding to the exact same SQLite
Online Backup API the `sqlite3` shell's `.backup` command uses underneath — both produce
an equivalent, internally consistent copy.

## Restoring from a backup

Follow these steps in order. Do not skip the integrity check or the post-restore
migration re-run.

1. **Stop the scheduler.** `launchctl unload` the LaunchAgent (exact label
   `com.personalos.morning` — see `docs/com.personalos.morning.plist` and
   `tests/production_scheduler_kill_drill.py`). Confirm it is actually unloaded with
   `launchctl list | grep com.personalos.morning` (no output means it is not loaded).
   This prevents a scheduled run from writing to the database mid-restore.

2. **Pick the backup snapshot to restore from** (one of the `.backup` files produced by
   the "Taking a backup" section above — pick the most recent good one, or an earlier one
   if the most recent is itself known-bad).

3. **Verify the backup snapshot's integrity before trusting it:**

   ```bash
   sqlite3 /Users/coldstake/PersonalOS/backups/personal_os-<timestamp>.backup \
     "PRAGMA integrity_check;"
   ```

   This must print exactly `ok`. If it does not, that snapshot is not safe to restore
   from — try an earlier one.

4. **Move the current (possibly corrupt/bad) live database aside** — do not delete it,
   it may be useful for forensics:

   ```bash
   mv /Users/coldstake/PersonalOS/personal_os.db \
      /Users/coldstake/PersonalOS/personal_os.db.pre-restore-$(date -u +%Y%m%dT%H%M%SZ)
   ```

5. **Restore the chosen backup snapshot into the live path, using the same Online Backup
   API mechanism used to take it** (backup *from* the validated snapshot file *into* a
   fresh connection at the live production path — not a raw filesystem copy, for the same
   torn-snapshot-avoidance reason as the forward direction):

   **Command-line:**

   ```bash
   sqlite3 /Users/coldstake/PersonalOS/backups/personal_os-<timestamp>.backup \
     ".backup '/Users/coldstake/PersonalOS/personal_os.db'"
   ```

   **Python, equivalent invocation:**

   ```python
   import sqlite3

   backup_path = "/Users/coldstake/PersonalOS/backups/personal_os-<timestamp>.backup"
   restored_path = "/Users/coldstake/PersonalOS/personal_os.db"

   backup_connection = sqlite3.connect(backup_path)
   restored_connection = sqlite3.connect(restored_path)
   try:
       backup_connection.backup(restored_connection)
   finally:
       restored_connection.close()
       backup_connection.close()
   ```

6. **Run an integrity check on the restored live database:**

   ```bash
   sqlite3 /Users/coldstake/PersonalOS/personal_os.db "PRAGMA integrity_check;"
   ```

   Must print `ok`. If it does not, the restore failed — move the current file aside
   again, go back to step 2, and try a different (earlier) snapshot.

7. **Re-run schema migrations idempotently** — the restored snapshot may predate
   migrations applied since it was taken; `apply_migrations()`
   (`src/personalos/db/migrations.py`) is safe to call against an already-migrated
   database (it records applied versions and skips them). Either use
   `personalos.config.bootstrap_production_database()` (added by P-SCHED-02, schema-only,
   no seed data), or call `apply_migrations()` directly against a connection opened on
   the restored path.

8. **Verify with the status CLI** before resuming the scheduler, per
   `governance/RUNBOOK.md`'s "Everything" kill-procedure line
   (`personalos status --db /Users/coldstake/PersonalOS/personal_os.db`).

9. **Resume the scheduler** (`launchctl load` the LaunchAgent) only once 6–8 above are
   all confirmed good. This is the same kind of deliberate, Chris-only action as the
   original load — this document does not authorize it, it just describes the step for
   when Chris performs it himself.

## What this drill does NOT cover

- It does not automate backup scheduling (cron/launchd for backups themselves is a
  separate operational decision, not part of the one `com.personalos.morning` LaunchAgent
  this packet authors).
- It does not replace Time Machine as a disk-loss safety net — it is the primary defense
  against a *corrupted or torn backup*, not the only backup mechanism in place.
