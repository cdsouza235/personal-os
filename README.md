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
- [docs/PHASE_14C_CONNECTED_REHEARSAL.md](docs/PHASE_14C_CONNECTED_REHEARSAL.md):
  next connected Gmail/Todoist/OpenRouter rehearsal plan after connectivity
  confirmation.
- [docs/PHASE_14C_WIDE_NET_REHEARSAL.md](docs/PHASE_14C_WIDE_NET_REHEARSAL.md):
  next wider Phase 14-C plan for one OpenRouter diagnostic, one Todoist task,
  one Gmail self-send, and one self-only Calendar event.
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
manual outcome check and future OpenRouter diagnostic-field readiness. Use
`personalos phase14c connected-rehearsal-plan --json` to inspect the next
larger model-to-task-to-email rehearsal plan without reading credentials or
calling live services. Use `personalos phase14c connected-rehearsal --json`
to inspect the executable gate for that rehearsal. The approved 2026-07-01
connected rehearsal used one Nemotron Super primary call and one GLM 5.2
fallback call, then stopped at model validation before creating Todoist or
sending Gmail; Calendar and protected OpenClaw runtime remained untouched.
Do not rerun the connected live command without a new explicit approval. Use
`personalos phase14c wide-net-rehearsal-plan --json` to inspect the next
wider inert plan for one OpenRouter diagnostic, one Todoist task, one Gmail
self-send, and one self-only Calendar event. That plan is not live
authorization. Use
`personalos phase14c wide-net-calendar-bridge-payloads --json` to inspect the
Google Calendar app connector payloads for the duplicate precheck and
self-only create step; that command is report-only and does not call the
connector. Use `personalos phase14c wide-net-execution-handoff --json` to
inspect the future bounded live command template, Calendar connector handoff,
call budgets, and post-run evidence requirements without wiring the connector
or reading credentials. Use
`personalos phase14c wide-net-calendar-transcript-template --json` and
`personalos phase14c wide-net-calendar-transcript-validate --input-file <file> --json`
to inspect and validate sanitized Calendar connector precheck/create
transcripts without calling the connector or echoing raw event details. Use
`personalos phase14c wide-net-evidence-template --json` to inspect the
fillable sanitized post-run evidence shape; the template is not accepted
evidence until a separately approved run fills it with observed counts and
booleans. Use
`personalos phase14c wide-net-evidence-validate --input-file <file> --json` to
validate one sanitized wide-net evidence report without echoing raw evidence;
the validator rejects oversized files before JSON parsing and uses shared
bounded redaction checks with explicit depth and node limits. Use
`personalos phase14c wide-net-evidence-crosscheck --calendar-transcript-file <file> --evidence-file <file> --json`
to check that a sanitized Calendar transcript and sanitized wide-net evidence
agree on the marker, precheck count, and Calendar create count without echoing
raw inputs. Use `personalos phase14c wide-net-evidence-rehearsal --json` to
run a repo-local rehearsal with synthetic sanitized inputs through the Calendar
transcript validator, wide-net evidence validator, and crosscheck chain
without returning raw fixture payloads or producing live evidence.
Use `personalos phase14c wide-net-readiness-rollup --json` to inspect one
repo-local wide-net readiness rollup that summarizes the plan, Calendar
payload/transcript surfaces, execution handoff, evidence template, and
synthetic evidence rehearsal. The rollup does not read credentials, does not
call connectors, does not initialize live clients, does not write files, does
not produce live evidence, and does not authorize a live run; it records
remaining human and connector gates. Use
`personalos phase14c wide-net-readiness-rollup-contract --json` to validate
that rollup against a fixed inert contract and fixed reason-code output without
reading credentials, calling connectors, initializing live clients, writing
files, or authorizing live execution.
Use `personalos phase14c wide-net-rehearsal --json` to inspect the default
no-live gate; its `--execute-live` path fails closed before credential values
are read until an audited Calendar client/connector bridge exists. The
injected wide-net runner now enforces a Calendar duplicate-marker precheck
before any model, Todoist, Gmail, or Calendar create step can run, and the
Calendar bridge scaffold fails closed on unrecognized precheck response
shapes.

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
