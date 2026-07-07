# PR #97 Audit — Phase 14-C CA-bundle retry live-smoke evidence (docs + docs-tests)

- Branch: `phase-14c-ca-live-smoke-evidence`
- Head: `09aed61616c8a54ae1c6372d53b03d9b536ac1f5`
- Base: `origin/main` @ `f2e84ae` (after PR #96 merge)
- Reviewer: Claude Code `/code-review` (high effort, recall-biased)
- Scope: `git diff main...HEAD` (7 files, +175 / -74) — docs and docs-tests only, no source changes

## Verdict

**Clean — approved for merge.** No correctness, safety, or leakage findings. The packet records
the successful CA-bundle retry that reverses the prior unconfirmed/failed evidence, and it does so
with an honest, process-correct duplicate-task reconciliation.

## Findings

None.

## Verified OK

- **Todoist duplicate-task reconciliation is correct and honest.**
  - First attempt: `unconfirmed_after_task_create_attempt` (TLS trust failure before completion).
  - Manual Todoist check recorded as `not_found` — exactly the gate PR #96 diagnostics mandated,
    confirming the first attempt created no task (consistent with an SSL cert failure during the
    handshake).
  - Retry under a NEW distinct approval reference `phase14c-2026-06-30-connectivity-ca-retry` →
    exactly one task, `mutation_state=confirmed_task_created`.
  - Net: exactly one task, no duplicate; the mandated manual-check-before-retry gate was followed.
  - Root cause (`SSL_CERT_FILE` missing CA bundle) coherently explains why the first-run
    `transport_or_parse_error` meant "no task created."
- **No leakage.** Emails still masked `c***@gmail.com`; no tokens, API keys, raw provider
  responses, full prompts, or model IDs. The `SSL_CERT_FILE=/opt/homebrew/etc/ca-certificates/cert.pem`
  path and approval-reference labels are not secrets. The retry metadata recorded
  (`success=true`, `input_tokens=40`, `output_tokens=47`, sanitized latency) is entirely within
  the `SAFE_METADATA_FIELDS` allowlist. Tree-wide email/secret sweep clean.
- **No stale contradictions.** The "unconfirmed/failed" framing was consistently rewritten to
  "first-run … then CA-retry passed" across README, STATUS, OPENCLAW_MODEL_STRATEGY,
  CONNECTIVITY_READINESS, and SUPERVISED_SMOKE_TEST.
- **Docs-tests track the reworded text.** The stale "manual todoist check" assertions were
  replaced (not left dangling), and the new CA-retry evidence + no-rerun boundaries are pinned.
  Docs/model test modules pass locally (18 OK).
- **No-rerun boundaries updated.** Both the first-run and CA-bundle live commands carry explicit
  "do not rerun without new explicit approval" warnings.
- **Readiness unchanged.** `not_ready` / `inert_report_only=true`; bounded retries do not flip
  `live_rails_activated`.

## Test status (per PR)

- Focused docs/model: 18 OK (re-confirmed locally)
- Targeted Phase 14-C suite: 97 OK
- Full suite: 754 OK; ResourceWarning suite: 754 OK
- Readiness still `not_ready` / `inert_report_only=true`
