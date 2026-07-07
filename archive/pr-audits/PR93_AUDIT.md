# PR #93 Audit — Phase 14-C gated live smoke clients (Todoist + OpenRouter)

- Branch: `phase-14c-live-smoke-clients`
- Head: `16b3a7cbb8c91f95bedb895b1cd568924b94a151` (original) → `76e920270db2af6aedc6304d8a98f5e76bc37ad6` (re-audited)
- Base: `origin/main` @ `bde2eea` (after PR #92 merge)
- Reviewer: Claude Code `/code-review` (high effort, recall-biased)
- Scope: `git diff main...HEAD` (13 files, +1273 / -38)

## Re-audit (head `76e9202`) — APPROVED FOR MERGE

Follow-up re-audited as a focused delta (`16b3a7c..76e9202`, 7 files / +82 / -14). All findings resolved or accepted; no regressions; no new findings.

- **Finding 1 (Medium) — FIXED.** Introduced `mutation_state` with three honest states
  (`not_attempted` / `unconfirmed_after_task_create_attempt` / `confirmed_task_created`).
  `_todoist_safety_assertions` now takes `todoist_task_created` separately (`bool | None`)
  instead of aliasing `external_mutation`. On post-send failure both fields are `None`, and the
  CLI propagates `external_mutation: null` (not `false`) when
  `task_create_calls==1 and mutation_state=="unconfirmed_after_task_create_attempt"`. Top-level
  CLI fields are now mutually consistent (`external_mutation: null`,
  `external_writes: "todoist_task_create_attempted"`, `no_external_writes: false`).
- **Finding 2 (pre-live) — RESOLVED.** `due_date` (`YYYY-MM-DD`) verified against Todoist API v1
  `POST /api/v1/tasks`; recorded in `docs/PHASE_14C_SUPERVISED_SMOKE_TEST.md` and asserted by a
  docs test.
- **Finding 3 (cleanup) — DEFERRED (nonblocking).** Duplicate `_config_names_only` helper left
  as an accepted nit.
- **New test:** `_FailingAfterAttemptTodoistClient` records the payload (POST sent) then raises,
  simulating create-succeeds/parse-fails; asserts `None` mutation fields, unconfirmed
  `mutation_state`, and no token leak in the serialized report.
- **No regressions:** `{**report}` spread still preserves the new `external_mutation: null`;
  `not_attempted` early-return paths keep `mutation_state` from `base` (no false attempt claim).
- Validation per PR: focused 83 OK, full 740 OK, ResourceWarning 740 OK; readiness still
  `not_ready` / `inert_report_only=true`.

**Verdict: clean — approved for merge.**

---

## Original audit (head `16b3a7c`)

## Verdict

**Approve with one assertion fix before any live run.** No credential leak and no
unauthorized live path. The default report-only contract holds and is genuinely names-only.
One nested safety-assertion can over-claim "no mutation" on a rare failure path (finding 1);
fix it before the first live Todoist run. Findings 2–3 are a pre-live verification note and a
cleanup nit.

## Findings

### 1. (Medium) FAILED-after-POST over-claims `external_mutation: False`
`phase14c_todoist_live_smoke.py` (~L776): when `create_task` POSTs successfully but the
client-side `response.read()`/`json.loads` raises, or the body is not a Mapping, the `except`
branch returns `safety_assertions.external_mutation=False` and `todoist_task_created=False` —
even though Todoist may have already created the task server-side. The CLI wrapper is more
honest (`external_writes="todoist_task_create_attempted"`, `no_external_writes=False` when
`task_create_calls==1`), so the nested smoke report contradicts the wrapper.

Suggested fix: on a post-send failure, report `external_mutation`/`todoist_task_created` as
unknown/indeterminate (e.g. a `mutation_state: "unconfirmed"` field) rather than a hard `False`.

### 2. (Low / pre-live verification) Confirm Todoist v1 `due_date` field
`phase14c_todoist_live_smoke.py` (~L805): `build_phase14c_todoist_task_payload` sends
`{"content", "due_date"}` to `https://api.todoist.com/api/v1/tasks`. REST v2 used `due_date`;
confirm the unified v1 API accepts the same field (vs `due_string` / a `due` object). If wrong,
the first live task is created with no due date or the call 400s. Not executed in this PR.

### 3. (Low / cleanup) `_config_names_only` duplicated again
`phase14c_todoist_live_smoke.py` (~L890) re-implements the same Iterable/Mapping name extractor
already in `phase14c_connectivity_setup.py`. Now a 4th copy across phase14c modules — promote to
a shared util.

## Verified OK

- `model_alias` keys sent by `_run_one_model_probe` (`nemotron_super` / `glm_5_2`) match the
  `OpenRouterModelSmokeClient.models_by_alias` keys — alias contract is consistent.
- `response_text` is NOT in `SAFE_METADATA_FIELDS`; `sanitize_openclaw_model_run_metadata`
  drops it, so raw provider responses are never emitted.
- GLM 5.2 fallback fires only when primary validation fails (`run_openclaw_model_smoke_probe`).
- API key / Todoist token appear only in the `Authorization: Bearer` header — never logged,
  returned, or committed.
- Credentials are read only behind `--execute-live` AND `--approval-reference` AND
  names-present AND values-present; report-only paths never call `_openrouter_env_values()`.
- Empty-but-present token/values are caught (missing_config / missing_provider_config) with
  `credential_values_read` reported truthfully.
- `_with_workflow_context` `{**report}` spread preserves the new commands' fields; the
  external_writes/credentials/production_db_active default change is backward-compatible for
  existing callers (none set those keys).
- Bounded call limits enforced: max 1 Todoist task; max 1 primary + 1 fallback model call.
- HTTPError (subclass of URLError/OSError) is caught; http_status preserved for the model client.
- No DB opened, no files written, no scheduler activated, no protected paths touched.

## Test status (per PR)

- Focused suite: 82 OK
- Full suite: 739 OK; ResourceWarning suite: 739 OK
- Readiness still `not_ready`, `inert_report_only=true`
