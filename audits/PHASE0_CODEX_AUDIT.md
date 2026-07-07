## Verdict summary

The repository is not a V1-ready Personal OS. It is a heavily tested, repo-local,
inert scaffold with some real local/dev behaviors: SQLite state, Today View,
priority/routine state helpers, no-send briefings, synthesis preview/apply for a
subset of state, and report/ledger machinery. It is not a live production system:
PRD V1 names live Todoist, Calendar, Gmail, PersonalOS Markdown, and OpenClaw
runtime surfaces behind permission gates (`docs/PRD.md:135`, `docs/PRD.md:139`,
`docs/PRD.md:152`, `docs/PRD.md:157`), while the actual product modules mostly
declare themselves dev/test or no-send (`src/personalos/routines.py:1`,
`src/personalos/todoist.py:1`, `src/personalos/calendar_blocks.py:1`,
`src/personalos/composer.py:1`, `src/personalos/briefings.py:1`).

The most honest status is:

- Local state, Today View, fake Composer, and safety gating: `real` for
  repo-local/dev-test use.
- Dashboard, routines, synthesis import/apply, briefings, reports, ledgers:
  `partial`.
- Todoist/Calendar/Gmail/OpenRouter live work: separate bounded smoke clients
  exist and some have already run live, but those are not the V1 product rails.
- PersonalOS Markdown durable notes and protected OpenClaw runtime operation:
  `scaffold-only` or `absent`.
- Readiness remains `not_ready` by design, not merely because of missing config:
  MVP and wide-net readiness reports hardcode non-authorization and live false
  fields (`src/personalos/mvp_readiness.py:20`, `src/personalos/mvp_readiness.py:187`,
  `src/personalos/phase14c_wide_net_readiness_rollup.py:96`,
  `src/personalos/phase14c_wide_net_readiness_rollup.py:140`).

## Q1 Capability matrix

PRD V1 scope and acceptance are at `docs/PRD.md:787` and
`docs/PRD.md:1463`. Verdicts below use only current repo code as ground truth.

| PRD surface or acceptance criterion | Verdict | Modules and evidence |
| --- | --- | --- |
| Modular local-first productivity/routine/priority/execution OS | `partial` | The product vision expects routines, priorities, briefings, Todoist, Calendar, notes, reports, dashboards, and Mac Mini workflows (`docs/PRD.md:135`, `docs/PRD.md:139`, `docs/PRD.md:140`, `docs/PRD.md:141`). The repo has many local/dev foundations, but live rails and runtime operation are explicitly blocked or scaffolded. |
| Local dashboard shell | `partial` | HTML dashboard and JSON routes exist (`src/personalos/dashboard.py:227`, `src/personalos/dashboard.py:473`), but the banner states no task/calendar/routine/priority/briefing/apply/live routes (`src/personalos/dashboard.py:236`, `src/personalos/dashboard.py:239`). It binds localhost only (`src/personalos/dashboard.py:574`, `src/personalos/dashboard.py:593`), so the PRD's "phone/laptop" acceptance is not fully met (`docs/PRD.md:1467`). |
| SQLite state store exists and is backed up | `real` | Core tables cover routines, priorities, Todoist candidates, Calendar blocks, Composer, synthesis import, briefings, reports, and fitness (`src/personalos/state.py:14`). This is real for local/dev use; connections reject production config (`src/personalos/db/connection.py:20`, `src/personalos/config.py:42`). Runtime bootstrap can create backups before migration when the DB already exists (`src/personalos/runtime_bootstrap.py:197`, `src/personalos/runtime_bootstrap.py:217`, `src/personalos/runtime_bootstrap.py:795`). |
| Routine editor can add/edit/disable routines | `partial` | Routine create/update functions exist (`src/personalos/routines.py:49`, `src/personalos/routines.py:78`; storage at `src/personalos/state.py:217` and `src/personalos/state.py:271`). The dashboard explicitly has no routine routes (`src/personalos/dashboard.py:239`), so this is an API/helper, not an editor. |
| Today View shows routines, priorities, tasks, calendar blocks, and status | `real` | Today View assembles routine, priority, follow-up, Todoist candidate, Calendar block, briefing, ledger, scheduler, readiness, permission, and status summaries (`src/personalos/today.py:65`, `src/personalos/today.py:85`, `src/personalos/today.py:89`, `src/personalos/today.py:104`, `src/personalos/today.py:108`). Safety warnings say it is read-only and makes no live calls (`src/personalos/today.py:45`, `src/personalos/today.py:51`). |
| Priority registry | `real` | Priority CRUD and dashboard summaries exist for local/dev use (`src/personalos/priorities.py:33`, `src/personalos/priorities.py:97`, `src/personalos/priorities.py:124`). It is still labeled dev/test-only (`src/personalos/priorities.py:1`). |
| ChatGPT synthesis import can create structured state | `partial` | Preview parses and persists structured candidates locally (`src/personalos/synthesis_import.py:45`, `src/personalos/synthesis_import.py:207`, `src/personalos/synthesis_import.py:258`). Apply is approval-gated, local, and only supports priorities/projects/followups (`src/personalos/synthesis_apply.py:38`, `src/personalos/synthesis_apply.py:129`, `src/personalos/synthesis_apply.py:640`), not routines, Todoist, Calendar, or Markdown notes. |
| Daily routine rules are configurable | `partial` | PRD expects first-class fields such as `cadence_rule`, `preferred_windows`, `missed_behavior`, and `weekly_target` (`docs/PRD.md:945`, `docs/PRD.md:951`, `docs/PRD.md:957`, `docs/PRD.md:961`). Code stores arbitrary `settings_json` (`src/personalos/state.py:224`, `src/personalos/state.py:234`) and can enable/disable routines, but the domain rules are not first-class or enforced. |
| Todoist auto-write for approved low-risk routine tasks after live approval | `scaffold-only` | Product Todoist code previews, writes local SQLite rows, and simulates via a fake client (`src/personalos/todoist.py:38`, `src/personalos/todoist.py:62`, `src/personalos/todoist.py:79`, `src/personalos/todoist.py:133`). The separate Phase 14-C smoke client can POST one task (`src/personalos/phase14c_todoist_live_smoke.py:36`, `src/personalos/phase14c_todoist_live_smoke.py:52`), but that is not a routine auto-write rail. |
| Calendar auto-write for approved self-only blocks after live approval | `scaffold-only` | Product Calendar code mirrors Todoist with preview/local/fake paths (`src/personalos/calendar_blocks.py:38`, `src/personalos/calendar_blocks.py:62`, `src/personalos/calendar_blocks.py:79`, `src/personalos/calendar_blocks.py:133`). The wide-net runner can call an injected Calendar client (`src/personalos/phase14c_wide_net_rehearsal_live.py:113`, `src/personalos/phase14c_wide_net_rehearsal_live.py:352`), but the CLI hardcodes `calendar_client_available = False` (`src/personalos/cli.py:3292`, `src/personalos/cli.py:3297`). |
| Gmail briefings after live approval | `scaffold-only` | Briefing generation is no-send/manual-export only (`src/personalos/briefings.py:39`, `src/personalos/briefings.py:105`, `src/personalos/briefings.py:260`). A separate Gmail SMTP smoke client can send one controlled email (`src/personalos/phase14c_gmail_live_smoke.py:50`, `src/personalos/phase14c_gmail_live_smoke.py:70`), but no product Gmail briefing rail exists. |
| 8 / 12 / 4 / 8 briefings generate from current state | `partial` | Four briefing windows are modeled (`src/personalos/briefings.py:39`) and preview generation builds from Today View and fake Composer (`src/personalos/briefings.py:52`, `src/personalos/briefings.py:105`, `src/personalos/briefings.py:150`, `src/personalos/briefings.py:167`). It is no-send/fake only. |
| Completed Todoist tasks are removed from later briefings once live sync exists | `absent` | PRD requires removal after live sync (`docs/PRD.md:1097`, `docs/PRD.md:1477`). Current Todoist state is candidate/local/fake creation and simulated status updates (`src/personalos/todoist.py:79`, `src/personalos/todoist.py:133`); Today View only counts local candidate statuses (`src/personalos/today.py:198`). I found no live Todoist completion-sync implementation. |
| High-value review/follow-up tasks can be created after permission approval | `partial` | Default permission model allows low-risk high-value review tasks (`src/personalos/permissions.py:34`, `src/personalos/permissions.py:37`, `src/personalos/permissions.py:68`). Synthesis apply can create local followups after approval (`src/personalos/synthesis_apply.py:38`, `src/personalos/synthesis_apply.py:129`, `src/personalos/synthesis_apply.py:249`), but Todoist follow-up auto-write is not integrated. |
| High-stakes execution actions remain gated | `real` | Default permissions require approval for high-value execution, messages, and external calendar events (`src/personalos/permissions.py:38`, `src/personalos/permissions.py:39`, `src/personalos/permissions.py:40`), and any non-low risk requires approval (`src/personalos/permissions.py:68`). Synthesis apply blocks high-stakes candidates (`src/personalos/synthesis_apply.py:681`). |
| Composer model uses narrow state packets only | `real` | Current fake/local Composer packet sections are enumerated and forbidden terms include credentials, tokens, PersonalOS/OpenClaw paths, live APIs, raw notes, and unrestricted file access (`src/personalos/composer.py:69`, `src/personalos/composer.py:90`). Packet validation enforces exact keys and sections (`src/personalos/composer.py:287`, `src/personalos/composer.py:305`), and fake model runs report `network_called=False` (`src/personalos/composer.py:578`, `src/personalos/composer.py:718`). |
| OpenClaw executes validated outputs only after runtime approval | `scaffold-only` | PRD expects approved OpenClaw runtime workflows (`docs/PRD.md:152`, `docs/PRD.md:1481`). Code has a local/test/sandbox harness that explicitly does not call protected runtime (`src/personalos/phase14c_supervised_smoke.py:701`, `src/personalos/phase14c_supervised_smoke.py:706`, `src/personalos/phase14c_supervised_smoke.py:747`) and model smoke code, not a runtime execution rail. |
| Logs/completion reports exist for runtime operations | `partial` | Side-effect intent/attempt ledgers exist for dry-run/simulated rails (`src/personalos/side_effects.py:1`, `src/personalos/side_effects.py:25`, `src/personalos/side_effects.py:298`, `src/personalos/side_effects.py:426`). Report jobs/runs exist via fake runner only (`src/personalos/reports.py:1`, `src/personalos/reports.py:414`, `src/personalos/reports.py:510`). |
| No live production mutation occurs without configured permission | `partial` | Product modules are fail-closed/fake/local; production DB config is unavailable (`src/personalos/config.py:42`, `src/personalos/db/connection.py:20`). However live smoke clients are separate from the central `permissions.py` model and can run when given flags, config, approval text, and credentials (`src/personalos/phase14c_todoist_live_smoke.py:125`, `src/personalos/phase14c_gmail_live_smoke.py:153`, `src/personalos/cli.py:2074`, `src/personalos/cli.py:1987`). |
| Codex/Fable workflow is repo-based and tested | `real` | The repo has extensive docs/tests around inert workflow and gates; `pyproject.toml` exposes `personalos` as the repo CLI (`pyproject.toml:13`). This is real as process governance, not a user-facing V1 capability. |
| PersonalOS Markdown durable notes | `absent` | PRD includes PersonalOS/Markdown durable notes (`docs/PRD.md:154`, `docs/PRD.md:806`). Synthesis apply explicitly sets `no_personalos_writes=True` (`src/personalos/synthesis_apply.py:66`, `src/personalos/synthesis_apply.py:73`), and top-level `personalos/` contains only `.gitkeep` placeholders. |
| Fitness integration hook | `partial` | Fitness source exists but is not imported by non-test source in the import scan; V1 scope only says "hook" (`docs/PRD.md:811`). |
| Weekly chart pack workflow hook | `partial` | Report job types include chart-pack and finance-oriented shells (`src/personalos/state.py:76`, `src/personalos/state.py:90`), but `reports.py` is dev/test-only and fake-runner based (`src/personalos/reports.py:1`, `src/personalos/reports.py:414`). |

## Q2 Dead & duplicated code

Quantification:

- Source under `src/personalos/`: 65 Python files, 43,766 LOC.
- Process/readiness/report-contract heavy subset: 30 files, 15,901 LOC, counting
  `phase14*`, `mvp_readiness`, `nonhuman_closure`, `weekend_test_readiness`,
  `dry_run_evidence`, `final_nonhuman_handoff`, `pre_live_readiness`, and
  `openclaw_model_strategy`.
- Top-level `personalos/`: eight `.gitkeep` placeholder files, 0 LOC:
  `calendar`, `composer`, `evidence`, `gmail`, `priorities`, `reports`,
  `routines`, `todoist`.

No-non-test-import scan:

- `personalos.cli`, 4,677 LOC, has no non-test source importer, but is the
  console entrypoint via `pyproject.toml:13`, so it is not orphaned.
- These modules had no non-test source importers in an AST import scan:
  `completion.py` 155 LOC, `final_nonhuman_handoff.py` 812 LOC, `fitness.py`
  1,207 LOC, `priorities.py` 603 LOC, `reports.py` 1,252 LOC, `routines.py`
  328 LOC, `runtime_bootstrap.py` 1,086 LOC.
- That does not prove they are dead: several are tested library surfaces. It
  does prove many product-looking modules are not wired into an app path or CLI
  command path.

Duplicated logic:

- Permission evaluators are repeated across modules instead of using one shared
  evaluator: examples include `routines.py:194`, `priorities.py:386`,
  `todoist.py:287`, `calendar_blocks.py:295`, `briefings.py:386`,
  `composer.py:857`, `synthesis_import.py:357`, `synthesis_apply.py:438`,
  `fitness.py:893`, `reports.py:880`, `side_effects.py:789`,
  `runtime_bootstrap.py:348`.
- `_permission_decision` is also repeated in many of those modules:
  `routines.py:259`, `priorities.py:525`, `todoist.py:378`,
  `calendar_blocks.py:386`, `briefings.py:735`, `composer.py:1327`,
  `synthesis_import.py:1114`, `synthesis_apply.py:1534`,
  `reports.py:1097`, `side_effects.py:1135`, `runtime_bootstrap.py:1016`.
- Required-text validators are duplicated: `routines.py:310`,
  `priorities.py:577`, `briefings.py:850`, `composer.py:1439`,
  `synthesis_import.py:1327`, `reports.py:1147`, `scheduler.py:1087`,
  `runtime_bootstrap.py:872`, `state.py:4799`.

Code that mostly validates report formats:

- There is a large family of report-contract validators whose primary behavior
  is to enforce inert/non-authorizing shapes, not product behavior:
  `dry_run_evidence.py:308`, `dry_run_evidence.py:400`,
  `phase14c_candidate_decision_support.py:264`,
  `phase14c_candidate_decision_support.py:454`,
  `nonhuman_closure.py:171`, `nonhuman_closure.py:261`,
  `mvp_readiness.py:163`, `mvp_readiness.py:281`,
  `phase14c_wide_net_calendar_operator_packet.py:142`,
  `phase14c_wide_net_calendar_operator_packet.py:204`,
  `weekend_test_readiness.py:376`, `weekend_test_readiness.py:440`,
  `final_nonhuman_handoff.py:315`, `final_nonhuman_handoff.py:472`,
  `phase14c_wide_net_readiness_rollup.py:190`,
  `phase14c_wide_net_readiness_rollup.py:294`.
- Tests are correspondingly contract-heavy: a grep over `tests/` found 232
  hits for `docs_describe`, `contract_is_no_live_report`, `contract_valid`,
  `remains_inert`, `must_remain`, or `report_matches_inert_contract`.

## Q3 Safety enforcement classes

| Rail | Class | Evidence and gaps |
| --- | --- | --- |
| Todoist product module | `enforced-in-code` for fake/local product path | Product code previews, writes local DB rows, or simulates through a required fake client (`src/personalos/todoist.py:62`, `src/personalos/todoist.py:79`, `src/personalos/todoist.py:184`, `src/personalos/todoist.py:195`). No external mutation is reported in these paths (`src/personalos/todoist.py:69`, `src/personalos/todoist.py:123`, `src/personalos/todoist.py:201`). |
| Todoist Phase 14-C smoke | `already-ran-live` plus `enforced-in-code` guard, with convention gap | The smoke client can POST to Todoist (`src/personalos/phase14c_todoist_live_smoke.py:52`). It defaults no-run without `execute_live`, approval text, and config/token (`src/personalos/phase14c_todoist_live_smoke.py:125`, `src/personalos/phase14c_todoist_live_smoke.py:131`, `src/personalos/phase14c_todoist_live_smoke.py:137`, `src/personalos/phase14c_todoist_live_smoke.py:143`). It limits to one create (`src/personalos/phase14c_todoist_live_smoke.py:113`, `src/personalos/phase14c_todoist_live_smoke.py:207`). Gap: standalone approval is only "present", not exact (`src/personalos/phase14c_todoist_live_smoke.py:101`). STATUS says the CA-bundle retry created exactly one Todoist task (`STATUS.md:244`, `STATUS.md:245`). |
| Gmail SMTP smoke | `already-ran-live` plus `enforced-in-code` guard, with convention gap | SMTP client logs in and sends (`src/personalos/phase14c_gmail_live_smoke.py:70`, `src/personalos/phase14c_gmail_live_smoke.py:81`). It defaults no-run without `execute_live`, approval text, required config, and app-password/sender/recipient (`src/personalos/phase14c_gmail_live_smoke.py:153`, `src/personalos/phase14c_gmail_live_smoke.py:159`, `src/personalos/phase14c_gmail_live_smoke.py:165`, `src/personalos/phase14c_gmail_live_smoke.py:171`). Payload is one email, no CC/BCC/attachments/thread (`src/personalos/phase14c_gmail_live_smoke.py:130`). Gap: approval is only present, not exact (`src/personalos/phase14c_gmail_live_smoke.py:117`). STATUS says one controlled Gmail self-send passed (`STATUS.md:232`, `STATUS.md:234`). |
| Google Calendar product module | `enforced-in-code` for fake/local product path | Calendar product code is preview/local/fake only (`src/personalos/calendar_blocks.py:62`, `src/personalos/calendar_blocks.py:79`, `src/personalos/calendar_blocks.py:184`), and fake client results report no network/credentials/mutation (`src/personalos/calendar_blocks.py:54`, `src/personalos/calendar_blocks.py:55`, `src/personalos/calendar_blocks.py:56`). |
| Google Calendar wide-net/live path | `already-ran-live` outside normal product wiring; runner guarded, CLI fail-closed | The wide-net runner can call an injected Calendar client after exact approval, complete config, and duplicate precheck (`src/personalos/phase14c_wide_net_rehearsal_live.py:166`, `src/personalos/phase14c_wide_net_rehearsal_live.py:195`, `src/personalos/phase14c_wide_net_rehearsal_live.py:203`, `src/personalos/phase14c_wide_net_rehearsal_live.py:250`, `src/personalos/phase14c_wide_net_rehearsal_live.py:352`). CLI hardcodes no Calendar client (`src/personalos/cli.py:3297`). STATUS records one Google Calendar event already passed (`STATUS.md:227`, `STATUS.md:229`). Gap: the Calendar connector action is not enforced by product code in `calendar_blocks.py`; repo code mostly records readiness/transcripts. |
| OpenRouter / OpenClaw model lane | `already-ran-live` external API call, not external mutation | OpenRouter client POSTs to `chat/completions` (`src/personalos/openrouter_model_smoke_client.py:15`, `src/personalos/openrouter_model_smoke_client.py:62`). CLI requires `execute_live`, approval text, provider config, and provider value `openrouter` before constructing the client (`src/personalos/cli.py:2215`, `src/personalos/cli.py:2220`, `src/personalos/cli.py:2224`, `src/personalos/cli.py:2246`, `src/personalos/cli.py:2268`). Model strategy caps calls at one primary and one fallback (`src/personalos/openclaw_model_strategy.py:210`, `src/personalos/openclaw_model_strategy.py:217`, `src/personalos/openclaw_model_strategy.py:243`) and reports no tool execution or external mutation (`src/personalos/openclaw_model_strategy.py:445`, `src/personalos/openclaw_model_strategy.py:456`, `src/personalos/openclaw_model_strategy.py:459`). STATUS records live OpenRouter attempts and a CA-bundle pass (`STATUS.md:239`, `STATUS.md:247`). |
| Protected OpenClaw runtime | `scaffold-only`, no protected invocation | The repo-local harness explicitly does not call protected runtime, read credentials, touch protected paths, start background work, or mutate external state (`src/personalos/phase14c_supervised_smoke.py:704`, `src/personalos/phase14c_supervised_smoke.py:706`, `src/personalos/phase14c_supervised_smoke.py:747`). Wide-net safety assertions require `protected_openclaw_runtime_called=False` (`src/personalos/phase14c_wide_net_readiness_rollup.py:162`, `src/personalos/phase14c_wide_net_readiness_rollup.py:173`). STATUS says no protected-runtime OpenClaw invocation has been performed (`STATUS.md:256`, `STATUS.md:257`). |

Safety classification summary:

- `enforced-in-code`: local product paths; pre-live readiness rail disabling;
  synthesis safety blocks; fake Composer; fake/local Todoist/Calendar; CLI
  gating for live smoke clients.
- `convention-only`: standalone smoke approval references for Gmail/Todoist/
  OpenRouter are non-empty strings rather than exact expected values; live smoke
  clients are not integrated with central `permissions.py`; external connector
  Calendar use sits outside the product module.
- `already-ran-live`: Gmail SMTP, Todoist, Google Calendar, and OpenRouter have
  live evidence in `STATUS.md`. Protected OpenClaw runtime has not.

## Q4 The honest readiness answer

`readiness.status=not_ready` is blocked for three different reasons:

1. `pre_live_readiness.py` is a readiness-for-inertness gate, not live readiness.
   It returns `ready` only when every gate is satisfied and all live rails are
   disabled (`src/personalos/pre_live_readiness.py:264`,
   `src/personalos/pre_live_readiness.py:267`,
   `src/personalos/pre_live_readiness.py:273`). It blocks unknown or non-disabled
   rails (`src/personalos/pre_live_readiness.py:416`,
   `src/personalos/pre_live_readiness.py:430`) and blocks activation requests
   by construction (`src/personalos/pre_live_readiness.py:565`,
   `src/personalos/pre_live_readiness.py:571`). So it can reach `ready`, but
   only as "ready while live rails remain disabled."

2. `mvp_readiness.py` cannot produce a live-ready report without code changes.
   It hardcodes `MVP_READINESS_STATUS = "not_ready"` (`src/personalos/mvp_readiness.py:20`,
   `src/personalos/mvp_readiness.py:22`) and returns `live_mvp_ready=False`,
   `inert_report_only=True`, `phase14_c_blocked=True`, and readiness
   `status=not_ready` (`src/personalos/mvp_readiness.py:187`,
   `src/personalos/mvp_readiness.py:191`, `src/personalos/mvp_readiness.py:192`,
   `src/personalos/mvp_readiness.py:195`, `src/personalos/mvp_readiness.py:196`).

3. `phase14c_wide_net_readiness_rollup.py` cannot authorize live execution
   without code changes. Its required false fields include
   `ready_for_live_execution`, `wide_net_live_run_authorized_by_this_report`,
   `calendar_cli_connector_wiring_present`, `credential_values_read`, and
   `external_mutation` (`src/personalos/phase14c_wide_net_readiness_rollup.py:96`).
   The builder returns those fields false and still requires human approval and
   Claude Code audit (`src/personalos/phase14c_wide_net_readiness_rollup.py:240`,
   `src/personalos/phase14c_wide_net_readiness_rollup.py:247`,
   `src/personalos/phase14c_wide_net_readiness_rollup.py:249`,
   `src/personalos/phase14c_wide_net_readiness_rollup.py:250`). Its readiness
   subobject is hardcoded `status: not_ready` (`src/personalos/phase14c_wide_net_readiness_rollup.py:140`).

Blockers by type:

- Technical blockers: no audited Calendar CLI connector wiring
  (`src/personalos/cli.py:3297`; remaining gate at
  `src/personalos/phase14c_wide_net_readiness_rollup.py:502`); product Todoist/
  Calendar/Gmail rails are fake/local rather than V1 automation
  (`src/personalos/todoist.py:1`, `src/personalos/calendar_blocks.py:1`,
  `src/personalos/briefings.py:1`); protected OpenClaw runtime is absent
  (`src/personalos/phase14c_supervised_smoke.py:706`); production config is
  unavailable (`src/personalos/config.py:42`).
- Evidential blockers: fresh explicit human live approval, Claude Code read-only
  audit, SSL cert availability, OpenRouter budget check, sanitized Calendar
  transcript, sanitized wide-net evidence, and evidence crosscheck are all
  remaining gates (`src/personalos/phase14c_wide_net_readiness_rollup.py:490`,
  `src/personalos/phase14c_wide_net_readiness_rollup.py:497`,
  `src/personalos/phase14c_wide_net_readiness_rollup.py:507`,
  `src/personalos/phase14c_wide_net_readiness_rollup.py:512`,
  `src/personalos/phase14c_wide_net_readiness_rollup.py:517`,
  `src/personalos/phase14c_wide_net_readiness_rollup.py:522`,
  `src/personalos/phase14c_wide_net_readiness_rollup.py:527`).
- Decisional blockers: MVP report explicitly lists candidate approval, Phase
  14-C authorization, live-service access, Calendar connector live use,
  credential/auth handling, production DB activation, scheduler/background
  activation, and OpenClaw handoff/invocation as pending human decisions
  (`src/personalos/mvp_readiness.py:63`, `src/personalos/mvp_readiness.py:67`,
  `src/personalos/mvp_readiness.py:68`, `src/personalos/mvp_readiness.py:69`,
  `src/personalos/mvp_readiness.py:70`, `src/personalos/mvp_readiness.py:71`,
  `src/personalos/mvp_readiness.py:72`).

The honest answer: one narrow pre-live evaluator can be made `ready` only while
live rails remain disabled. The canonical MVP and wide-net readiness reports are
non-authorizing and `not_ready` by construction.

## Q5 Structural liabilities

1. Product code and process/audit code are strongly coupled. Today View imports
   operator status, pre-live readiness, scheduler, side-effect ledgers, synthesis
   apply/import, and status surfaces (`src/personalos/today.py:11`,
   `src/personalos/today.py:13`, `src/personalos/today.py:14`,
   `src/personalos/today.py:15`, `src/personalos/today.py:32`,
   `src/personalos/today.py:37`). The MVP report composes candidate-decision
   and wide-net readiness reports (`src/personalos/mvp_readiness.py:10`,
   `src/personalos/mvp_readiness.py:14`, `src/personalos/mvp_readiness.py:174`).
   This makes the repo good at proving it is inert, but it blurs product
   boundaries.

2. `state.py` is a large cross-domain monolith. It centralizes routines,
   priorities, projects, followups, Todoist tasks, Calendar blocks, Composer,
   synthesis import, briefings, reports, and fitness constants in one file
   (`src/personalos/state.py:14`, `src/personalos/state.py:16`,
   `src/personalos/state.py:17`, `src/personalos/state.py:18`,
   `src/personalos/state.py:19`, `src/personalos/state.py:20`,
   `src/personalos/state.py:21`). That improves early velocity but makes schema
   ownership and domain evolution harder.

3. `cli.py` is also a monolith. It is the public entrypoint
   (`pyproject.toml:13`) and contains live-smoke env reads and command handlers
   for many unrelated surfaces, including Gmail (`src/personalos/cli.py:1987`),
   Todoist (`src/personalos/cli.py:2074`), OpenRouter (`src/personalos/cli.py:2198`),
   and wide-net (`src/personalos/cli.py:3292`). This concentrates safety-critical
   branching and product operations in one large file.

4. Routine flexibility is too loose. PRD defines first-class routine/cadence/
   missed-behavior semantics (`docs/PRD.md:945`, `docs/PRD.md:968`,
   `docs/PRD.md:979`), but implementation mostly stores an arbitrary
   `settings_json` blob (`src/personalos/state.py:224`, `src/personalos/state.py:234`)
   and active/paused/enabled flags (`src/personalos/routines.py:249`). That is
   flexible for adding new routines, but weak for correctness, scheduling,
   catch-up rules, and UI editing.

5. Live-rail semantics are split across product fake modules, smoke clients,
   CLI guards, and connector processes. The central permission model is simple
   and useful (`src/personalos/permissions.py:34`, `src/personalos/permissions.py:50`),
   but live Gmail/Todoist/OpenRouter smoke approval checks are separate flag/
   config gates (`src/personalos/phase14c_gmail_live_smoke.py:153`,
   `src/personalos/phase14c_todoist_live_smoke.py:125`,
   `src/personalos/cli.py:2215`). This weakens the claim that "configured
   permission" is the single source of truth for live mutation.

6. The test suite is over-weighted toward preserving report wording and inert
   contract shape. Contract validators such as
   `phase14c_wide_net_readiness_rollup.py:294`,
   `phase14c_candidate_decision_support.py:454`, and
   `final_nonhuman_handoff.py:472` are valuable for governance, but they do not
   prove user-facing workflows. The grep count of 232 test hits for inert/report
   contract wording is a signal that safety proof has outgrown product proof.

## Ways this audit could be wrong

- Static import scanning can miss dynamic CLI dispatch, package entrypoints, or
  modules intentionally imported only by tests. I treated "no non-test import"
  as "not wired into app/product paths," not as proof of dead code.
- I did not inspect protected runtime/personal paths, credentials, live service
  accounts, or external systems. Claims about already-run live actions rely on
  `STATUS.md` repo evidence (`STATUS.md:227`, `STATUS.md:232`,
  `STATUS.md:244`, `STATUS.md:247`) and source code, not live revalidation.
- The audit is source-grounded at the current working tree. Uncommitted local
  changes outside this task or future PRs could change wiring, readiness, or
  live-rail behavior.
- Some "partial" verdicts could be upgraded or downgraded depending on whether
  Chris defines V1 as local/dev MVP or production/live MVP. I used PRD §28 as
  the bar, especially the live-sync and live-approval acceptance bullets.
