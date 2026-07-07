# PR #102 Audit — Phase 14-C wide-net executable gate (fail-closed runner)

- Branch: PR #102 head `3008a75fbd68ec0e0d449de5ec59f222427de725`
- Base: `origin/main` @ `3212b60` (after PR #101 merge)
- Reviewer: Claude Code `/code-review` (high effort, recall-biased)
- Scope: `git diff main...HEAD` (16 files, +1422 / -43)

## Verdict

**Approve for merge — the fail-closed gate is correct and safe.** `--execute-live` reads no
credentials and makes no live call because there is no audited Calendar bridge yet. Finding 1 is a
Medium design gap that is NOT active now (fail-closed) but must be resolved in the Calendar bridge
PR. Finding 2 is Low.

## Findings

### 1. (Medium, deferred to bridge PR) No Calendar duplicate-marker precheck
`phase14c_wide_net_rehearsal_live.py:280` — the runner calls `calendar_client.create_event(payload)`
directly with no precheck, and the `WideNetCalendarClient` Protocol exposes only `create_event`
(no read/search). PR #101's plan mandates `duplicate_marker_precheck_required: True` and a stop
condition for a pre-existing marker event. As written, once the audited Calendar bridge is wired in,
a rerun or post-partial-failure retry would create a DUPLICATE self-only marker event. Not active
now (fail-closed: no calendar client exists). Resolve in the bridge PR: extend the Protocol with a
marker search/list read + precheck logic in the runner, or make dedup a verified bridge guarantee.

### 2. (Low) `_safe_failure` drops `http_status`; Calendar HTTPError not closed
`phase14c_wide_net_rehearsal_live.py:672` — this `_safe_failure` returns only type+message, dropping
the `http_status` that the connected/todoist versions record for HTTPError (the PR #96 diagnostic
specifically added to surface 402/spend blockers — the exact failure mode seen last run). Separately,
the Todoist branch calls `error.close()` on HTTPError but the Gmail/Calendar generic `except`
branches do not, leaving a file-like HTTPError response unclosed. Both Low; calendar path inert until
the bridge exists.

(Recurring non-blocking nit: `_config_names_only`/`_optional_string`/`_optional_email`/`_safe_failure`
duplicated again — promote to a shared util.)

## Verified OK (safety-critical)

- **Fail-closed before credentials, at both layers.** CLI hardcodes `calendar_client_available =
  False`, so `env_values` stays `None` (no `os.environ` value reads) and no `calendar_client` is
  passed; the runner returns `WIDE_NET_NOT_RUN_MISSING_CALENDAR_CLIENT` before
  `credential_values_read = True`. Traced both handlers: `--execute-live` + exact approval + all
  names + sourced `.env.local` still reads no credentials and makes no live call.
- **Gating order** — execute-live → approval present → EXACT approval match → config names present →
  calendar client present → non-empty values → provider==openrouter; each short-circuits before the
  next; credentials read only after all pass.
- **Bounded budgets & chain-stop** — 1 model primary + ≤1 fallback, 1 Todoist, 1 Gmail, 1 Calendar.
  Todoist fail → stop; Gmail fail → stop (Todoist kept); Calendar fail → Todoist+Gmail kept, calendar
  unconfirmed. Honest `mutation_state`/`external_mutation: null` per step.
- **Model is diagnostic-only** — `model_output_drives_external_writes: False`; model text never used
  in task/email/calendar payloads (fixed marker only); model-validation failure yields
  `WIDE_NET_PASSED_WITH_MODEL_DIAGNOSTIC_FAILURE` without blocking rails — matches the plan.
- **Calendar payload bounded** — `calendar_id: primary`, 0 attendees, no Meet, no recurrence, no
  attachments, 15 min; report carries only `_redacted_calendar_payload` (counts/booleans, no
  addresses).
- **No leakage** — no email addresses in the report (absent, not just masked); model metadata
  sanitized (no response_text); `_safe_failure` fixed redacted message (no `str(error)`); results
  field-allowlisted. Tree-wide sweep clean.
- **Correct exception ordering** (`HTTPError` before generic), import correctly isort-ordered
  (`...wide_net_rehearsal → wide_net_rehearsal_live`); focused tests pass locally (18 OK); readiness
  unchanged (`not_ready` / `inert_report_only=true` / `live_rails_activated=false`).

## Note for the Calendar bridge PR (next step)

Wiring a real `calendar_client` flips `calendar_client_available` to True and un-gates credential
reads + live calls. That PR must: (a) implement Finding 1's duplicate-marker precheck, (b) get its
own pre-run audit + fresh explicit approval, and (c) top up OpenRouter balance (prior run 402'd,
though here it only affects the diagnostic-only model step, not the rails).

## Test status (per PR)

- Focused wide-net executor/CLI/docs/model suite: 99 OK
- Full suite: 784 OK; ResourceWarning suite: 784 OK
- Readiness still `not_ready` / `inert_report_only=true` / `live_rails_activated=false`
