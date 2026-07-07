# PR #96 Audit — Phase 14-C live-smoke diagnostics + safe failure metadata

- Branch: `phase-14c-smoke-diagnostics`
- Head: `f2237d613586187b91b7fce9e4379328bd5da731`
- Base: `origin/main` @ `87168fd` (after PR #95 merge)
- Reviewer: Claude Code `/code-review` (high effort, recall-biased)
- Scope: `git diff main...HEAD` (14 files, +493 / -19)

## Verdict

**Clean — approved for merge.** No correctness, safety, or leakage findings. Adds a fully inert
diagnostics command plus safe failure-classification metadata (`error_kind`/`http_status`) with
correct exception handling and no new exposure. One non-blocking cleanup nit.

## Findings

### 1. (Low / cleanup, non-blocking) `_safe_error_kind` duplicated
`phase14c_todoist_live_smoke.py:301` and `openrouter_model_smoke_client.py:144` now both define
the same URLError-reason class-name extractor. Two copies to keep in sync (joins the existing
`_config_names_only` duplication family). Promote to a shared util.

## Verified OK

- **Exception ordering correct in both clients.** `HTTPError → JSONDecodeError → URLError →
  (OSError, ValueError)`: every subclass precedes its parent, no unreachable `except`, and the
  caught-exception union is identical to before the split (nothing newly escapes).
- **No new leakage.** `error_kind` is a class name only (`_safe_error_kind` returns
  `reason.__class__.__name__` — no host/IP/message); `http_status` is an int. Both added to the
  `SAFE_METADATA_FIELDS` allowlist so `sanitize_openclaw_model_run_metadata` passes them through.
  Todoist `_safe_failure` keeps the fixed generic `message` (no `str(error)`), consistent with the
  PR #94 Gmail redaction fix.
- **Resource hygiene.** `error.close()` added for the file-like `HTTPError` in both clients;
  non-HTTP branches have nothing to close.
- **Mutation semantics preserved.** Todoist `HTTPError` routes to
  `mutation_state=unconfirmed_after_task_create_attempt` (cautious/correct; same outcome as
  before, now carrying `http_status`/`error_kind`).
- **Diagnostics command is genuinely inert.** `build_phase14c_live_smoke_diagnostics_report()` is a
  pure constant builder (imports only `SAFE_METADATA_FIELDS` and `PHASE14C_TODOIST_TASK_TITLE`; no
  `os`/`urllib`/file I/O). The CLI handler sets all no-credential / no-live-client / no-mutation
  flags and emits a static report (exit 0).
- **Import correctly isort-ordered** (`gmail → live_smoke_diagnostics → supervised`).
- **No PII/secrets** in docs or source (tree-wide sweep clean). Docs consistently describe
  `error_kind`/`http_status` as safe fields and the manual-Todoist-check-before-retry requirement.
- **Tests** — focused modules pass locally (34 OK via unittest). `ruff` not installable in this
  environment (consistent with author note); import order verified by inspection.

## Test status (per PR)

- Targeted diagnostics/client/CLI/docs suite: 97 OK
- Full suite: 754 OK; ResourceWarning suite: 754 OK
- Readiness still `not_ready` / `inert_report_only=true`
