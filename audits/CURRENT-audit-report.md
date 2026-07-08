# CURRENT audit report - P-CLEAN-02

Packet: P-CLEAN-02
Iteration: 1
Date: 2026-07-07
Auditor: Codex
Verdict: reject

## Findings

### F1 - Blocking: rail-state replacement is not fail-loud and is runtime-mutable

The new rail-state surface does not meet the prompt's replacement criteria.

Evidence:
- `src/personalos/status.py:36` exposes `RAIL_STATES` as a mutable `dict[str, str]`.
- `src/personalos/status.py:42` exposes `SCHEDULER_STATE` as a module global.
- `src/personalos/status.py:48`-`66` copies current values and returns
  `invalid_rail_states`, but it does not raise or otherwise fail the caller.
- `src/personalos/cli.py:1535`-`1544` renders invalid rail states as text and still returns a
  normal report.
- `src/personalos/dashboard.py:660`-`692` renders invalid or missing rail states as HTML text,
  including "unavailable" fallbacks.
- `tests/test_today_dashboard.py:341`-`361` explicitly accepts missing rail-state fields as
  "unavailable", which is silent degradation, not fail-loud behavior.

Hostile-caller probes:

```bash
PYTHONPATH=src python3 -c 'import personalos.status as s; s.RAIL_STATES["gmail"]="bogus"; print(s.create_rail_state_report())'
```

Exited 0 and returned `invalid_rail_states: ['gmail']` while preserving
`status.py`'s claim that "no runtime path mutates these states."

```bash
PYTHONPATH=src python3 -c 'from personalos import cli; print(cli._human_report({"command":"status","status":"completed","rail_states":{"rails":{"gmail":"bogus"},"scheduler":"off","invalid_rail_states":["gmail"]}}))'
```

Exited 0 and printed `status: completed` plus `INVALID RAIL STATES (fail loud): gmail`.
That is a warning label, not a failed consumer path.

```bash
PYTHONPATH=src python3 -c 'import personalos.status as s; s.SCHEDULER_STATE="enabled"; print(s.create_rail_state_report())'
```

Exited 0 and returned `invalid_rail_states: ['scheduler']`.

Answer to prompt questions 1 and 2: yes, an in-process runtime caller can mutate the
exported rail-state globals; no, every consumer does not fail loud on invalid state values.
This violates the core replacement acceptance criterion.

### F2 - Blocking: process-layer cleanup left credential-loading Phase 14-C helpers in `cli.py`

The file deletion list is exact, but process-layer code remains in the live CLI module.

Evidence:
- `src/personalos/cli.py:616` defines `_connected_rehearsal_env_values()`.
- `src/personalos/cli.py:644` defines `_wide_net_rehearsal_env_values()`.
- Those helpers read old Phase 14-C/OpenClaw/Gmail/Todoist/Calendar env names at
  `src/personalos/cli.py:618`-`670`, including API key, Gmail app password, Todoist token,
  and Calendar credential label variables.
- `git grep -n "os.environ" -- src/personalos/cli.py` finds only those remaining process-era
  helper reads.
- `git grep -n -E "def _.*(phase14|wide_net|connected|rehearsal|readiness|operator)" --
  src/personalos/cli.py tests/test_cli.py` finds those two CLI helpers plus dead Phase 14-C
  helpers in `tests/test_cli.py`.

I did not find a current parser route calling these helpers, so this is not a reachable live
write. It is still a deletion-fidelity failure for a packet whose purpose is to retire the
process layer from code, and it preserves credential-loading helper code in a module that
should now expose only product/no-send workflows.

## Sanctioned Deletion Fidelity

Tracked file deletions match the prompt's file-level sanctioned list:
- 32 deleted source modules under `src/personalos/`: 21 `phase14c_*`, 2 `phase14_*`, and
  the 9 named process/readiness modules.
- 27 deleted test files.
- `scripts/phase14c_connectivity_setup.sh` deleted.

Commands:

```bash
git diff --name-status 61a3703...HEAD -- src/personalos | awk '$1=="D" {print $2}' | grep -E '^src/personalos/(phase14c_|phase14_|mvp_readiness|nonhuman_closure|weekend_test_readiness|dry_run_evidence|final_nonhuman_handoff|openclaw_model_strategy|openrouter_model_smoke_client|operator_status|pre_live_readiness).*\.py$' | wc -l
```

Printed `32`.

```bash
git diff --name-status 61a3703...HEAD -- src/personalos | awk '$1=="D" {print $2}' | grep -E '^src/personalos/phase14c_.*\.py$' | wc -l
git diff --name-status 61a3703...HEAD -- src/personalos | awk '$1=="D" {print $2}' | grep -E '^src/personalos/phase14_.*\.py$' | wc -l
git diff --name-status 61a3703...HEAD -- src/personalos | awk '$1=="D" {print $2}' | grep -E '^src/personalos/(mvp_readiness|nonhuman_closure|weekend_test_readiness|dry_run_evidence|final_nonhuman_handoff|openclaw_model_strategy|openrouter_model_smoke_client|operator_status|pre_live_readiness)\.py$' | wc -l
```

Printed `21`, `2`, and `9`.

```bash
git diff --name-status 61a3703...HEAD -- tests | awk '$1=="D" {print $2}' | wc -l
```

Printed `27`.

`git diff --name-status 61a3703...HEAD -- scripts/phase14c_connectivity_setup.sh` printed
`D scripts/phase14c_connectivity_setup.sh`.

## Replacement Surface Review

Prompt question 3: I did not find deleted modules carrying surviving enforcement whose loss
weakens the current posture. Against `audits/PHASE0_CODEX_AUDIT.md` Q3, the deleted live
smoke clients and readiness modules were separate smoke/report/approval surfaces. The
surviving product enforcement substrates remain outside this packet's diff:
`permissions.py`, `side_effects.py`, `idempotency.py`, `path_safety.py`, `scheduler.py`, and
`state.py` are not changed by `git diff 61a3703...HEAD`.

However, the replacement surface itself is weaker than its own contract because invalid
activation-ladder states are returned as report data rather than rejected.

Prompt question 4: zero tracked network-capable imports remain under `src/personalos/`.

```bash
git grep -n -E '^\s*(import|from)\s+(smtplib|urllib\.request|http\.client|socket|requests)(\b|\.)' -- src/personalos
```

Exited 1 with no matches.

Deleted-module import check:

```bash
git grep -n -E "from personalos\.(dry_run_evidence|final_nonhuman_handoff|mvp_readiness|nonhuman_closure|openclaw_model_strategy|openrouter_model_smoke_client|operator_status|pre_live_readiness|weekend_test_readiness)|from personalos\.phase14|import personalos\.(dry_run_evidence|final_nonhuman_handoff|mvp_readiness|nonhuman_closure|openclaw_model_strategy|openrouter_model_smoke_client|operator_status|pre_live_readiness|weekend_test_readiness)|import personalos\.phase14" -- src tests
```

Exited 1 with no matches.

`PYTHONPATH=src python3 -c 'import importlib.util; print(importlib.util.find_spec("personalos.phase14c_gmail_live_smoke"))'`
printed `None`, and importing that deleted module raised `ModuleNotFoundError`.

## CLI Check

```bash
PYTHONPATH=src python3 -m personalos.cli --help
```

Exited 0 and showed only:
`workflows`, `demo`, `status`, `today`, `briefing`, `synthesis`, `side-effects`,
`dashboard`, `scheduler`.

```bash
PYTHONPATH=src python3 -m personalos.cli phase14c --help
PYTHONPATH=src python3 -m personalos.cli readiness --help
```

Both exited 2 with invalid choice errors. The parser blocks are gone.

There is one stale wording carry in the `status` help: "Render inert local
status/readiness from an explicit safe DB." I did not treat that as a separate finding
because there is no `readiness` command path, but it is cleanup evidence for the reject.

## QUALITY_GATES Evidence

All QUALITY_GATES commands were run locally from the repo root and exited 0:

1. `git status --short` printed nothing; `git diff --check` printed nothing.
2. `PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py"` ran 417 tests in
   24.554s: OK.
3. `PYTHONTRACEMALLOC=10 PYTHONPATH=src python3 -W always::ResourceWarning -m unittest discover -s tests -p "test_*.py" -q`
   ran 417 tests in 27.578s: OK.
4. `find . -maxdepth 2 -name var -print` printed nothing; the SQLite/DB artifact find
   printed nothing.
5. `gitleaks detect --no-git --source . --config .gitleaks.toml --exit-code 9` exited 0
   and reported no leaks found after scanning about 8.57 MB.
6. `git check-ignore -q .env.local` exited 0; `test -z "$(git ls-files '.env*' | grep -v '^.env.example$')"`
   exited 0.

Declared carries accepted as carries, not findings:
- `governance/QUALITY_GATES.md` still says 809 baseline; governance kit edit is deferred
  to the next sanctioned G-GOV packet.
- `.env.example` remains for future P-RAIL packets.

I did not open `.env.local`, load credential values, contact external services, execute a
live-capable CLI path, or start scheduler/background behavior.

## Bootstrap Attestation

Manifest-listed rulebook files:
- `GOVERNANCE_MANIFEST.yaml` changed as the sanctioned G-GOV rider.
- No other manifest-listed governance/rulebook file changed. The grep over the branch diff
  for `AGENTS.md`, `governance/HUMAN_GATES.md`, `governance/QUALITY_GATES.md`,
  `governance/RISK_REGISTER.md`, `governance/SECURITY.md`,
  `governance/DEPENDENCY_POLICY.md`, `governance/RUNBOOK.md`,
  `governance/POLICY_EXCEPTIONS.md`, `governance/ROADMAP.md`, `docs/PRD.md`,
  `docs/ARCHITECTURE.md`, `README.md`, `.gitleaks.toml`, governance templates, and auditor
  standing briefs printed nothing.

Manifest diff:
- removed the six deleted legacy network-capable smoke module protected paths.
- added `src/personalos/status.py`.
- no other manifest content changed.

Protected paths:
- `scripts/phase14c_connectivity_setup.sh` deletion is sanctioned.
- `src/personalos/status.py` addition/change is sanctioned as the new activation-ladder
  state surface.
- No `audits/signoffs/**`, `migrations/**`, `.env*`, `src/personalos/permissions.py`,
  `src/personalos/path_safety.py`, or `src/personalos/rails/**` diff entries were present.

Audit/status handoff files present in the diff (`audits/CURRENT-audit-prompt.md`,
`audits/CURRENT-audit-report.md`, `audits/AUDIT-LOG.md`,
`governance/living/agent-writable/STATUS.md`) are not manifest-listed rulebook files.

## Ways This Review Could Be Wrong

- `rg` is unavailable in this environment, so I used `git grep`, `grep`, `awk`, and `find`.
  That covers tracked source for import/path checks but not ignored local artifacts.
- I treated direct mutation of exported Python module globals as a runtime path because
  `status.py` is the replacement activation-ladder surface and the prompt explicitly asks
  whether any runtime path can mutate those values. If the intended boundary is only
  "no first-party command mutates them," then F1 would narrow, but the fail-open invalid
  consumer behavior would still remain.
- The stale `__pycache__` files for deleted modules are ignored and `importlib.find_spec`
  did not find deleted modules. I did not treat ignored bytecode as a tracked deletion
  fidelity failure.
- QUALITY_GATES results above are auditor-run local evidence only; per project doctrine,
  runner/Conductor-executed evidence remains the evidence of record.
