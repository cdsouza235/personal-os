# CURRENT audit prompt — packet P-CLEAN-02 — ITERATION 2 (reject closure)

Packet: `P-CLEAN-02` · Iteration: 2 · Date: 2026-07-07
Auditor: Codex, per `audits/AUDITOR-BRIEF-codex.md`.
Branch: `packet/P-CLEAN-02` (base for the packet diff = `61a3703`). Your iteration-1
verdict was **reject** (F1 fail-open/mutable rail state; F2 leftover credential-loading
helpers). Verify closure by re-deriving — including re-running your own r1 probes.

## Closure claims to verify

### F1 — fail-closed by construction (not by label)
- `src/personalos/status.py`: private `_RAIL_STATES`/`_SCHEDULER_STATE` literals are
  validated **at import** — `_validate_rail_states` raises `RailStateError`, so an illegal
  value makes the module (and every consumer) refuse to load.
- Public `RAIL_STATES` is a `MappingProxyType`: your r1 probe
  `s.RAIL_STATES["gmail"]="bogus"` must now raise TypeError.
- `create_rail_state_report()` reads the PRIVATE literals and re-validates per call:
  rebinding the public attribute is inert (report unchanged); mutating the private dict
  to an illegal value yields `RailStateError`, never a report. Re-run your probes.
- `invalid_rail_states` no longer exists anywhere (`git grep invalid_rail_states` = 0):
  validation raises instead of labeling.
- `dashboard.render_today_view_html` RAISES ValueError on missing/malformed
  `rail_state_summary` — the "unavailable" silent-degradation path you flagged is gone
  (test: `test_dashboard_render_fails_loud_on_missing_or_malformed_rail_states`).
- `cli._append_rail_state_lines` no longer has the warning-label branch.
- 4 new contract tests in `tests/test_status.py` (immutability, illegal-value validation,
  rebind-inertness, exact report shape). Derive your own additional probes if you see a
  hole — the honest residual is documented in status.py: rewriting module PRIVATES is
  host-level tampering outside the model (same class as the harness's trusted-host bound).

### F2 — process-era credential helpers gone
- `_connected_rehearsal_env_values` / `_wide_net_rehearsal_env_values` deleted;
  `grep -c os.environ src/personalos/cli.py` = 0.
- The 4 dead phase14c fixture helpers deleted from `tests/test_cli.py`.
- Stale `status` help wording fixed ("status and rail states").

## Also within scope
- Anything NEW the rework introduced (diff since your r1: `status.py`, `dashboard.py`,
  `cli.py`, `demo/no_send_e2e.py`, the 5 test files).
- **Updated declared test delta: 809 → 421** (was 417 at r1; +4 contract tests, −1
  replaced dashboard test, +1 net elsewhere — verify the arithmetic yourself against the
  diff). Run all QUALITY_GATES steps.
- Standing carries unchanged (QUALITY_GATES baseline line; `.env.example`).

## Output
Overwrite `audits/CURRENT-audit-report.md`; append to `audits/AUDIT-LOG.md`.
Verdict: accept / accept_with_conditions / reject, findings ranked, "ways this review
could be wrong", bootstrap attestation. Same constraints (read-only except your two
files; never open `.env.local`; no live paths).
