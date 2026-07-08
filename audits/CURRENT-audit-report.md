# CURRENT audit report - P-CLEAN-02

Packet: P-CLEAN-02
Iteration: 2
Date: 2026-07-07
Auditor: Codex
Verdict: reject

## Findings

### B1 - Blocking: r2 introduced a Conductor-only signoff artifact inside the packet branch

The reject-closure code changes close the original F1/F2 product issues, but the r2 commit
also adds `audits/signoffs/P-CLEAN-01-G4-G1-signoff.md`.

Evidence:
- `git show --name-status 8751a9c` shows `A audits/signoffs/P-CLEAN-01-G4-G1-signoff.md`
  in the same commit as the P-CLEAN-02 r2 closure changes.
- `git diff 2f785bd..HEAD -- audits/signoffs/P-CLEAN-01-G4-G1-signoff.md` shows a new
  one-line approval record for P-CLEAN-01.
- `GOVERNANCE_MANIFEST.yaml` lists `audits/signoffs/**` under protected paths as
  "Conductor-only approval records - ANY agent write = blocker".
- P-CLEAN-02's allowed/sanctioned scope does not include `audits/signoffs/**`; the current
  audit prompt's r2 closure file list also does not include this file.

I am not asserting the approval is false. The problem is provenance and scope: an approval
record appears inside the agent packet branch/rework commit, and the auditor has no
independent way to verify it was a Conductor-only write rather than an agent-authored
self-attestation. Per the risk register, that needs Conductor review outside this packet
before this packet can be accepted.

Required closure: remove this signoff artifact from the P-CLEAN-02 packet diff, or have the
Conductor land/sign it through the declared signoff channel in a way the packet audit can
distinguish from agent work.

## Original Reject Closure

### F1 - Rail-state fail-closed behavior: closed

The r2 implementation changes `src/personalos/status.py` from a mutable public report
surface to a private-literal surface with validation at module execution and per report.
The real report-producing paths now fail before producing a report if the private state is
illegal.

Independent probes:

```bash
PYTHONPATH=src python3 - <<'PY'
import personalos.status as s
try:
    s.RAIL_STATES["gmail"] = "bogus"
except Exception as exc:
    print(type(exc).__name__ + ": " + str(exc))
PY
```

Output: `TypeError: 'mappingproxy' object does not support item assignment`.

Additional hostile probes:
- Rebinding `personalos.status.RAIL_STATES = {"gmail": "live"}` did not affect
  `create_rail_state_report()`, which still returned all rails inert.
- Mutating `personalos.status._RAIL_STATES["gmail"] = "bogus"` caused
  `create_rail_state_report()` to raise `RailStateError`; no report was produced.
- Executing a patched copy of `status.py` with an illegal rail literal raised
  `RailStateError` during module execution.
- Executing a patched copy of `status.py` with `_SCHEDULER_STATE = "enabled"` raised
  `RailStateError` during module execution.

Consumer checks:
- `dashboard.render_today_view_html()` raises `ValueError` for missing, `None`, string,
  empty, and missing-`rails` `rail_state_summary` values.
- `src/personalos/cli.py` no longer has the old invalid-state warning-label branch.
- The new contract tests are present in `tests/test_status.py`:
  `test_rail_states_public_view_is_immutable`,
  `test_rail_state_validation_fails_closed_on_illegal_values`,
  `test_rail_state_report_ignores_public_attribute_rebinding`, and
  `test_rail_state_report_shape_is_exact`.

Residual note:
- A forged direct call to the private CLI formatter can still print a bogus rail value if a
  caller hand-builds an invalid report dict. I did not count that as an F1 blocker because
  first-party command paths create reports through `create_rail_state_report()` or
  `create_status_summary()`, and those paths now fail closed before formatting.

Token check:
- `git grep -n invalid_rail_states -- src tests` exits 1 with no tracked source/test
  matches.
- The literal repo-wide `git grep invalid_rail_states` is not zero because the audit
  prompt, living STATUS handoff, and prior/current audit report text preserve that token as
  audit history. Product code is clean; the literal repo-wide closure claim is overbroad.

### F2 - Process-era credential helpers: closed

The two leftover env-reading helpers from r1 are gone.

Evidence:
- `git grep -n "_connected_rehearsal_env_values\|_wide_net_rehearsal_env_values\|os.environ" -- src/personalos/cli.py tests/test_cli.py`
  exits 1 with no matches.
- `grep -c 'os\.environ' src/personalos/cli.py` prints `0` (grep exit 1 because there are
  zero matches).
- Credential-name grep over `src/personalos/cli.py` and `tests/test_cli.py` finds no
  `TODOIST_`, `OPENROUTER_`, `GMAIL_`, `GOOGLE_`, `SMTP_`, `APP_PASSWORD`, `TOKEN`,
  `API_KEY`, or `CREDENTIAL` references.
- The four dead Phase 14-C fixture helpers are deleted from `tests/test_cli.py`.
- `personalos status --help` now says "Render inert local status and rail states from an
  explicit safe DB."

## Sanctioned Deletion Fidelity

The tracked deletion set still matches the P-CLEAN-02 sanctioned process-layer deletion
shape:
- Deleted source modules: 32 total = 21 `phase14c_*`, 2 `phase14_*`, and 9 named
  process/readiness modules. Unexpected source deletions: none.
- Deleted tests: 27 total. Unexpected deleted product tests by name/pattern: none.
- Deleted scripts: exactly `scripts/phase14c_connectivity_setup.sh`.

Deleted-module import check:

```bash
git grep -n -E "from personalos\.(dry_run_evidence|final_nonhuman_handoff|mvp_readiness|nonhuman_closure|openclaw_model_strategy|openrouter_model_smoke_client|operator_status|pre_live_readiness|weekend_test_readiness)|from personalos\.phase14|import personalos\.(dry_run_evidence|final_nonhuman_handoff|mvp_readiness|nonhuman_closure|openclaw_model_strategy|openrouter_model_smoke_client|operator_status|pre_live_readiness|weekend_test_readiness)|import personalos\.phase14" -- src tests
```

Exited 1 with no matches.

Network primitive check:

```bash
git grep -n -E '^\s*(import|from)\s+(smtplib|urllib\.request|http\.client|socket|requests)(\b|\.)' -- src/personalos tests
```

Exited 1 with no matches.

CLI surface:
- `PYTHONPATH=src python3 -m personalos.cli --help` exposes only
  `workflows`, `demo`, `status`, `today`, `briefing`, `synthesis`, `side-effects`,
  `dashboard`, and `scheduler`.
- No `phase14c`, readiness, or live-smoke command remains visible.

## Test Count Delta

The r2 test diff adds five test methods and removes one dashboard fallback test:
- Added four `tests/test_status.py` rail-state contract tests.
- Added `test_dashboard_render_fails_loud_on_missing_or_malformed_rail_states`.
- Removed `test_dashboard_rail_state_panel_marks_missing_fields_unavailable`.

Net: +4 from the r1 suite count, matching 417 -> 421. The current suite confirms 421 tests.

The broader declared packet delta is therefore 809 -> 421, a reduction of 388 tests, with
the reduction attributable to the sanctioned process-module/test retirement.

## QUALITY_GATES Evidence

Run locally from repo root on `packet/P-CLEAN-02` at
`8751a9c66c090e7a68eb5ebc6cf1b938b0fc9c28`:

1. `git status --short` exited 0 and printed nothing.
2. `git diff --check` exited 0 and printed nothing.
3. `PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py"` ran 421 tests in
   12.763s: OK.
4. `PYTHONTRACEMALLOC=10 PYTHONPATH=src python3 -W always::ResourceWarning -m unittest discover -s tests -p "test_*.py" -q`
   ran 421 tests in 25.930s: OK.
5. `find . -maxdepth 2 -name var -print` printed nothing.
6. `find . -path ./.git -prune -o \( -name "*.sqlite" -o -name "*.sqlite3" -o -name "*.db" \) -print`
   printed nothing.
7. `gitleaks detect --no-git --source . --config .gitleaks.toml --exit-code 9` exited 0
   and reported no leaks found after scanning about 8.57 MB.
8. `git check-ignore -q .env.local` exited 0.
9. `test -z "$(git ls-files '.env*' | grep -v '^.env.example$')"` exited 0.

Per project doctrine, these are auditor-run development checks, not runner evidence of
record.

## Bootstrap Attestation

I read the current `GOVERNANCE_MANIFEST.yaml` for attestation.

Manifest governance files:
- `GOVERNANCE_MANIFEST.yaml` changed as the P-CLEAN-02 sanctioned G-GOV rider: it removes
  the six deleted legacy network-capable smoke modules from protected paths and adds
  `src/personalos/status.py`.
- No other manifest-listed governance/rulebook file changed in the packet diff.

Manifest protected paths:
- `src/personalos/status.py` changed as the sanctioned new activation-ladder state surface.
- `scripts/phase14c_connectivity_setup.sh` was deleted as the sanctioned host-touching
  Phase 14-C setup-script deletion.
- `audits/signoffs/P-CLEAN-01-G4-G1-signoff.md` was added; this is the blocker in B1.
- No `migrations/**`, `.env*`, `src/personalos/permissions.py`,
  `src/personalos/path_safety.py`, or `src/personalos/rails/**` diff entries were present.

I did not open `.env.local`, load credential values, contact external services, execute a
live-capable CLI path, or start scheduler/background behavior. I did not read
`governance/SECURITY.md` because the auditor standing brief marks protected paths as out of
bounds.

## Ways This Review Could Be Wrong

- The new signoff file may have been written directly by the Conductor outside any agent
  action. The branch/commit shape does not prove that, and the file's own text is not
  independent evidence under the rulebook. If the Conductor confirms and lands it through a
  distinguishable Conductor-only path, B1 should clear without code changes.
- I treated the private CLI formatter as non-blocking because the real report constructors
  now fail closed. If the harness threat model treats arbitrary calls to private helper
  functions as supported runtime surface, that residual should be promoted.
- `rg` is unavailable in this environment, so I used `git grep`, `grep`, `find`, and small
  Python probes. The tracked-source checks are covered; ignored generated files were not
  treated as packet evidence.
- QUALITY_GATES results above are local auditor evidence only; runner-executed evidence
  remains the evidence of record.
