# PR #94 Audit — Phase 14-C gated Gmail SMTP self-send smoke

- Branch: PR #94 head `47a98993c772b82bc24c075f942a28ac266f25e2` (original) → `3f2392122b6262f9d995f8c42c11549155fcc829` (re-audited)
- Base: `origin/main` @ `a75a01c` (after PR #93 merge)
- Reviewer: Claude Code `/code-review` (high effort, recall-biased)
- Scope: `git diff main...HEAD` (15 files, +864 / -41)

## Re-audit (head `3f23921`) — APPROVED FOR MERGE

Follow-up re-audited as a focused delta (`47a9899..3f23921`, 3 files / +15 / -6). Both
recommended fixes landed; no regressions; no new findings.

- **Finding 1 (Medium) — FIXED.** `_safe_failure` now returns a fixed
  `"Gmail SMTP send attempt failed; details redacted."` and no longer interpolates `str(error)`.
  The retained `type` field is only the exception class name (no PII). Regression test raises a
  real `SMTPRecipientsRefused` with `chris@example.com` embedded and asserts the serialized
  report omits that address (and the redacted message is used). The exception is an
  `SMTPException` subclass, so it routes through the existing unconfirmed-mutation handler.
- **Finding 2 (Low / CI) — FIXED.** The `phase14c_gmail_live_smoke` import was moved above
  `phase14c_supervised_smoke`; the `from personalos.*` block is now correctly isort-ordered,
  resolving the I001 violation. Verified by inspection — ruff is not installable in this
  environment (consistent with the author's note).
- **Finding 3 (cleanup) — DEFERRED (nonblocking).** Duplicate `_config_names_only` unchanged.
- Validation per PR: focused 113 OK, full 748 OK, ResourceWarning 748 OK; readiness still
  `not_ready` / `inert_report_only=true`.

**Verdict: clean — approved for merge.**

---

## Original audit (head `47a9899`)

## Verdict

**Approve with two fixes recommended before merge.** No app-password leak and no unauthorized
live-send path; the default report-only contract is genuinely names-only and live send is gated
behind `--execute-live` + `--approval-reference` + all-3-names-present. One medium info-exposure
inconsistency (finding 1) and one likely CI lint failure (finding 2) should be addressed.
Finding 3 is the recurring deferred cleanup nit.

## Findings

### 1. (Medium) Failure path leaks the unmasked email address
`phase14c_gmail_live_smoke.py:313` — `_safe_failure` returns `{"type":..., "message": str(error)}`.
For SMTP refusals, `str(error)` embeds the raw address: `SMTPSenderRefused.args` includes the
sender, `SMTPRecipientsRefused.args` includes the recipient(s). That string is emitted in the
report's `gmail_smoke.failure.message` to stdout. The module otherwise masks all emails
(`sender_masked`/`recipient_masked` via `_mask_email`), so this path contradicts its own masking
contract and the PR's "no recipient exposure" claim.

- The app password is NOT exposed — smtplib does not place credentials in exception strings.
- The sibling Todoist `_safe_failure` uses a fixed generic message; Gmail should match (or mask
  the address before including it).

Suggested fix: return a fixed category + generic message (mirroring the Todoist helper), or run
the message through an email-masking pass.

### 2. (Low / CI lint) New import breaks isort order
`cli.py:44` — `from personalos.phase14c_gmail_live_smoke import ...` is placed after
`phase14c_supervised_smoke`, but `gmail` sorts before `supervised`. pyproject
`[tool.ruff.lint] select = ["E","F","I","UP","B"]` enables isort, so `ruff check` reports I001
(unsorted imports). The PR validation log lists test suites only (no lint), so CI may still fail.

Suggested fix: move the gmail import above the supervised_smoke import (or run `ruff check --fix`).

### 3. (Low / cleanup) `_config_names_only` duplicated again
`phase14c_gmail_live_smoke.py:320` — now a 5th copy across phase14c modules. Promote to a shared
util. Recurring deferred nit.

## Verified OK

- Credentials read only behind `--execute-live` AND `--approval-reference` AND all three SMTP
  config names present (`_gmail_smtp_env_values` called only in that branch); report-only paths
  never read values.
- Transport is `smtplib.SMTP_SSL` host `smtp.gmail.com` port 465 (encrypted), single send, 10s
  timeout; `call_limits.max_email_sends == 1` enforced.
- `mutation_state` tri-state from the PR #93 fix is correctly reused: post-send failure →
  `unconfirmed_after_send_attempt`, `external_mutation: null`, `gmail_email_sent: null`; CLI
  propagates `external_mutation: null` + `external_writes: "gmail_email_send_attempted"`.
- App password never logged, returned, or committed; `_sanitize_send_result` allowlists
  `provider`/`message_id`/`message_accepted` only.
- `pre_live_readiness.py` change is reason-string only; GMAIL live rail remains disabled by
  default; readiness still `not_ready` / `inert_report_only=true`.
- `REQUIRED_CONFIG_ENTRY_NAMES` / connectivity-setup gmail rail expanded to the 3 SMTP names
  consistently; `.env.example` placeholders only.
- Setup script prompts the app password hidden (`prompt_secret`) and the controlled recipient in
  plain text (also resolves the no-echo-recipient nit raised on PR #92).

## Test status (per PR)

- Focused suite: 113 OK
- Full suite: 748 OK; ResourceWarning suite: 748 OK
- Readiness still `not_ready` / `inert_report_only=true`
