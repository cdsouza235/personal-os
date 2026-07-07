# PR #108 Audit — Wide-net Calendar transcript template + validator

- Branch: `phase-14c-calendar-transcript-validator`
- Head: `c5d73c0a71cf16af64536fb64863a08b9277c4fc` (original) → `197f4296c7e9f4e33c9a1ff7982adcc7d804dd17` (re-audited)
- Base: `origin/main` @ `d60f8e8` (after PR #107 merge)
- Reviewer: Claude Code `/code-review` (high effort, recall-biased)
- Scope: `git diff main...HEAD` (13 files, +949 / -13)

## Re-audit (head `197f429`) — APPROVED FOR MERGE

Fix re-audited as an isolated delta (`c5d73c0..197f429`, 3 files / +51 / -9).

- **Finding 1 (Low) — FIXED.** `_validate_create` no longer echoes raw `result_keys`. It now
  reports `result_key_count` (int) and `allowed_result_keys` (filtered to
  `isinstance(key, str) and key in _ALLOWED_CREATE_RESULT_KEYS`), with
  `result_keys_allowed = result_key_count == len(allowed_result_keys)` — so disallowed keys still
  block, but the output can only ever contain allowlisted key names. Re-traced the exact malicious
  case `{"chris.private@gmail.com": "evt_12345"}`: still BLOCKED, and the serialized report now
  omits BOTH the email and the event id (`allowed_result_keys: ()`, `result_key_count: 1`).
  Regression test added. `_empty_create_summary` updated consistently; delta isolated to the
  create-summary output shape.

**Verdict: clean — approved for merge.**

---

## Original audit (head `c5d73c0`)

## Verdict

**Approve with one Low fix recommended.** The template is inert and the validator is tight and
fail-closed. One Low finding: the validator echoes raw `sanitized_result` key names, which can
surface an unmasked email/secret used as a dict key — a narrow contradiction of its no-leak
guarantee (no false-accept). Fix in this PR or a quick follow-up.

## Findings

### 1. (Low) `create_summary.result_keys` echoes raw input key names
`phase14c_wide_net_calendar_transcript.py:296` — `_validate_create` returns
`result_keys = tuple(sorted(str(key) for key in result))`, echoed unconditionally in the output.
The redaction scan (`redaction_failure_reasons`) checks keys only against the exact forbidden-name
set and scans string VALUES (not keys) for emails/secrets, so an email/secret used as a KEY slips
the scan AND is echoed via `result_keys`.

Trace (confirmed): `calendar_create.sanitized_result = {"chris.private@gmail.com": "x"}` is correctly
BLOCKED (`result_keys_allowed=False`), but the output's `calendar_create_summary.result_keys` =
`["chris.private@gmail.com"]` — the unmasked email is in the serialized report while
`unmasked_emails_reported` is still asserted False. No false-accept (blocked), but a no-leak
boundary shouldn't echo arbitrary input key names.

Fix: echo `result_key_count` + `result_keys_allowed` (bool), or only echo
`sorted(set(result) & _ALLOWED_CREATE_RESULT_KEYS)`, and/or extend the redaction scan to run key
strings through the email/secret checks.

## Verified OK

- **Template inert.** Reports expected connector args (from the bridge report, which validates
  them); all safety flags False; `template_only_not_authorization: True`.
- **Validator tight & fail-closed.** Requires marker match; precheck performed + `search_events` +
  exact-args match + valid contract (shared `require_explicit_calendar_matching_event_count`) +
  count 0 + no details/attendees logged; create (if performed) requires clear precheck +
  `create_event` + exact args + `sanitized_result` mapping with only allowed keys
  (`id`/`event_id`/`status`); plus shared bounded redaction. Any failure → blocked / exit 1. No
  false-accept path.
- **CLI safe.** `--input-file` via `validate_existing_input_file_path` (rejects
  protected/sensitive/production/var paths); 256 KiB size gate BEFORE `_load_json_object`
  (oversized → blocked, no parse); no `os.environ`; all no-live flags. Template handler is a pure
  emitter.
- **Aside from `result_keys`, no raw echo** — output is reason codes + bools + `matching_event_count`
  (int). Source leakage sweep clean; focused + CLI tests pass locally (88 OK); CLI connector gate
  untouched (still fail-closed); readiness unchanged (`not_ready` / `inert_report_only=true` /
  `live_rails_activated=false`).

## Test status (per PR)

- Focused CLI/new module: 83 OK; focused packet: 100 OK
- Full suite: 819 OK; ResourceWarning suite: 819 OK
