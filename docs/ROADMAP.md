# Roadmap

Last updated: 2026-06-25

[../STATUS.md](../STATUS.md) is the canonical current phase snapshot. This
roadmap records phase history and near-term sequencing; it should not be the
only source for current validated state.

## Current / Next

Phase 13E-D is implemented and post-merge validated. Phase 13G is implemented
and post-merge validated. Phase 14-A/B preparation is implemented and
post-merge validated as an inert control-plane packet: first live pilot design
plus fail-closed scaffolding, no activation. Pre-Phase-14-C
candidate-selection preparation is implemented and post-merge validated as
inert process/template/validator scaffolding. One future Todoist candidate,
Clean Kitchen Countertops and Stovetop, is recorded for candidate-review
tracking only via PR #40, not approved, not authorized, and not activated.
The Phase 14-C candidate decision gate is documented as an inert future
approval boundary; it does not authorize Phase 14-C, candidate execution, live
Todoist/Gmail/Calendar access, OpenClaw, credentials, production DB,
scheduler/background behavior, dynamic cleaning, Watch Tower adoption,
`.agent/`, `CLAUDE.md`, or runtime/operator scaffolding.
The Phase 14-C candidate decision-support bundle adds an inert review
checklist and unfilled false-default decision-record template for that same
candidate-review tracking only posture. The Phase 14-C candidate
decision-support validator adds an inert source/test report helper for the
same unfilled template; it blocks filled decisions, approval/authorization
flags, live-service fields, credentials/secrets, live IDs, unknown schema
fields, nested payloads under known fillable fields, dynamic cleaning flags,
Watch Tower flags, `.agent/`, `CLAUDE.md`, and runtime/operator scaffolding
flags. Table-driven invariant tests cover the false-default schema, every
fillable decision field, every required false field, and the allowed blocked /
decision-needed status set. Report-level tests cover blocked-report
sanitization, deterministic default timestamps, and explicit report shape
contracts.

The Phase 13E-D planning/evidence doc is
[PHASE_13E_D_SYNTHETIC_NO_SEND_DEMO.md](PHASE_13E_D_SYNTHETIC_NO_SEND_DEMO.md).
The Phase 13G decision packet is
[PHASE_13G_PRE_LIVE_READINESS_MATRIX.md](PHASE_13G_PRE_LIVE_READINESS_MATRIX.md).
The Phase 14-A/B preparation artifact is
[PHASE_14_AB_FIRST_LIVE_PILOT_PREP.md](PHASE_14_AB_FIRST_LIVE_PILOT_PREP.md).
The pre-Phase-14-C candidate-selection preparation artifact is
[PHASE_14_CANDIDATE_SELECTION_PREP.md](PHASE_14_CANDIDATE_SELECTION_PREP.md).
The Phase 14-C candidate decision-gate artifact is
[PHASE_14C_DECISION_GATE.md](PHASE_14C_DECISION_GATE.md).
The Phase 14-C candidate decision-support artifact is
[PHASE_14C_CANDIDATE_DECISION_SUPPORT.md](PHASE_14C_CANDIDATE_DECISION_SUPPORT.md).
Phase 14-A/B preparation must remain proposed-only and must not authorize,
activate, schedule, or run a live pilot.

## Future Blocked Work

Phase 14-C live pilot work is future work and is blocked until Chris
explicitly approves design, scope, readiness evidence, and the narrow live rail
or pilot being considered. The recorded candidate-review tracking decision
remains separate from candidate approval for execution and live activation.
The decision gate records evidence and wording that Chris should review before
any future movement beyond candidate-review tracking only.
The candidate decision-support artifact records review questions and an
unfilled template only; it does not select approve, reject, or defer.
The candidate decision-support validator records no human decision and only
preserves the unfilled/blocked repo-local report boundary. Its invariant tests
remain repo-local and do not select approve, reject, or defer. Blocked-report
sanitization and report shape tests do not grant live access or expose unsafe
input values.

Phase 14 must not be inferred from completion of Phase 13E-D, Phase 13F docs,
readiness reports, activation checklists, Phase 13G, or Phase 14-A/B
preparation.

## Phase And Work Packet Semantics

Phase labels describe product maturity and safety posture. Work packets
describe how much Codex/Fable may do before stopping for human review.

A work packet may span multiple inert subphases when Chris approves that
bounded envelope. This can include docs/control-plane alignment, tests,
fake/local adapters, read-only/report-only surfaces, no-send workflows,
previews, dry-runs, and safe dev/test work.

A work packet may not cross into live activation, credentials/OAuth/API keys,
production DB paths, protected paths, scheduler/background/LaunchAgent/
crontab/daemon work, OpenClaw runtime operation, external runtime writes,
live model/API providers, high-stakes execution, major product decisions, or
merge approval without explicit Chris approval.

The canonical work packet protocol is
[AGENT_WORK_PACKET_PROTOCOL.md](AGENT_WORK_PACKET_PROTOCOL.md).

Phase 14-A/B is the current pre-live preparation boundary unless blockers are
found.

Future Phase 14 should be structured as:

- Phase 14-A: first live pilot design, no activation.
- Phase 14-B: pilot gates and fail-closed implementation, no live mutation
  unless explicitly approved.
- Phase 14-C: first approved live pilot.

## Completed Phase Groups

- Phase -1: repo scaffold and initial docs.
- Phase 0: approved read-only inventory.
- Phase 1: runtime stabilization foundation.
- Phase 2: dashboard/state foundation.
- Phase 3: routine engine foundation.
- Phase 4: priority engine foundation.
- Phase 5: Todoist and Calendar preview/fake module foundation.
- Phase 6: Composer packet and fake model foundation.
- Phase 6B: fake/local Composer smoke validation.
- Phase 7: report jobs and chart-pack foundation.
- Phase 7B: fake/local report smoke validation.
- Phase 8: fitness integration contract foundation.
- Phase 8B: fake/local fitness smoke validation.
- Phase 9: correctness hardening.
- Phase 9B: dev/test runtime DB bootstrap foundation.
- Phase 10A: local Today View dashboard foundation.
- Phase 10B: no-send briefing loop foundation.
- Phase 10C: dashboard briefing visibility.
- Phase 11A: ChatGPT synthesis import preview foundation.
- Phase 11B: dashboard synthesis import preview.
- Phase 12A: no-send operator CLI.
- Phase 12B: side-effect/idempotency ledger foundation.
- Phase 13A: approved local synthesis apply into dev/test SQLite only.
- Phase 13B: synthesis apply atomicity and recovery hardening.
- Phase 13C: scheduler simulation records and CLI.
- Phase 13D: checkpoint hardening.
- Phase 13E-A: unified operator status report shape.
- Phase 13E-B: CLI discovery and completion-summary polish.
- Phase 13E-C: dashboard safe-action/status polish, complete via PR #28.
- Phase 13E-D: synthetic end-to-end no-send demo, complete via PR #31 with
  post-merge STATUS refresh via PR #32.
- Phase 13F-A: pre-live readiness policy docs.
- Phase 13F-B: inert readiness evaluator.
- Phase 13F-C: read-only readiness status surfaces.
- Phase 13F-D: activation checklist and first-live pilot protocol docs.
- Phase 13G: pre-live readiness matrix and Long-Run Agent Work Packet Protocol
  v1, complete via PR #33 with post-merge STATUS refresh via PR #34.
- Phase 14-A/B: first live pilot preparation, proposed-only design, and
  fail-closed scaffolding, complete via PR #35. No live pilot authorized or
  run.
- Pre-Phase-14-C candidate-selection preparation: inert candidate-selection
  process, blank fail-closed template, and validator scaffolding, complete via
  PR #37. Clean Kitchen Countertops and Stovetop is recorded for
  candidate-review tracking only via PR #40. No Todoist candidate is approved,
  authorized, activated, or run.
- Phase 14-C candidate decision gate: inert docs/test decision boundary for
  future human review of the recorded candidate. No Phase 14-C approval,
  candidate approval, execution authorization, live service access, dynamic
  cleaning implementation, Watch Tower adoption, `.agent/`, `CLAUDE.md`, or
  runtime/operator scaffolding.
- Phase 14-C candidate decision support: inert docs/test review checklist and
  unfilled false-default decision-record template for the recorded candidate.
  No approve/reject/defer decision selected, no Phase 14-C approval, no
  candidate approval, no candidate authorization, no activation or execution,
  and no live service access.
- Phase 14-C candidate decision-support validator: inert source/test report
  helper for the unfilled false-default decision record. It emits
  `decision_needed` or `blocked`; it does not record approve, reject, or defer.
  Unknown schema fields, nested payloads under known fillable fields, every
  fillable decision field, every required false field, and unsupported status
  values fail closed. Blocked reports do not echo unsafe input values, and
  default report timestamps remain deterministic. Report and validation payload
  shape contracts remain explicit.

## Historical Boundary Reference

These retained phrases document stable phase safety contracts without making
old phases the current status source.

- Phase 7: Weekly Chart Pack and report jobs are coded jobs. ChatGPT is the
  interpretation layer. TradingView alerts are manually supplied. There is no
  live market data fetching, no TradingView API, no investment
  recommendations, no portfolio execution, no scheduler, no production SQLite,
  and no dashboard UI.
- Phase 8 Fitness Integration Foundation: the existing CSV-based local fitness
  tracker is preserved. There is no Notion dependency, no live PersonalOS CSV
  reads or writes, no Apple Health or wearable API integration, no workout
  recommendation engine, no Todoist/Calendar/Gmail writes, no scheduler or
  LaunchAgents, no production SQLite/runtime state, and no dashboard UI yet.
- Phase 9B Runtime DB Bootstrap Foundation: local/dev-preview only,
  backup-before-migrate, MVP preview seed profile, no-send, no live external
  write permission, no scheduler, no daily briefing generation loop, and no
  production runtime activation.
- Phase 10A Local Dashboard Today View Foundation: Personal OS Today View,
  read-only local dashboard shell, localhost-only by default, no public
  internet exposure, no live Todoist writes, no task/calendar mutation from
  dashboard, no scheduler activation, and no production runtime activation.
- Phase 10B No-Send Daily Briefing Loop Foundation: manual export only, no
  Gmail sending, no live model calls, no scheduler or LaunchAgents, no
  Todoist/Calendar writes, fake Composer path only, and completion report.
- Phase 10C Dashboard Briefing Integration: Briefing Outputs section, manual
  export preview is read-only, completion report safety flags, no generation
  button, no scheduler activation, no Gmail/model/Todoist/Calendar writes, and
  future real-content redaction.
- Phase 11B Dashboard Synthesis Import Preview UI: ChatGPT Synthesis Import
  Preview, Preview import, `/synthesis-import/preview`,
  `synthesis_import_dev_test_write`, `synthesis_import_dev_test_preview`,
  `synthesis_import_dev_test_read`, only `synthesis_import_previews`, no apply
  permission, no apply/save, no PersonalOS Markdown writes, no
  Todoist/Calendar/Gmail writes, no live model/API calls, localhost-only, and
  no LAN/public bind relaxation.
- Phase 12A Operator CLI: `personalos status`,
  `personalos briefing preview`, `personalos synthesis preview`,
  `personalos dashboard render`, explicit `--db`, explicit `--output-file`,
  input paths, no live model/API calls, no scheduler activation, no
  LaunchAgents, and no production runtime activation.
- Phase 12B: side-effect and idempotency foundations with
  `external_write_intents`, `external_write_attempts`, and
  `idempotency_records`; `no_external_writes=true`, `no_send_mode=true`,
  `live_write=false`, no live Todoist writes, no live Calendar writes, no
  PersonalOS Markdown writes, no scheduler, no LaunchAgents, and no production
  DB activation.
- Phase 13D: read-only except explicit local synthesis preview, synthesis
  preview record creation,
  `PYTHONPATH=src python3 -m unittest discover -s tests -p`, running without
  it can produce misleading import failures, no live/prod rails, no Apply
  button, no live rail, and no external write.

### Exact Phrase Index

The following exact lowercase phrases are intentionally retained for doc
boundary tests and audit search:

- phase 7
- weekly chart pack
- report jobs are coded jobs
- chatgpt is the interpretation layer
- tradingview alerts are manually supplied
- no live market data fetching
- no tradingview api
- no investment recommendations
- no portfolio execution
- no scheduler
- no production sqlite
- no dashboard ui
- phase 8 fitness integration foundation
- existing csv-based local fitness tracker is preserved
- no notion dependency
- no live personalos csv reads or writes
- no apple health or wearable api integration
- no workout recommendation engine
- no todoist/calendar/gmail writes
- no scheduler or launchagents
- no production sqlite/runtime state
- no dashboard ui yet
- phase 9b runtime db bootstrap foundation
- local/dev-preview
- backup-before-migrate
- mvp preview seed profile
- no-send
- live external write permission
- no daily briefing generation loop
- no production runtime activation
- phase 10a local dashboard today view foundation
- personal os today view
- read-only local dashboard shell
- localhost-only by default
- no public internet exposure
- no live todoist writes
- no task/calendar mutation from dashboard
- no scheduler activation
- phase 10b no-send daily briefing loop foundation
- manual export only
- no gmail sending
- no live model calls
- no todoist/calendar writes
- fake composer path only
- completion report
- phase 10c dashboard briefing integration
- briefing outputs section
- manual export preview is read-only
- completion report safety flags
- no generation button
- no gmail/model/todoist/calendar writes
- future real-content redaction
- phase 11b dashboard synthesis import preview ui
- chatgpt synthesis import preview
- preview import
- /synthesis-import/preview
- synthesis_import_dev_test_write
- synthesis_import_dev_test_preview
- synthesis_import_dev_test_read
- only `synthesis_import_previews`
- no apply permission
- no apply/save
- no personalos markdown writes
- no live model/api calls
- localhost-only
- no lan/public bind relaxation
- phase 12a
- operator cli
- personalos status
- personalos briefing preview
- personalos synthesis preview
- personalos dashboard render
- explicit `--db`
- explicit `--output-file`
- input paths
- no launchagents
- phase 12b
- side-effect
- idempotency
- external_write_intents
- external_write_attempts
- idempotency_records
- no_external_writes=true
- no_send_mode=true
- live_write=false
- no live calendar writes
- no production db activation
- phase 13d
- read-only except explicit local synthesis preview
- synthesis preview record creation
- pythonpath=src python3 -m unittest discover -s tests -p
- running without it can produce misleading import failures
- no live/prod rails
- no apply button
- no live rail
- no external write

## Persistent Non-Goals Until Approved

- No live Gmail, Todoist, Google Calendar, PersonalOS Markdown, or OpenClaw
  execution.
- No credential loading or reading.
- No production DB activation.
- No scheduler, LaunchAgent, crontab, daemon, or background-loop activation.
- No external writes or live external service calls.
- No protected path inspection or mutation.

## Phase 13E-D Acceptance Direction

Phase 13E-D should create a deterministic synthetic demo that proves existing
local no-send surfaces can produce one evidence bundle without external
systems. It should not introduce live clients, production runtime state,
credential handling, OpenClaw calls, scheduler activation, or Phase 14 work.
