# Personal OS

Personal OS is Chris's private, local-first productivity, routine, priority,
briefing, reporting, and execution operating system. It is designed around
clear ownership, explicit safety gates, repo-local development, structured
SQLite state, and future gated execution rails.

This repository is the source of truth for code, tests, migrations, and
Markdown documentation. The current project snapshot lives in
[STATUS.md](STATUS.md); README is only the overview and navigation entry point.

## Start Here

- [STATUS.md](STATUS.md): current phase, validated state, recent PRs, and
  blocked work.
- [AGENTS.md](AGENTS.md): Codex/Fable repo instructions and stop conditions.
- [docs/PRD.md](docs/PRD.md): product truth and role boundaries.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): system topology and state
  model.
- [docs/SAFETY_POLICY.md](docs/SAFETY_POLICY.md): safety posture, protected
  systems, readiness gates, and prohibited work.
- [docs/MVP_READINESS_GAP_REPORT.md](docs/MVP_READINESS_GAP_REPORT.md):
  inert MVP readiness/gap report contract and blocked human-decision surface.
- [docs/NON_HUMAN_CLOSURE_PLAN.md](docs/NON_HUMAN_CLOSURE_PLAN.md):
  accelerated non-human repo-local closure packet plan and human-gate split.
- [docs/WEEKEND_TEST_READINESS_RUNBOOK.md](docs/WEEKEND_TEST_READINESS_RUNBOOK.md):
  inert weekend testing plan, no-go criteria, rollback templates, and evidence
  labels.
- [docs/DRY_RUN_EVIDENCE_BUNDLE.md](docs/DRY_RUN_EVIDENCE_BUNDLE.md):
  inert dry-run evidence contract, no-send demo report validator, and
  fake/local fixture surface map.
- [docs/FINAL_NONHUMAN_HANDOFF.md](docs/FINAL_NONHUMAN_HANDOFF.md):
  final inert non-human handoff report, exact human gates, and next human
  work checklist.
- [docs/PHASE_14C_SUPERVISED_SMOKE_TEST.md](docs/PHASE_14C_SUPERVISED_SMOKE_TEST.md):
  guarded supervised smoke-test runbook for Todoist, Google Calendar, Gmail,
  and OpenClaw.
- [docs/PHASE_14C_CONNECTIVITY_READINESS.md](docs/PHASE_14C_CONNECTIVITY_READINESS.md):
  current connector/client/config inventory and mobile-continuity setup names
  for the remaining Phase 14-C smoke rails.
- [docs/OPENCLAW_MODEL_STRATEGY.md](docs/OPENCLAW_MODEL_STRATEGY.md):
  deterministic Nemotron Super / GLM 5.2 lane strategy for OpenClaw smoke and
  reasoning work.
- [docs/AGENT_WORK_PACKET_PROTOCOL.md](docs/AGENT_WORK_PACKET_PROTOCOL.md):
  long-run Codex/Fable work packet protocol.
- [docs/ROADMAP.md](docs/ROADMAP.md): phase history and current/next phase.
- [docs/CODEX_WORKFLOW.md](docs/CODEX_WORKFLOW.md): branch, validation, PR,
  and completion-report workflow.

## Operating Roles

- Chris: owner, final approver, and source of judgment.
- ChatGPT: strategy, synthesis, PRD, architecture, and audit layer.
- Codex/Fable: repo implementation, tests, documentation, migrations, and PRs.
- OpenClaw: approved runtime/operator only; not repo implementation.

## State Boundaries

- GitHub repo: code, docs, tests, and migrations.
- SQLite: structured runtime state.
- PersonalOS/Obsidian/Markdown: durable notes later, behind explicit gates.
- Todoist, Google Calendar, Gmail, and OpenClaw: gated live rails only.

## Safety Boundary

Personal OS is currently not broadly live. One bounded supervised Calendar
smoke event has passed; one bounded Gmail SMTP self-send has passed; one
first-run Todoist Inbox/default create attempt was unconfirmed, then a manual
`not_found` check plus separately approved CA-bundle retry created exactly one
bounded Inbox/default task; and one first-run OpenRouter model smoke failed
with sanitized TLS trust metadata before a separately approved CA-bundle retry
passed on the Nemotron Super primary call with no GLM 5.2 fallback. Protected
OpenClaw runtime remains unrun. Todoist, Google Calendar, Gmail, and OpenClaw
are acceptable low-blast-radius rails for the bounded Phase 14-C supervised smoke-test plan in
[docs/PHASE_14C_SUPERVISED_SMOKE_TEST.md](docs/PHASE_14C_SUPERVISED_SMOKE_TEST.md),
but repo prep, runbook review, request validation, credential-name preflight,
live-readiness reports, request-template generation, and the fake-client dry-run
rehearsal do not perform additional live actions. The current remaining-rail
connector/config inventory is recorded in
[docs/PHASE_14C_CONNECTIVITY_READINESS.md](docs/PHASE_14C_CONNECTIVITY_READINESS.md).
Use `scripts/phase14c_connectivity_setup.sh` and
`personalos phase14c connectivity-setup --json` for local names-only setup
verification without printing credential values. The repo also has
`personalos phase14c gmail-smtp-smoke --json`,
`personalos phase14c todoist-inbox-smoke --json`, and
`personalos phase14c openrouter-model-smoke --json` gate commands whose
default mode is no-execution/report-only; their live modes require explicit
`--execute-live` flags, approval references, configured credentials, and the
bounded Phase 14-C supervised smoke envelope. Use
`personalos phase14c live-smoke-diagnostics --json` for the no-live Todoist
manual outcome check and future OpenRouter diagnostic-field readiness.

Codex/Fable must not inspect or mutate `/Users/coldstake/PersonalOS`,
`/Users/coldstake/.openclaw`, credential stores, LaunchAgents, crontab,
production ledgers, production SQLite paths, or other protected runtime state.

Codex/Fable must not send Gmail, write Todoist, write Google Calendar, write
PersonalOS Markdown, load or read credentials, activate a production DB,
activate a scheduler, start daemons/background loops, call OpenClaw, call live
external services, or create external writes without explicit Chris approval
for that narrow action.

Before any live-rail work, the repo must satisfy the applicable readiness and
activation policies:

- [docs/AGENT_WORK_PACKET_PROTOCOL.md](docs/AGENT_WORK_PACKET_PROTOCOL.md)
- [docs/PRE_LIVE_READINESS.md](docs/PRE_LIVE_READINESS.md)
- [docs/LIVE_RAIL_ACTIVATION_POLICY.md](docs/LIVE_RAIL_ACTIVATION_POLICY.md)
- [docs/ACTIVATION_CHECKLIST.md](docs/ACTIVATION_CHECKLIST.md)
- [docs/FIRST_LIVE_PILOT_PROTOCOL.md](docs/FIRST_LIVE_PILOT_PROTOCOL.md)
- [docs/PHASE_13G_PRE_LIVE_READINESS_MATRIX.md](docs/PHASE_13G_PRE_LIVE_READINESS_MATRIX.md)
- [docs/PHASE_14_AB_FIRST_LIVE_PILOT_PREP.md](docs/PHASE_14_AB_FIRST_LIVE_PILOT_PREP.md)
- [docs/PHASE_14_CANDIDATE_SELECTION_PREP.md](docs/PHASE_14_CANDIDATE_SELECTION_PREP.md)
- [docs/PHASE_14C_DECISION_GATE.md](docs/PHASE_14C_DECISION_GATE.md)
- [docs/PHASE_14C_CANDIDATE_DECISION_SUPPORT.md](docs/PHASE_14C_CANDIDATE_DECISION_SUPPORT.md)
- [docs/MVP_READINESS_GAP_REPORT.md](docs/MVP_READINESS_GAP_REPORT.md)
- [docs/NON_HUMAN_CLOSURE_PLAN.md](docs/NON_HUMAN_CLOSURE_PLAN.md)
- [docs/WEEKEND_TEST_READINESS_RUNBOOK.md](docs/WEEKEND_TEST_READINESS_RUNBOOK.md)
- [docs/DRY_RUN_EVIDENCE_BUNDLE.md](docs/DRY_RUN_EVIDENCE_BUNDLE.md)
- [docs/FINAL_NONHUMAN_HANDOFF.md](docs/FINAL_NONHUMAN_HANDOFF.md)
- [docs/PHASE_14C_SUPERVISED_SMOKE_TEST.md](docs/PHASE_14C_SUPERVISED_SMOKE_TEST.md)
- [docs/OPERATOR_HANDOFF_CONTRACT.md](docs/OPERATOR_HANDOFF_CONTRACT.md)
- [docs/PRODUCTION_DB_POLICY.md](docs/PRODUCTION_DB_POLICY.md)

Those policies do not activate live rails by themselves.

## Validation

Run tests with `PYTHONPATH=src`; omitting it can produce misleading import
failures.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py"
```

For control-plane and phase-closeout work, use the full validation bundle in
[AGENTS.md](AGENTS.md).
