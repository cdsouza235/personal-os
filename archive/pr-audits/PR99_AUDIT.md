# PR #99 Audit — Phase 14-C connected rehearsal executable gate (live runner)

- Branch: `phase-14c-connected-rehearsal-executor`
- Head: `53b45d929c500165002f3a056e33f1d3677bcb93` (original) → `95e84110ca75edace78134d639113926b991e8c9` (re-audited)
- Base: `origin/main` @ `9ea3a57` (after PR #98 merge)
- Reviewer: Claude Code `/code-review` (high effort, recall-biased)
- Scope: `git diff main...HEAD` (13 files, +1222 / -8)

## Re-audit (head `95e8411`) — APPROVED FOR MERGE

Fix re-audited as a focused delta (`53b45d9..95e8411`, 5 files / +50 / -8). Finding 1 resolved;
no regressions; no new findings.

- **Finding 1 (Low) — FIXED.** `_connected_due_date` now uses `source_date`: keeps the planned
  `2026-07-06` while `planned >= today`, otherwise rolls to `next_upcoming_monday(today)`. Dead
  branch removed; parameter now meaningful. Verified live across boundaries:
  `2026-06-30 → 2026-07-06`, `2026-07-06 → 2026-07-06` (due-today kept), `2026-07-07 → 2026-07-13`,
  `2026-07-13 → 2026-07-20` (stale Monday rolls strictly forward, no same-day). Regression test
  added.
- **Finding 2 (Low / cleanup) — partially reduced, still deferred.** The fix reuses the existing
  `next_upcoming_monday` helper instead of re-implementing, trimming the duplication. Remaining
  duplicated helpers (`_config_names_only`/`_optional_email`/`_safe_failure`/`_EMAIL_RE`) left as a
  non-blocking nit.
- Member import order remains valid (`CONST, Class, function` under ruff order-by-type). Focused
  tests pass locally (12 OK). Safety envelope from the original audit is unchanged by this delta.

**Verdict: clean — approved for merge.** (The eventual live run still requires a fresh explicit
approval per the plan's own precondition.)

---

## Original audit (head `53b45d9`)

## Verdict

**Approve with the dead-code cleanup recommended before the live run.** This is the highest-risk
PR in the series (the actual model→task→email live runner reading real credentials), and the
safety envelope holds: airtight gating, bounded budgets, chain-stops-on-failure with honest
mutation state, and no brief/credential/email leakage. Two Low findings; neither compromises safety.

## Findings

### 1. (Low) Dead `_connected_due_date`; Todoist due date is hardcoded
`phase14c_connected_rehearsal_live.py:434` —
```
def _connected_due_date(source_date):
    if source_date is None:
        return PHASE14C_CONNECTED_REHEARSAL_DUE_DATE
    return PHASE14C_CONNECTED_REHEARSAL_DUE_DATE
```
Both branches return the same constant; `source_date` is ignored. The live Todoist task is pinned
to `2026-07-06`. If the approved run happens on/after 2026-07-07, the task is created with a
past-due date (unlike the Todoist smoke, which uses `next_upcoming_monday`). Tests passing
`source_date` cannot detect this. Fix: remove the dead param/branch, or actually derive the date.

### 2. (Low / cleanup, non-blocking) Helper duplication
`phase14c_connected_rehearsal_live.py:636` (and `_optional_string`/`_optional_email`/`_safe_failure`/
`_EMAIL_RE`) re-implement helpers already in the gmail/todoist modules — the recurring nit, now the
largest instance. Promote to a shared util so email-regex/redaction stay consistent.

## Verified OK (safety-critical)

- **Airtight, defense-in-depth gating.** Credential VALUES are read only when
  `execute_live AND exact approval-reference match (phase14c-2026-07-01-connected-rehearsal) AND
  all required config names present` — enforced at both the CLI (before `os.environ.get` of values)
  and the runner. Missing/empty values and a non-`openrouter` provider short-circuit before any
  live call, with `credential_values_read` reported truthfully.
- **Bounded budgets enforced structurally.** 1 OpenRouter primary, ≤1 fallback (only on primary
  validation failure), 1 Todoist create, 1 Gmail send; no loops/retries; Calendar / protected
  OpenClaw runtime / scheduler / production DB fixed at 0.
- **Chain stops on failure with honest state.** Model fail → no Todoist/Gmail. Todoist fail → no
  Gmail (`mutation_state=unconfirmed_after_task_create_attempt`, `external_mutation: null`). Gmail
  fail after Todoist success → `todoist_created_gmail_unconfirmed_after_send_attempt`,
  `gmail_email_sent: null`. PR #93/#94 unconfirmed-mutation lessons correctly applied.
- **No leakage.** Model brief text is stripped from `model.attempts` and never emitted (only
  line/char counts, `brief_text_logged: False`). `_safe_failure` returns a fixed redacted message
  (no `str(error)`), so SMTP/HTTP exceptions cannot leak email addresses. Results are
  field-allowlisted (`_sanitize_todoist_result`/`_sanitize_gmail_result`); no emails or credentials
  in the report. Tree-wide sweep clean.
- **Model-output content filter.** `_validated_brief` rejects briefs containing
  secret/password/token/api-key/`.env`/oauth/`/users/coldstake` fragments, `@`, or `http(s)` links,
  and caps at 3 lines / 160 chars before the text reaches the task/email body.
- **Correct exception ordering** (`HTTPError` before generic `(OSError, ValueError,
  JSONDecodeError, URLError)`), `error.close()` on the file-like `HTTPError`, import correctly
  isort-ordered (`connected_rehearsal → connected_rehearsal_live → connectivity_setup`).
- Focused executor/CLI/docs/model tests pass locally (29 OK); readiness unchanged
  (`not_ready` / `inert_report_only=true` / `live_rails_activated=false`).

## Note for the eventual live run

Per the plan's own precondition, the live run itself still requires the new explicit approval plus
this audit. Recommend fixing finding 1 before that run so the created task's due date is not stale.

## Test status (per PR)

- Focused connected rehearsal executor/CLI/docs/model suite: 95 OK
- Full suite: 768 OK; ResourceWarning suite: 768 OK
- Readiness still `not_ready` / `inert_report_only=true` / `live_rails_activated=false`
