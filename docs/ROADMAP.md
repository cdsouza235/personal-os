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
contracts. Missing-field matrix tests cover every required text default and
every required false field so absent required fields fail closed as
`decision_needed`. Required unfilled decision-field tests cover every fillable
decision field so absent unfilled fields also fail closed as `decision_needed`.
Blocked-reason sanitization keeps caller-supplied decision
and drift values out of blocked report JSON. Unknown schema key-name
sanitization keeps caller-supplied unknown keys out of blocked report JSON.
Blocked report sanitization matrix tests cover representative unknown-schema,
decision-selection, candidate-drift, and nested-fillable payload inputs.
Nested prohibited-field tests keep caller-controlled nested live/API and
credential/secret values out of blocked report JSON. Strict
required-false-field tests block non-boolean false-like values instead of
accepting them as the unfilled false-default template. Strict
required-text-default tests block case/spacing variants instead of accepting
them as the unfilled template. Strict readiness.status tests block
case/spacing variants instead of accepting them as `not_ready` and keep
caller-controlled readiness drift values out of blocked report JSON.
Required readiness.status tests keep `readiness.status=not_ready` in the
false-default template and make missing readiness status fail closed as
`decision_needed`.
Required unfilled decision-field tests keep every fillable decision field in
the false-default template and make missing fillable fields fail closed as
`decision_needed`.
Strict unfilled decision-field tests block whitespace-only fillable field
values instead of accepting them as the empty unfilled template.
Required-field drift non-echo matrix tests cover every required text default
and every required false field so caller-controlled drift values stay out of
blocked report JSON.
Fillable and prohibited-field non-echo matrix tests cover every fillable
decision field, prohibited live/API field, and prohibited credential/secret
field so caller-controlled values stay out of blocked report JSON.
Report inert false-field matrix tests cover top-level approval, execution,
live rail, credential, scheduler, protected-path, model/API, Watch Tower,
`.agent`, `CLAUDE.md`, runtime scaffold, and external mutation flags.
Report inert true-field matrix tests cover blocked, tracking-only,
merge-is-not-live-authorization, and inert readiness flags.
Contract manifest tests expose and synchronize the false-default
decision-record schema, allowed `decision_needed` / `blocked` status set,
prohibited field groups, report top-level shape, inert false fields, inert
true field paths, raw decision-record echo exclusions, and non-authorization
assertions as structured inert audit metadata.
Report-embedded contract manifest tests verify that the inert report carries
that same static manifest and that blocked reports still do not echo
caller-controlled unsafe input tokens through the manifest field.
Report-contract validator tests verify default and blocked reports against
the static inert contract and make tampered reports fail closed without
echoing unsafe report keys or values in validator output.
Report-contract validator matrix tests cover absent reports, top-level shape
drift, inert false-field drift, inert true-path drift, raw-echo fields, and
validation-payload mismatch.
Report-contract posture matrix tests cover report metadata drift, readiness
payload drift, safety posture field drift, and extra safety posture keys
without echoing caller-controlled values.
Long-run governance now treats the completed bounded packet as the default
PR/audit unit for safe inert repo-local work, so Codex/Fable should bundle
adjacent safe substeps rather than stop after every micro-invariant. Human
judgment conditions remain explicit stop gates for product, safety, scope,
design, secrets, credentials, live-service testing, and validation failures
requiring architectural, product, safety, or workflow judgment. Delegated
repo-merge authority, when Chris grants it for a current loop, is repo merge
authority only and does not authorize Phase 14-C, candidate approval,
candidate authorization, activation, execution, live-service access,
credentials, production DB, scheduler/background behavior, OpenClaw,
protected paths, dynamic cleaning, Watch Tower, `.agent/`, `CLAUDE.md`, or
runtime/operator scaffolding.

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
sanitization, report shape tests, missing-field matrix tests, and
blocked-reason sanitization tests do not grant live access or expose unsafe
input values. Unknown schema key-name sanitization tests preserve the same
non-echo boundary for caller-supplied unknown keys. Blocked report
sanitization matrix tests preserve that boundary across representative blocked
record shapes. Nested prohibited-field tests preserve that boundary for
nested live/API and credential/secret values. Strict required-false-field
tests preserve the false-default boundary for boolean false values only.
Strict required-text-default tests preserve the same boundary for exact
literal text defaults only. Strict readiness.status tests preserve the same
boundary for the exact `not_ready` readiness value only.
Required readiness.status tests preserve the same boundary by requiring the
template to carry that not-ready value.
Required unfilled decision-field tests preserve the same boundary by requiring
the template to carry every fillable decision field as unfilled.
Strict unfilled decision-field tests preserve the same boundary by requiring
the template's fillable decision fields to remain exactly empty.
Required-field drift non-echo matrix tests preserve the same boundary by
checking every required text default drift value and every required
false-field non-boolean value.
Fillable and prohibited-field non-echo matrix tests preserve the same boundary
by checking every fillable decision field value, every prohibited live/API
field value, and every prohibited credential/secret field value.
Report inert false-field matrix tests preserve the same boundary by checking
top-level report flags remain false.
Report inert true-field matrix tests preserve the same boundary by checking
safe blocked/tracking/inert report flags remain true.
Contract manifest tests preserve the same boundary by checking that structured
audit metadata stays synchronized with the template, report, status, and
blocked-field contracts without recording a decision.
Report-embedded contract manifest tests preserve the same boundary by keeping
that manifest available in inert reports without exposing caller-controlled
unsafe input tokens.
Report-contract validator tests preserve the same boundary by checking report
shape, manifest equality, allowed statuses, inert flags, readiness, raw-echo
exclusions, and safety posture without exposing unsafe report keys or values.
Report-contract validator matrix tests preserve the same boundary by checking
each report-contract drift category without adding runtime behavior.
Report-contract posture matrix tests preserve the same boundary by checking
metadata, readiness, and safety-posture drift categories without exposing
caller-controlled values.

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

The completed bounded packet is the default unit for PRs and Claude Code audit
in safe inert long-run work. Codex/Fable should bundle adjacent safe
repo-local substeps into one packet and one audit handoff instead of creating a
separate PR or audit after each micro-invariant, unless the scope becomes
ambiguous, a human judgment condition appears, or a real stop gate is reached.

A work packet may not cross into live activation, credentials/OAuth/API keys,
production DB paths, protected paths, scheduler/background/LaunchAgent/
crontab/daemon work, OpenClaw runtime operation, external runtime writes,
live model/API providers, high-stakes execution, major product decisions, or
merge approval without explicit Chris approval or a current explicit delegated
repo-merge instruction that satisfies all audited-head, mergeable/clean,
validation, clean-worktree, no-drift, and no-open-gate conditions. Delegated
repo-merge authority is not product approval or live authorization.

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
  values fail closed. Missing required text defaults and required false fields
  fail closed as `decision_needed`. Blocked reports do not echo unsafe input
  values, and default report timestamps remain deterministic. Report and
  validation payload shape contracts remain explicit. Blocked reasons avoid
  echoing caller-supplied decision or drift values into report JSON. Unknown
  schema reasons avoid echoing caller-supplied unknown key names into report
  JSON. The blocked report sanitization matrix locks representative non-echo
  cases for caller-controlled tokens. Nested prohibited-field tests lock
  non-echo coverage for caller-controlled nested live/API and
  credential/secret values. Strict required-false-field tests block
  non-boolean false-like values. Strict required-text-default tests block
  case/spacing variants. Strict readiness.status tests block non-exact
  `not_ready` variants. Required readiness.status tests make missing
  readiness status fail closed. Required unfilled decision-field tests make
  missing fillable fields fail closed. Strict unfilled decision-field tests
  block whitespace-only fillable field values. Required-field drift non-echo
  matrix tests cover every required text default and required false field.
  Fillable and prohibited-field non-echo matrix tests cover every fillable
  field and prohibited field group. Report inert false-field matrix tests
  cover top-level false report flags.
  Report inert true-field matrix tests cover safe blocked/tracking/inert
  report flags.
  Contract manifest tests cover structured schema/report/status
  synchronization for inert audit metadata.
  Report-embedded contract manifest tests cover the static manifest inside
  default and blocked reports without echoing caller-controlled unsafe input.
  Report-contract validator tests cover default, blocked, and tampered report
  contract validation without echoing unsafe report keys or values.
  Report-contract validator matrix tests cover absent reports, top-level
  shape drift, inert false/true drift, raw-echo fields, and validation-payload
  mismatch.
  Report-contract posture matrix tests cover metadata, readiness, and safety
  posture drift without echoing caller-controlled values.

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
