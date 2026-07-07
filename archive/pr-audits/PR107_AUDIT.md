# PR #107 Audit — Shared Phase 14-C safety utils + redaction/size hardening (refactor)

- Branch: `phase-14c-*` (shared safety utils refactor)
- Head: `af88477a30f45a7a276af8482cfda66c9dd85113`
- Base: `origin/main` @ `ff2cf29` (after PR #106 merge)
- Reviewer: Claude Code `/code-review` (high effort, recall-biased)
- Scope: `git diff main...HEAD` (22 files, +546 / -299)

## Verdict

**Clean — approved for merge.** A behavior-preserving consolidation of duplicated helpers plus two
genuine, fail-closed hardenings. No safety semantics weakened.

## Findings

None.

## Verified OK

- **Behavior-preserving consolidation.** `config_names_only`, `optional_string`, `optional_email`,
  `safe_error_kind`, and the redaction logic are extracted into a stdlib-only leaf module
  `phase14c_safety_utils` (no `personalos` imports → no cycle; confirmed by successful imports and
  the test run). Unification is in the SAFE direction: `optional_email` now uses the stricter
  `_EMAIL_RE` everywhere, strengthening the wide-net runner's old weaker `"@"-and-no-space` check
  while leaving gmail/connected identical.
- **Masking/metadata untouched.** `_mask_email`, `SAFE_METADATA_FIELDS`, and
  `sanitize_openclaw_model_run_metadata` are not modified (the `response_text` +/- lines are the
  forbidden-keys set moving to shared, not a change to the metadata allowlist).
- **Hardening 1 — bounded redaction.** `redaction_failure_reasons` gains `max_depth=32` /
  `max_nodes=5000`; exceeding either appends a reason code and stops → report BLOCKED (fail-closed).
  Resolves the PR #106 recursion-depth note. Same forbidden keys / secret patterns / email regex,
  so legitimate reports (well under the bounds) keep their classification.
- **Hardening 2 — input-size gate.** The evidence-validate handler checks `st_size > 262_144`
  (256 KiB) BEFORE `_load_json_object`, returning a blocked report (`accepted: False`,
  `["input_file_too_large"]`, no raw content, exit 1) without parsing the oversized file. Generous
  cap; won't block legitimate KB-sized reports.
- **Validator semantics preserved.** Status allowlist (`_recognized_status` /
  `_COMPLETE_PASS_STATUSES`), call-count budget checks, calendar-precheck checks, and
  model/safety-flag checks unchanged; only the redaction helper is now the shared bounded one.
- **Fail-closed CLI gate untouched.** The src diff does not touch `calendar_client_available`
  (still `False` at cli.py:2084 on baseline) or the runner's `if calendar_client is None` gate
  (runner:198). `--execute-live` remains inert (no credential read, no live call).
- **No leakage** (tree-wide sweep clean). **125 tests across all refactored gated modules pass
  locally** (live-smoke clients, connected + wide-net runners, calendar bridge, model strategy,
  full CLI), plus the new `test_phase14c_safety_utils` (codes-only + fail-closed-on-scan-limits).
  Readiness unchanged (`not_ready` / `inert_report_only=true` / `live_rails_activated=false`).

## Note

`ruff` is unavailable in this environment (as the author flagged); import ordering / lint verified
by inspection only. No isort issue observed in the changed imports.

## Test status (per PR)

- Focused affected suite: 165 OK
- Full suite: 810 OK; ResourceWarning suite: 810 OK
- Readiness still `not_ready` / `inert_report_only=true` / `live_rails_activated=false`
