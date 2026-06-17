# Production DB Policy

## Purpose

This policy defines the requirements before any production SQLite database can
be activated for Personal OS. It is documentation and policy design only. It
does not approve a production DB path, add migrations, run migrations, create
runtime artifacts, or activate production state.

Production SQLite activation requires separate explicit Chris approval.
The future [Activation Checklist](ACTIVATION_CHECKLIST.md) must also be
completed before any production DB path is approved or used for a live pilot.

## Environment Classes

Personal OS distinguishes these SQLite environments:

- Test DB: created by automated tests or disposable local checks.
- Dev DB: explicit local development database used for repo-local validation.
- Local preview DB: explicit safe local database used for no-send/manual
  preview workflows.
- Restore-test DB: a restored backup copy used to verify recovery.
- Production DB: the approved runtime SQLite database used by the Mac Mini
  runtime and live/operator workflows.

Approval for one environment does not authorize another. Dev/test/local
preview databases are not production databases.

## Default State

Production DB activation is disabled by default. No repo command, migration
helper, bootstrap helper, scheduler, dashboard, CLI command, OpenClaw workflow,
or live rail may infer a production DB path.

Every production operation must require an explicit approved path and fail
closed otherwise.

## Explicit Production DB Path Approval

Before production activation, Chris must approve:

- Exact production DB path.
- Runtime host.
- Owner/operator.
- Allowed commands or workflows.
- Backup destination.
- Restore-test destination.
- Migration version/commit.
- Rollback condition.
- Evidence required after the operation.

The production path must be approved by path, not by vague labels such as
latest DB, runtime DB, or default DB.

The activation checklist must capture the approved path, backup destination,
restore-test destination, migration plan, integrity-check plan, rollback
condition, and completion-report evidence before any production DB mutation.

## Protected Paths

Protected paths remain off limits unless explicitly approved for the exact
operation:

- `/Users/coldstake/PersonalOS`
- `/Users/coldstake/.openclaw`
- LaunchAgents
- Credentials and OAuth material
- Production ledgers
- Existing production SQLite state
- Any other runtime state outside the approved DB path

Repository-local runtime artifacts are prohibited. Production DB files,
backups, WAL files, SHM files, ledgers, and runtime `var/` folders must not be
created inside this repository.

## Migration Policy

Production migrations require:

- A clean, reviewed repo commit.
- Identified migration files.
- Checksum verification for existing migration metadata.
- A migration preview or plan.
- Backup before mutation.
- Restore verification before live migration.
- Integrity checks before and after the approved operation.
- Rollback or roll-forward plan bound to the approved path.
- SQLite foreign key enforcement.
- Completion report after the attempt.

Migrations must be applied through the approved migration system, not by ad
hoc SQL pasted into a shell.

## Backup Before Migration

Before any production DB mutation:

- Create a timestamped backup.
- Confirm backup file existence.
- Record source and backup metadata.
- Keep the backup outside the repo.
- Avoid printing sensitive content.
- Preserve the backup until Chris approves cleanup.

If backup creation fails, the migration must stop.

## Restore Verification

Before first production activation, and before risky migrations, the operator
must restore the backup into a separate safe restore-test path and verify:

- The restored DB opens.
- `PRAGMA integrity_check` returns `ok`.
- Migration metadata is readable.
- Expected core tables exist.
- Sanity counts are plausible.
- No production DB file was modified during the restore test.

Restore verification evidence must be included in the completion report.

## File Permissions

Production DB file permissions must be narrow enough for the approved runtime
operator and host. The policy for the specific activation must document:

- Owning user.
- Owning group if relevant.
- File mode expectations.
- Directory mode expectations.
- Backup file permissions.
- Whether WAL/SHM sidecar files are expected.

Secrets must not be stored in SQLite unless a future explicit credential
policy allows it.

## Locking And Concurrency

Before production activation, the runtime design must state:

- Whether one process or multiple processes may open the DB.
- Whether WAL mode is used.
- Busy timeout behavior.
- Transaction boundaries for write operations.
- Scheduler/background loop concurrency expectations.
- Operator behavior when the DB is locked.

Live rails must not assume writes succeeded when SQLite reports lock,
transaction, or integrity errors.

## Checksum And Integrity Checks

Production DB operations must include appropriate integrity checks:

- Migration checksum verification.
- `PRAGMA integrity_check`.
- Foreign key enforcement and, where useful, `PRAGMA foreign_key_check`.
- Schema version/migration metadata review.
- Table/count sanity checks for affected modules.

Checksum mismatch, failed integrity check, or unexpected schema state must
stop mutation and escalate to Chris.

## Rollback Behavior

Every production DB operation must state rollback behavior before mutation:

- Restore from backup.
- Roll forward with a corrective migration.
- Mark a run failed and leave state unchanged.
- Stop and escalate when rollback is unsafe.

If a transaction fails, the completion report must state whether SQLite rolled
back the transaction and what verification was performed.

## Audit And Event Logging

Production DB operations must produce audit evidence:

- Operator.
- Runtime host.
- Repo commit.
- DB path label.
- Operation.
- Migration version if applicable.
- Backup path label.
- Restore-test result if applicable.
- Integrity check result.
- Started/completed timestamps.
- Outcome.
- Error or escalation notes.

Where the active schema supports it, system event records should be written
for approved production operations. If the schema cannot safely record the
event, the completion report must explain where evidence is stored instead.

## Prohibited Behavior

The following remain prohibited until explicitly approved in a later phase:

- Implicit production DB path discovery.
- Production DB mutation from a repo-local `var/` path.
- Creating production runtime artifacts inside this repo.
- Running unreviewed SQL against production.
- Applying migrations without backup.
- Treating a successful backup as restore verification.
- Running scheduler/live rails against production DB before activation.
- Printing credentials or protected data in DB reports.
- Using OpenClaw production DB workflows without an approved handoff.
