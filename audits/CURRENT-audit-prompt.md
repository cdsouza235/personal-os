# CURRENT audit prompt — packet P-CLEAN-02 (process-layer retirement) — iteration 1

Packet: `P-CLEAN-02` · Iteration: 1 · Date: 2026-07-07
Auditor: Codex, per `audits/AUDITOR-BRIEF-codex.md` (esp. lens 4: sanctioned-deletion
fidelity, and lens 2: doctrine-as-implementation on the NEW rail-state surface).
Branch: `packet/P-CLEAN-02`, stacked on `packet/P-CLEAN-01` (base for THIS packet's diff =
`61a3703`, the P-CLEAN-01 commit). Audit `git diff 61a3703...HEAD`.

## The packet (governance/ROADMAP.md → P-CLEAN-02)
Deletes the process layer from code and replaces readiness/operator consumption with a
lean rail-state surface.

### Sanctioned deletions (verify the diff matches EXACTLY — extra or missing = finding)
- 32 modules under `src/personalos/`: all `phase14c_*` (21), `phase14_*` (2),
  `mvp_readiness`, `nonhuman_closure`, `weekend_test_readiness`, `dry_run_evidence`,
  `final_nonhuman_handoff`, `openclaw_model_strategy`, `openrouter_model_smoke_client`,
  `operator_status`, `pre_live_readiness`.
- 27 test files (`tests/test_<same names>*.py`).
- `scripts/phase14c_connectivity_setup.sh` (configures env for deleted smoke commands).
- Inside `src/personalos/cli.py`: the `phase14c` + `readiness` parser blocks, 36
  `_command_*` handlers, 7 helper functions, 21+8 import blocks, 37 workflow-catalog
  entries, and the operator-status/readiness human-output renderers.
- Inside `tests/test_cli.py`: 66 test methods exercising retired surfaces + 8 import
  blocks (26 product test methods kept).
- Orphaned dashboard helpers (`_status_value`, `_format_bool_or_unavailable`,
  `_string_list`) and `_append_operator_status_lines`/`_append_readiness_lines` family.

### The replacement (audit this HARD — lens 2)
`src/personalos/status.py` gains `RAIL_STATES` / `SCHEDULER_STATE` constants +
`create_rail_state_report()` (per-rail `inert|soaking|live`, fail-loud
`invalid_rail_states`). Consumers rewired: `create_status_summary`, `today.py`
(`rail_state_summary` key), `dashboard.py` (banner + one `_render_rail_state_summary`
panel), `demo/no_send_e2e.py` (safety assertions + summary markdown + blocked summary),
`cli.py` (`workflows`/`status` reports, `_with_workflow_context` default,
`_append_rail_state_lines`). Questions to answer adversarially:
1. Is there ANY runtime path that can mutate `RAIL_STATES`/`SCHEDULER_STATE`?
2. Does every consumer fail loud (not silently-inert) on an invalid state value?
3. Did any deleted module carry ENFORCING (not merely reporting) logic whose loss weakens
   the posture? Check against your own Phase 0 Q3 classification
   (`audits/PHASE0_CODEX_AUDIT.md`) — the claim is that only asserting/reporting code
   died and `permissions/side_effects/idempotency/path_safety/scheduler/state` survive
   untouched.
4. Is any network-capable import (`smtplib`, `urllib.request`, `http.client`, `socket`)
   left anywhere under `src/personalos/`? (Expected: ZERO after this packet.)

### Sanctioned G-GOV rider (ROADMAP P-CLEAN-02 allows exactly this)
`GOVERNANCE_MANIFEST.yaml` protected-path shrink: six deleted smoke modules removed;
`src/personalos/status.py` ADDED (RAIL_STATES = activation-ladder state). Verify nothing
else in the manifest changed.

## Acceptance criteria
1. Deletion fidelity per the lists above; product modules/tests untouched beyond the
   enumerated consumer rewires (status/today/dashboard/demo/cli + 5 test files'
   assertion updates).
2. **Declared test delta: 809 → 417**, all green — run all QUALITY_GATES steps yourself.
3. CLI help (`personalos --help` via `PYTHONPATH=src python3 -m personalos.cli --help`)
   shows only product commands; no module imports a deleted name; zero network-capable
   imports under `src/`.
4. The four adversarial questions above answered with evidence.
5. Bootstrap attestation. Two DECLARED carries (not findings): QUALITY_GATES baseline
   line still reads 809 (governance/** is forbidden for this packet; refresh rides with
   the next sanctioned G-GOV edit); `.env.example` kept for future P-RAIL packets.

## Output
Overwrite `audits/CURRENT-audit-report.md`; append to `audits/AUDIT-LOG.md`.
Verdict: accept / accept_with_conditions / reject. Same constraints as always (read-only
except your two files; never open `.env.local`; no live paths).
