# Safety Policy

Last updated: 2026-06-26

## Purpose

Personal OS should remain useful locally while making activation boundaries
explicit. This policy defines protected systems, no-send posture, readiness
requirements, and prohibited work.

The canonical current safety snapshot is [../STATUS.md](../STATUS.md).

## Current Required Posture

Until Chris explicitly approves a later phase that changes these facts, the
repo must report:

- `readiness.status=not_ready`
- `inert_report_only=true`
- `live_rails_activated=false`
- `credentials_loaded=false`
- `credentials_read=false`
- `production_db_path_active=false`
- `scheduler_activated=false`
- `launch_agent_installed=false`
- `crontab_modified=false`
- `daemon_started=false`
- `openclaw_called=false`
- `external_services_contacted=false`
- `external_mutation=false`
- `gmail_touched=false`
- `todoist_touched=false`
- `calendar_touched=false`
- `personalos_markdown_written=false`
- `protected_paths_touched=false`

STATUS.md must be updated whenever the validated safety posture changes.

## Protected Systems

Codex/Fable must not inspect or mutate the following without explicit Chris
approval for that exact scope:

- `/Users/coldstake/PersonalOS`
- `/Users/coldstake/.openclaw`
- credential stores, OAuth files, tokens, secrets, or environment secrets
- production SQLite paths
- production ledgers
- Gmail
- Todoist
- Google Calendar
- LaunchAgents
- crontab
- daemon/background-loop configuration
- OpenClaw runtime files or runtime config
- other production runtime state

## Prohibited Actions

Codex/Fable must not:

- send, draft, read, or mutate Gmail outside a currently approved bounded
  supervised smoke-test step
- write or mutate Todoist outside a currently approved bounded supervised
  smoke-test step
- write or mutate Google Calendar outside a currently approved bounded
  supervised smoke-test step
- write PersonalOS Markdown
- load, read, print, or configure credentials
- activate or mutate production DB paths
- activate a scheduler
- install or modify LaunchAgents
- write crontab entries
- start daemons or background loops
- call OpenClaw outside a currently approved bounded supervised smoke-test
  step
- call live external services
- perform external writes
- start Phase 14

## Long-Run Mode Safety Rule

Long-run Codex/Fable work packets never weaken these safety gates. Long-run
mode only changes how long Codex/Fable may continue inside an approved
repo-local inert envelope before stopping.

After Chris approves a safe long-run envelope, Codex/Fable should prefer a
larger completed bounded packet as the unit of repo work and audit. That
larger packet default may bundle adjacent safe repo-local substeps, but it
does not allow Codex/Fable to skip human judgment conditions or continue past a
real safety gate.

Prompts may narrow safety rules, add stricter stop conditions, or require
extra validation. Prompts may not weaken this policy, `../AGENTS.md`,
[AGENT_WORK_PACKET_PROTOCOL.md](AGENT_WORK_PACKET_PROTOCOL.md), or
[CODEX_WORKFLOW.md](CODEX_WORKFLOW.md).

Live rails, credentials, production DB paths, protected paths,
scheduler/background work, LaunchAgents, crontab, daemons, OpenClaw runtime,
external runtime writes, live model/API calls, and high-stakes execution still
require explicit Chris approval for the exact scope.

Human judgment conditions include any product, safety, scope, or design choice
that cannot be resolved from repo-local evidence; secrets, credentials, OAuth,
API keys, tokens, or credential stores; actual live-service testing; and failed
validation that requires architectural, product, safety, or workflow judgment.
Codex/Fable must stop and ask Chris when those conditions appear.

Delegated repo-merge authority, when Chris grants it for a current long-run
loop, is limited to repo-local, inert, deterministic, testable work with a
clean audited head commit, mergeable/clean state, passing validation, clean
worktree, and no unresolved deviations or open questions. Claude Code audit
must be absent by policy or return `Pass` or `Pass with notes` with no
required fixes. It is repo merge authority only and does not mean product
approval, Phase 14-C authorization, candidate approval, candidate
authorization, candidate activation or execution, live-service access, live
activation, credential handling, production DB activation,
scheduler/background activation, OpenClaw invocation, protected-path access,
dynamic cleaning implementation, Watch Tower adoption, `.agent/`,
`CLAUDE.md`, or runtime/operator scaffolding.

## Readiness And Activation Gates

Before any live-rail work, the repo must satisfy the applicable gates:

- [PRE_LIVE_READINESS.md](PRE_LIVE_READINESS.md)
- [LIVE_RAIL_ACTIVATION_POLICY.md](LIVE_RAIL_ACTIVATION_POLICY.md)
- [ACTIVATION_CHECKLIST.md](ACTIVATION_CHECKLIST.md)
- [FIRST_LIVE_PILOT_PROTOCOL.md](FIRST_LIVE_PILOT_PROTOCOL.md)
- [PHASE_14C_SUPERVISED_SMOKE_TEST.md](PHASE_14C_SUPERVISED_SMOKE_TEST.md)
- [OPERATOR_HANDOFF_CONTRACT.md](OPERATOR_HANDOFF_CONTRACT.md)
- [PRODUCTION_DB_POLICY.md](PRODUCTION_DB_POLICY.md)

These documents and readiness/status reports are policy and evidence surfaces.
They do not authorize live rails, production DB activation, scheduler
activation, OpenClaw runtime operation, credential loading, or external writes
by themselves.

## Phase 14-C Supervised Smoke-Test Boundary

Todoist, Google Calendar, Gmail, and OpenClaw are acceptable low-blast-radius
rails for the bounded Phase 14-C supervised smoke-test plan in
[PHASE_14C_SUPERVISED_SMOKE_TEST.md](PHASE_14C_SUPERVISED_SMOKE_TEST.md).
That plan may prepare and, after Chris explicitly initiates the live-test
step, run at most:

- one clearly marked Todoist test task
- one clearly marked Google Calendar self test event
- one clearly marked Gmail test email to a controlled/self recipient
- one OpenClaw local/test/sandbox smoke invocation

The test marker is
`[Phase 14-C Test] Clean Kitchen Countertops and Stovetop`.

The supervised smoke-test boundary still blocks Calendar recurrence,
uncontrolled Calendar attendees, Gmail uncontrolled recipients, Gmail
attachments, Gmail forwarding, Gmail replies to existing real threads,
scheduler/background behavior, production DB activation, dynamic cleaning,
bulk writes, protected path access, broad OpenClaw runtime handoff, `.agent/`,
`CLAUDE.md`, Watch Tower adoption, and broad runtime/operator scaffolding.

Credential preflight may check that required environment/config entry names
exist. It must not print, inspect, copy, commit, log, or summarize
credential/token values.

Repo prep for the smoke test does not run the live smoke test. The live-test
step remains separate and manually initiated.

## Phase 13E-D / 13G Boundary

Phase 13E-D is implemented and post-merge validated. The planning/evidence
document is
[PHASE_13E_D_SYNTHETIC_NO_SEND_DEMO.md](PHASE_13E_D_SYNTHETIC_NO_SEND_DEMO.md).

Phase 13G is a planning/control-plane readiness matrix. It must not start
Phase 14, authorize a live pilot, or activate any live rail.

## Phase 14-A/B Preparation Boundary

Phase 14-A/B preparation may define a proposed first live pilot envelope and
fail-closed repo-local scaffolding only. The planning/evidence document is
[PHASE_14_AB_FIRST_LIVE_PILOT_PREP.md](PHASE_14_AB_FIRST_LIVE_PILOT_PREP.md).

Phase 14-A/B preparation must not authorize, activate, execute, schedule, or
run a live pilot. It must not create a live Todoist task, configure
credentials, activate production SQLite, start schedulers or background
processes, call OpenClaw, call live model/API providers, contact external
services, perform external writes, or inspect protected paths. Phase 14-C or
any live attempt requires a later explicit Chris approval packet.

## Pre-Phase-14-C Candidate-Selection Boundary

Pre-Phase-14-C candidate-selection preparation may define an inert
candidate-selection process, blank candidate template, fail-closed validator,
and candidate-review tracking record only. The planning/evidence document is
[PHASE_14_CANDIDATE_SELECTION_PREP.md](PHASE_14_CANDIDATE_SELECTION_PREP.md).
The future human decision-gate document is
[PHASE_14C_DECISION_GATE.md](PHASE_14C_DECISION_GATE.md).
The companion candidate decision-support document is
[PHASE_14C_CANDIDATE_DECISION_SUPPORT.md](PHASE_14C_CANDIDATE_DECISION_SUPPORT.md).

Candidate-selection preparation may record a human-selected candidate for
candidate-review tracking only. It must not select a candidate for live
execution, approve, authorize, schedule, activate, execute, or run a live
pilot. It must not create a live Todoist task, configure credentials, activate
production SQLite, start schedulers or background processes, call OpenClaw,
call live model/API providers, contact external services, perform external
writes, or inspect protected paths. Candidate-review tracking, candidate
approval for execution, and approving live activation remain separate later
Chris decisions.

The Phase 14-C candidate decision gate may document required future approval
wording, pre-approval evidence, and inert decision-record templates. It must
not approve Phase 14-C, approve or authorize the candidate, authorize
execution, authorize Todoist/Gmail/Calendar access, invoke OpenClaw, handle
credentials/auth, activate production DB paths, activate scheduler/background
behavior, implement dynamic cleaning, import a 15-task cleaning list,
implement skip/push/bump behavior, implement automatic rescheduling, adopt
Watch Tower, add `.agent/`, add `CLAUDE.md`, or add runtime/operator
scaffolding.

The Phase 14-C candidate decision-support artifact may document review
questions, failure modes, stop conditions, future approval wording, and an
unfilled false-default decision-record template. It must preserve
candidate-review tracking only and Phase 14-C remains blocked. Its repo-local
validator may produce inert `decision_needed` or `blocked` reports for the
unfilled template and unsafe filled records, but it must not record approve,
reject, or defer; approve or authorize a candidate; grant live-service access;
handle credentials/auth; activate production DB or scheduler/background
behavior; touch protected paths; call OpenClaw; implement dynamic cleaning;
adopt Watch Tower; add `.agent/`; add `CLAUDE.md`; or add runtime/operator
scaffolding. Unknown decision-record schema fields must fail closed instead of
being accepted as part of the unfilled template. Nested payloads under known
fillable fields must also fail closed because filling any decision-record field
would record a human decision outside the current blocked posture. The
validator tests must also keep table-driven coverage for every fillable
decision field, every required false field, the known schema field set, and
the allowed `decision_needed` / `blocked` status set. Blocked-report tests
must not echo unsafe input values, and default report timestamps must remain
deterministic unless explicitly overridden. Report and validation payload shape
tests must keep raw decision-record echo fields out of the inert report
contract. Missing required text defaults and required false fields must fail
closed as `decision_needed`. Blocked reasons must avoid echoing caller-supplied
decision or drift values into report JSON. Unknown schema reasons must avoid
echoing caller-supplied unknown key names into report JSON. Blocked report
sanitization matrix tests must preserve the non-echo boundary for
representative caller-controlled tokens. Nested prohibited-field tests must
keep caller-controlled nested live/API and credential/secret values out of
blocked report JSON. Strict required-false-field tests must block non-boolean
false-like values instead of accepting them as the unfilled false-default
template. Strict required-text-default tests must block case/spacing variants
instead of accepting them as the unfilled template.
Strict readiness.status tests must block case/spacing variants instead of
accepting them as `not_ready` and must keep caller-controlled readiness drift
values out of blocked report JSON.
Required readiness.status tests must keep `readiness.status=not_ready` in the
false-default template and make missing readiness status fail closed as
`decision_needed`.
Required unfilled decision-field tests must keep every fillable decision field
present in the false-default template and make missing fillable fields fail
closed as `decision_needed`.
Strict unfilled decision-field tests must block whitespace-only fillable field
values instead of accepting them as the empty unfilled template.
Required-field drift non-echo matrix tests must cover every required text
default drift value and every required false-field non-boolean value so
caller-controlled drift values stay out of blocked report JSON.
Fillable and prohibited-field non-echo matrix tests must cover every fillable
decision field value, every prohibited live/API field value, and every
prohibited credential/secret field value so caller-controlled values stay out
of blocked report JSON.
Report inert false-field matrix tests must cover top-level approval,
execution, live rail, credential, scheduler, protected-path, model/API, Watch
Tower, `.agent`, `CLAUDE.md`, runtime scaffold, and external mutation flags.
Report inert true-field matrix tests must cover blocked, tracking-only,
merge-is-not-live-authorization, and inert readiness flags.
Contract manifest tests must keep the structured audit manifest synchronized
with the false-default decision-record schema, allowed `decision_needed` /
`blocked` status set, prohibited field groups, report top-level shape, inert
false fields, inert true field paths, raw decision-record echo exclusions, and
non-authorization assertions.
Report-embedded contract manifest tests must keep the same static manifest in
default and blocked reports while preserving the blocked-report non-echo
boundary for caller-controlled unsafe input tokens.
Report-contract validator tests must keep default and blocked reports matched
to the static inert contract and must make tampered reports fail closed
without echoing unsafe report keys or values in validator output.
Report-contract validator matrix tests must cover absent reports, top-level
shape drift, inert false-field drift, inert true-path drift, raw-echo fields,
and validation-payload mismatch without weakening the inert, not-ready
posture.
Report-contract posture matrix tests must cover metadata drift, readiness
payload drift, safety posture field drift, and extra safety posture keys
without echoing caller-controlled values or weakening the inert, not-ready
posture.
Report-payload contract tests must keep report decision_option, candidate
tracking payload, decision-record template, validation payload fields,
validation reasons, normalized record, and preflight checklist fail-closed
without echoing caller-controlled values or weakening the inert, not-ready
posture.
Report-payload contract matrix tests must cover missing validation payload
fields, validation payload type drift, missing payload surfaces, and preflight
checklist type drift without echoing caller-controlled values or weakening the
inert, not-ready posture.

The [MVP readiness gap report](MVP_READINESS_GAP_REPORT.md) is an inert,
repo-local audit surface. It may summarize completed repo-local scaffolding,
pending human decisions, and blocked live rails, but it must keep
`readiness.status=not_ready`, `inert_report_only=true`, and
`live_rails_activated=false`. Its source contract must remain deterministic,
pure in-memory, and report-only. Its validator must fail closed on top-level,
readiness, Phase 14-C, non-authorization, list, and safety posture drift
without echoing caller-controlled values in validator output.

The MVP readiness gap report does not approve Phase 14-C, approve a
candidate, authorize a candidate, activate or run a candidate, authorize
live-service access, handle credentials, activate production DB, activate
scheduler/background behavior, invoke OpenClaw, touch protected paths,
implement dynamic cleaning, adopt Watch Tower, add `.agent/`, add
`CLAUDE.md`, or add runtime/operator scaffolding.

The [non-human closure plan](NON_HUMAN_CLOSURE_PLAN.md) may record a
three-to-five-packet Codex/Fable + Claude Code loop for closing remaining
repo-local, inert, deterministic work. It must keep every packet non-human and
non-live: no human decision, no live-service access, no credentials, no
production DB activation, no scheduler/background activation, no OpenClaw
invocation, no protected path access, no dynamic cleaning implementation, no
Watch Tower adoption, no `.agent/`, no `CLAUDE.md`, and no runtime/operator
scaffolding. It does not weaken any human gate.

The [weekend test readiness runbook](WEEKEND_TEST_READINESS_RUNBOOK.md) may
prepare manual test categories, evidence templates, no-go criteria, and
rollback tabletop templates for a future weekend testing pass. It must remain
repo-local, inert, report-only, and non-live. It does not start testing,
authorize live-service testing, approve Phase 14-C, approve or authorize a
candidate, handle credentials, activate production DB, activate
scheduler/background behavior, invoke OpenClaw, touch protected paths, or
grant go/no-go launch approval.

The [dry-run evidence bundle](DRY_RUN_EVIDENCE_BUNDLE.md) may record
temp-only no-send smoke command templates, fake/local fixture surfaces, and a
completion-report validator for the existing Phase 13E-D no-send demo. It
must keep dry-run execution not started by default, repo evidence artifacts
unwritten by default, and all live, credential, production DB,
scheduler/background, OpenClaw, protected-path, and external-write surfaces
blocked unless a separate future human gate explicitly approves them.

The [final non-human handoff](FINAL_NONHUMAN_HANDOFF.md) may record that the
safe repo-local non-human packet artifacts are assembled for review, but it
must keep Claude Code audit required for the current packet, keep
`readiness.status=not_ready`, keep `live_mvp_ready=false`, keep live rails
disabled, and keep candidate approval, Phase 14-C authorization,
live-service access, credential/auth handling, production DB activation,
scheduler/background activation, OpenClaw handoff or invocation, actual
live-service testing, and go/no-go launch approval as separate pending human
gates.

## High-Stakes Domains

Legal, tax, medical, health, investment, portfolio, crypto, relationship,
family-sensitive, external-message, external-meeting, and large-financial
commitment actions require explicit review or manual handling. They must not
be treated as low risk, auto-executed, or routed to live rails without a
separate approved policy and test path.

## Validation Evidence

Safety-sensitive changes should report:

- branch and changed files
- tests run and results
- `git diff --check`
- `git diff --cached --check` when staged files exist
- repo-local `var/` scan
- SQLite/DB artifact scan outside `.git`
- confirmation that protected systems were not touched
- confirmation that live rails, credentials, production DB, schedulers,
  external writes, and OpenClaw remained inactive
