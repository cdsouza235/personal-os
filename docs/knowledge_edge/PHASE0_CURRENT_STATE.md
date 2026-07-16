# Knowledge Edge — Packet 0A: Current-State Synthesis

Status: complete — read/investigate/document only, per the amendment's own §19 Packet 0A
scope ("Inspect canonical PRD, active amendments, architecture, harness, data model, UI,
scheduler, notifications, secrets, Obsidian integration, tests, and open PRs. Identify
conflicts, reuse opportunities, and existing gates. Confirm whether this amendment can be
folded into the active PRD amendment branch/PR.").
Owner: Builder (this packet) · Date: 2026-07-15
Zero product code, zero credentials, zero network requests, zero scheduler/rail changes.
Every claim below cites the exact file and line read to verify it. Where something could not
be verified (no git tooling in this sandbox), that is stated explicitly rather than guessed.

Governance context read first, per the task's own instruction: `governance/living/agent-writable/DECISIONS.md`
D-PO-016 (lines 166–195) records three decisions already made by Chris before this packet
ran: (1) launch-blocking is intentional; (2) "no new Fable role" — use the harness's
existing auditor + phase-end-auditor setup as-is; (3) earnings-calendar provider = Financial
Modeling Prep, paid tier, exact entitlement TBD (Packet 0B's job). [Superseded 2026-07-15:
D-PO-019 rejected FMP at its real price at Session 1; earnings coverage now uses the bounded
market-cap roster via SEC EDGAR + official IR pages — see PHASE0_ROSTER.md. Historical
references to FMP below stand as records of what was true when 0A ran.] All three are treated as
settled below, not re-litigated.

---

## 1. Canonical PRD — structure, numbering, and where this amendment would integrate

The canonical PRD is `docs/PRD.md` (confirmed by its own header: `docs/PRD.md:1`, "Personal
OS — PRD v0.3"; `docs/PRD.md:5` names the harness roles — "Builder=Opus, Auditor=Codex,
Phase-End=Fable, Conductor=Chris" — matching the amendment's own role vocabulary almost
word for word). It is short by design: `docs/PRD.md:8–11` states explicitly "This document
is the product spec only. Process/history live elsewhere... This PRD does not carry a
changelog, PR lists, or per-phase boundary language — that is what killed v0.2." Sections
run 1 (Vision) → 6 (Data), each a few paragraphs (`docs/PRD.md:1–109`, 109 lines total).

**There is no existing mechanism in this repo for representing "active PRD amendments" as a
first-class artifact.** The repo's actual convention for large structural change is:
architecture/design decisions land in `governance/living/agent-writable/DECISIONS.md`
(append-only, one entry per decision, e.g. D-PO-010 at `DECISIONS.md:57–97` for the routine
model) and, once ratified, get folded into `docs/PRD.md` and `docs/ARCHITECTURE.md`
directly as edited prose (see `docs/ARCHITECTURE.md:48–89`, the "Routine model (target
design — D-PO-010...)" section, which is literally D-PO-010's content rewritten into the
architecture doc). There is no `docs/amendments/` directory, no PRD versioning scheme beyond
whole-document revisions (v0.2 → v0.3, archived wholesale to `docs/archive/PRD-v0.2.md`),
and no "amendment" document type anywhere in the repo prior to this packet.

Given that convention, the reasonable integration path for Packet 0B (not this packet's job
to execute, only to identify) is: **a new top-level PRD section** (e.g. "§7 Knowledge Edge
Daily Intelligence Queue") added directly to `docs/PRD.md`, mirroring how the routine model
became PRD §3.1 rather than a separate linked document, plus a corresponding expansion of
`docs/ARCHITECTURE.md`'s system-shape diagram and invariants list. The amendment document
itself (`docs/knowledge_edge/PRD_AMENDMENT_KNOWLEDGE_EDGE.md`, committed by this packet) is
the durable record of the full original proposal — analogous to how `docs/archive/PRD-v0.2.md`
preserves full prior detail while the live PRD stays lean.

**Governance-manifest consequence:** `docs/PRD.md` and `docs/ARCHITECTURE.md` are both
listed as `governance_files` in `GOVERNANCE_MANIFEST.yaml:22–23` — any edit to either is a
G-GOV event per `governance/HUMAN_GATES.md:44` ("Any file in `GOVERNANCE_MANIFEST.yaml`" —
note the manifest itself lists PRD/ARCHITECTURE as protected, so editing *them* triggers the
RISK_REGISTER path-trigger row `governance/RISK_REGISTER.md:17`, "rulebook → G-GOV", not the
manifest-file row). Packet 0B's actual PRD integration edit will therefore be a G-GOV
packet requiring Conductor review of "what rule changed and why" — this is a real,
foreseeable gate on Packet 0B, not a hypothetical.

## 2. Architecture — current shape vs. the 22-entity data model

`docs/ARCHITECTURE.md` (v0.4, `docs/ARCHITECTURE.md:1`) documents a single linear pipeline:
CLI/Dashboard → synthesis import → SQLite state → cadence engine → morning-cycle scheduler
→ briefing/task-planner → permission model → ledgers → rails (`docs/ARCHITECTURE.md:8–26`).
Seven "critical invariants" are enumerated at `docs/ARCHITECTURE.md:28–40`, the two most
relevant to Knowledge Edge being #1 ("Single write path: all state mutation goes through
core APIs; schema only via `migrations/**`") and #5 ("No background execution other than
the one P-SCHED LaunchAgent").

There is **no dashboard/UI structure documented beyond "Today View, routine editor, priority
editor, rail/system status"** (`docs/PRD.md:83–86`, §3.6) — a single localhost-only page
family rendered by `src/personalos/dashboard.py`, not a multi-surface app shell. The
amendment's required surfaces (§14.2 of the amendment: queue dashboard, 7-day upcoming view,
saved queue, watched history, registry views, source health, scan-now, kill switch,
synthesis handoff, yield report, mode indicator) are an order of magnitude larger than
anything the current dashboard renders today; Packet 0B will need to decide whether these
are new routes on the existing `dashboard.py` render path or a new sibling module.

There is **no existing notification mechanism** — see item 5 below.

The existing data model (item 8 below) is organized as one SQLite DB with domain-split
Python modules under `src/personalos/state/`, not 22 named entities; the amendment's
22-entity model (`source`, `person`, `role`, `company`, `media_item`, `scheduled_event`, etc.
— amendment §13.1) has no current analogue in `docs/ARCHITECTURE.md` and would be a
materially larger schema surface than anything currently migrated.

## 3. Harness orchestrator conventions — RUNBOOK/HUMAN_GATES/QUALITY_GATES/RISK_REGISTER vs. actual observed practice

**Audit roles, verified against real files (not assumption):** the repo has exactly two
audit seats, both already built and both already run live this session:
- **Codex** — per-packet auditor, cross-family (OpenAI), standing brief at
  `audits/AUDITOR-BRIEF-codex.md`. Its own text (`audits/AUDITOR-BRIEF-codex.md:5`, "You are
  machine-invoked headlessly; there is no human relay") confirms it runs automatically per
  packet. Verdicts are `accept / accept_with_conditions / reject`
  (`audits/AUDITOR-BRIEF-codex.md:35`).
- **Fable** — phase-end auditor, standing brief at
  `audits/PHASE-END-AUDITOR-BRIEF-fable.md`. This file's own title is literally "Phase-End
  Auditor Standing Brief — Fable" (`audits/PHASE-END-AUDITOR-BRIEF-fable.md:1`) — **"Fable"
  is not a new name this amendment invented; it is the pre-existing, already-in-repo name
  for this project's own phase-end auditor**, distinct from Codex ("NOT a per-packet
  reviewer (Codex owns that, cross-family)" — `audits/PHASE-END-AUDITOR-BRIEF-fable.md:9`).
  A real report in this format already exists at `audits/phase-A-phase-end-fable-report.md`.

This means the amendment's §0 phrase "Codex audits every packet, Fable performs phase-end
audit" is **not a conflict at all — it is an almost-exact restatement of this repo's actual,
already-proven convention**, and D-PO-016's caution ("No new 'Fable' role... use the
harness's actual existing audit setup as-is") is best read as: don't build new tooling for
this, because the tooling and the name already exist and are already wired up. The one place
genuine care is needed: `governance/living/agent-writable/OPEN_QUESTIONS.md:99–104` records
that Q-PO-005 (a distinct "third-reviewer" seat, GLM 5.2 via OpenRouter, for
disagreement-routing / high-stakes passes) was **closed 2026-07-08** — "built, activated,
and proven live the same day this was raised... every packet since P-CORE-01 has run
high-stakes passes through it unattended, with real findings caught." D-PO-016's phrase
"the auditor role + third-reviewer seat already proven this session" (`DECISIONS.md:182`)
is accurate and independently verifiable against this OPEN_QUESTIONS.md entry — it is three
real seats (Codex, third-reviewer, Fable), not two, and all three already exist.

**Gate mechanics, as actually specified:** `governance/HUMAN_GATES.md:34–45` defines G0
(Plan), G1 (Merge), G2 (Money), G3 (Secrets), G4 (Irreversible), G5 (External/Live Rails),
G6 (Design), G7 (Dependency), G-GOV (rulebook change), G-RECOVERY. Approvals are committed
sign-off files at `audits/signoffs/<packet>-<gate>-signoff.md`, authored **only** by the
Conductor (`governance/HUMAN_GATES.md:5–10`) — chat-borne approvals are explicitly void.
`governance/RISK_REGISTER.md:7–24` is the deterministic path-trigger table that promotes a
packet to high-stakes/G-GOV/G4/G5 based on which files it touches; it fails toward
high-stakes for any unmatched path (`RISK_REGISTER.md:3-4`). This is a real, working
mechanism, not aspirational: `audits/signoffs/` already contains four real signoff files
(`P-CLEAN-01`, `P-CLEAN-02`, `P-DESIGN-01`, `P-GOV-01`), confirming the gate has actually
fired and been satisfied multiple times.

**Divergence from the amendment's assumed process, precisely stated:** the amendment's §0
"Execution model — batched human gates" (Sessions 1/2/3 plus asynchronous merge
acknowledgments) is a **new** gate-batching scheme invented for this amendment; it does not
match any existing named gate in `governance/HUMAN_GATES.md`. The existing gate table has no
concept of "Session 1/2/3" — it has G0 through G-RECOVERY, each triggered by content/path,
fired per packet as needed. The amendment's Session model is compatible with the *existing*
gates (each Session is described as satisfying specific G-numbered gates in bulk — e.g.
Session 1 pre-authorizes what would otherwise be per-packet G3/G5 triggers), but Packet 0B
must make this mapping explicit rather than assume the harness already has a "Session"
concept, because it does not. This is a real gap to close, not a paper-over: `HUMAN_GATES.md`
would need a new subsection (or a Knowledge-Edge-specific addendum) describing how the
batched-session model maps onto G3/G5/G-GOV so the orchestrator's mechanical checks
(RISK_REGISTER path triggers) keep working unmodified underneath the new session vocabulary.

**QUALITY_GATES baseline is stale, a known/tracked condition, not a surprise:**
`governance/QUALITY_GATES.md:33` still states the baseline as "809 tests, ~14s" from
P-GOV-01. Independently running the real suite in this sandbox
(`PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py"`, per
`governance/QUALITY_GATES.md:16`) produced **543 tests, all passing, in ~65s** as of this
packet's run. This is not a defect this packet should fix (out of scope — `governance/**` is
listed as a forbidden path for most packets) — `governance/living/agent-writable/STATUS.md:35`
already tracks this exact gap as carry item **R5** ("QUALITY_GATES baseline 809→421 + demo
vocabulary/banner (next G-GOV edit)"), itself now stale (421 vs. the 543 actually observed),
confirming the baseline number drifts forward every phase and is refreshed opportunistically
at G-GOV edits, not automatically. Packet 0B/later Knowledge Edge packets should expect to
carry the same kind of one-line baseline refresh when they land, and should not treat the
"809" figure as ground truth for anything.

**STATUS.md is stale relative to DECISIONS.md and does not reflect the most recent
completed work — read carefully, do not trust its "Current" section as the true state.**
`governance/living/agent-writable/STATUS.md:3–16` ends its narrative at P-DESIGN-01 merged
(routine model design) with "NEXT: P-CORE-01." But `DECISIONS.md` documents real work well
past that point: D-PO-011 (production DB path, 2026-07-10), D-PO-012 (orphan module
deletion, 2026-07-10), D-PO-013 (Calendar OAuth identity, 2026-07-13), D-PO-014 (seed
routine list, 2026-07-14), D-PO-015 (Todoist/Gmail live credentials provided, 2026-07-14).
`governance/living/agent-writable/OPEN_QUESTIONS.md:30–33` independently corroborates this:
Q-PO-007 (2026-07-13) opens with "with every ROADMAP.md packet merged, Chris decided NOT to
flip any rail live yet" — meaning the Phase D rail packets (`governance/ROADMAP.md:101–120`:
P-RAIL-TD-01/02, P-RAIL-GM-01/02, P-SCHED-02) have already been built and merged by
2026-07-13, none of which is reflected in STATUS.md's "Current" bullets. **STATUS.md's own
header calls itself "not trusted"** (`STATUS.md:1`, "git-diff-verified, not trusted") — take
that literally. For Packet 0B and beyond, treat `DECISIONS.md` + `OPEN_QUESTIONS.md` as the
authoritative recent-state record, and STATUS.md's "Current" section as reflecting an
earlier checkpoint, not the present.

## 4. Scheduler — confirmed, direct pattern conflict with the amendment's §15.1 dispatcher

This is the clearest, highest-confidence conflict this packet found, and the amendment's own
prompt anticipated it correctly.

**What actually exists:** `docs/com.personalos.morning.plist` is a real, already-authored
(not yet loaded — `docs/com.personalos.morning.plist:5-9`, "THIS FILE IS AUTHORED ONLY...
Loading it for real is a deliberate, later, Chris only action") launchd property list using
`StartCalendarInterval` with a fixed `Hour`/`Minute` (`docs/com.personalos.morning.plist:73-79`,
Hour=8, Minute=0 — the 8am morning briefing per `docs/PRD.md:65`, §3.3). The file's own
comment block is explicit and deliberate about the omissions:
`docs/com.personalos.morning.plist:36-38` — **"No RunAtLoad, no KeepAlive: this job must not
fire the moment it is loaded, and must not be relaunched by launchd if it exits; both would
fight a clean `launchctl unload` and are exactly what `governance/RUNBOOK.md`'s
'unload-proof' acceptance criterion is guarding against."** This is a single fixed-time job,
once a day, with a hand-designed absence of exactly the two mechanisms
(`RunAtLoad`+recurring interval) the amendment's §15.1 due-work dispatcher requires.

**What the amendment's §15.1 requires:** "a per-user `launchd` LaunchAgent implementing a
single **due-work dispatcher** contract: `RunAtLoad` plus a fixed dispatcher interval...
(allowable range 1–15 minutes; default 5) — that wakes, consults a local due-work table, and
makes no external request unless work is due." This is architecturally the opposite pattern:
continuously-recurring wake-and-check versus once-daily fixed-fire. The amendment needs this
because Knowledge Edge has multiple distinct fire times (4:30pm scan, 6:15am refresh, T-60/
T-15 per-event checks — amendment §7.1) that a single `StartCalendarInterval` cannot express
without either (a) one LaunchAgent per fire time, or (b) the interval-polling dispatcher the
amendment proposes.

**Reconciliation, stated plainly (not papered over):** the two scheduling mechanisms cannot
share one LaunchAgent as currently authored. Real options for Packet 0B to weigh, none of
which this packet decides:
1. **A second, independent LaunchAgent** running the due-work dispatcher pattern, alongside
   the existing `com.personalos.morning` fixed-time agent — two LaunchAgents, cleanly
   separated by label, each independently unload-proof-verifiable per
   `governance/RUNBOOK.md:31-32` ("Scheduler... `launchctl unload` the LaunchAgent (exact
   label recorded in the activation packet's sign-off)"). This preserves
   `docs/ARCHITECTURE.md:36`'s invariant #5 only if that invariant is explicitly revised to
   say "the P-SCHED LaunchAgent(s)" (plural) rather than "the one P-SCHED LaunchAgent" — a
   real, small, explicit ARCHITECTURE.md edit Packet 0B must call out, not silently break.
2. **Multiple fixed `StartCalendarInterval` entries** (one plist can declare an array of
   calendar intervals) for the two daily fixed times (4:30pm, 6:15am), with the T-60/T-15
   per-event checks handled by a short-lived interval-based agent that is itself only loaded
   for the bounded pre-event window rather than running continuously all day — a hybrid that
   stays closer to the existing fixed-time philosophy but adds real complexity to reason
   about "unload-proof" for a dynamically loaded/unloaded second agent.
3. **Redesign the amendment's dispatcher down to fixed intervals only** where possible
   (drop the general due-work table, keep three or four named `StartCalendarInterval`
   entries) and accept that per-event T-60/T-15 checks either don't exist at launch or are
   approximated by a tighter fixed cadence — a scope reduction Packet 0B would need Chris's
   explicit sign-off on, since the amendment's own §7.1 table treats T-60/T-15 checks as a
   named required behavior.

This packet takes no position on which option Packet 0B should choose — only that options 1
and 2 preserve the amendment's functional requirements at the cost of a second scheduling
mechanism existing in the repo (a real, non-trivial deviation from invariant #5 as currently
worded), while option 3 preserves the one-agent invariant at the cost of cutting a named
launch requirement.

**One more concrete, current-state fact relevant to any of the above:** the scheduler is
currently `off` — `src/personalos/status.py:61`, `_SCHEDULER_STATE: str = "off"  # off ->
manual -> background (P-SCHED-01/02, G4+G5)` — and `src/personalos/status.py:82` runs an
**import-time validation gate** on rail/scheduler state ("fail closed"). Any Knowledge Edge
scheduler work is additive against a system that is not yet running any background job for
real, which somewhat lowers the risk of the two-scheduler question (nothing is fighting for
wall-clock time in production yet) but does not remove the architectural question of what
the target end-state looks like.

Separately, `src/personalos/scheduler.py` (1127 lines) is **not** the real P-SCHED
implementation — its own module docstring says "No-send scheduler/runtime-loop simulation
foundation" (`src/personalos/scheduler.py:1`) and its safety-flag dict hardcodes
`launch_agent_installed: False` (`src/personalos/scheduler.py:57`) on every run. The actual
`personalos run morning` CLI command (`src/personalos/cli/today.py:53-100`,
`_command_run_morning`) calls into this simulation module
(`src/personalos/cli/today.py:17,63`, `run_scheduler_job_simulated(... job_type=
"briefing_preview" ...)`) and its report explicitly labels the workflow mode as "inert /
no-send / foreground simulation" (`src/personalos/cli/today.py:86`). Packet 0B should be
aware this module is Phase-13C-era foundation/simulation plumbing that the real plist-driven
scheduler calls through, not itself the scheduler; whether Knowledge Edge's own job types
belong in this same simulation module or a new one is a real Packet 0B design question.

## 5. Notification mechanism — confirmed absent

Searched the full repository (`docs/`, `src/`, `tests/`, `governance/`) for any existing
local-notification, `osascript`, `terminal-notifier`, `UNUserNotificationCenter`, or similar
mechanism. **None exists.** The only notification-shaped code found is the *simulation*
safety-flag vocabulary in `src/personalos/scheduler.py` (e.g. `no_gmail_send`,
`no_gmail_draft` — lines 61-63), which are inert booleans describing what a no-send
simulation run must NOT do, not a notification delivery mechanism. `docs/PRD.md` and
`docs/ARCHITECTURE.md` do not mention macOS notifications at all. The amendment's §15.2
local-notification requirement (queue-ready notification, watched-event reminder, etc.) is
therefore genuinely new work with zero existing primitive to extend — confirmed absent, not
guessed.

## 6. Secrets/credential handling — real, working convention; directly reusable

The convention is real, consistent, and already used by three live rail adapters:
- **Naming:** `PERSONALOS_RAIL_<RAILNAME>_<FIELD>`, e.g.
  `PERSONALOS_RAIL_TODOIST_TOKEN` (`src/personalos/rails/todoist.py:41`),
  `PERSONALOS_RAIL_GMAIL_SENDER_ADDRESS` / `PERSONALOS_RAIL_GMAIL_APP_PASSWORD`
  (`src/personalos/rails/gmail.py:78-79`), `PERSONALOS_RAIL_CALENDAR_CLIENT_ID` /
  `_CLIENT_SECRET` / `_REFRESH_TOKEN` (`src/personalos/rails/calendar.py:98-100`).
- **Access pattern:** read via `os.environ` only, presence-checked before use, never logged
  — e.g. `src/personalos/rails/todoist.py:182` (`credential_present = credential_env_var in
  os.environ`) and `:196` (`token = os.environ[credential_env_var]`), with an explicit
  comment at `:40` "Read via os.environ only; never hardcoded/logged."
- **Governing invariant:** `governance/RUNBOOK.md:4-5` — "**No agent ever holds production
  credentials.** Live-rail runtime uses credentials from the host environment under Chris's
  account; agent sandboxes get name-only preflight." This is exactly the posture the
  amendment needs for EDGAR user-agent identification, YouTube, and (if later adopted)
  broad-person-search credentials (D-PO-019: FMP retired, not a live credential target).
- **Real precedent for exactly this kind of decision:** D-PO-013 (`DECISIONS.md:123-133`)
  and D-PO-015 (`DECISIONS.md:154-164`) already resolved analogous OAuth/API-credential
  identity questions (which account holds the credential vs. which account is the
  read/write target) for Calendar and Gmail/Todoist — a directly reusable precedent
  structure for Packet 0B's EDGAR/YouTube/broad-search credential plan (FMP retired
  per D-PO-019).

**Genuinely stale artifact found here:** `.env.example` (repo root) still documents the
*retired* Phase-14C-era variable names (`PERSONALOS_PHASE14C_GMAIL_CREDENTIAL`,
`PERSONALOS_PHASE14C_TODOIST_TOKEN`, etc. — `.env.example:5-11`) and even still lists
`PERSONALOS_OPENCLAW_MODEL_API_KEY` (`.env.example:14`) despite OpenClaw being cut
(D-PO-004). `src/personalos/rails/todoist.py:39-40` itself documents the real name as
"deliberately renamed from the retired Phase 14-C var — see `.env.example` for the
rationale" — but `.env.example` was never actually updated to show the new
`PERSONALOS_RAIL_*` names side by side with the old ones, so the promised rationale isn't
actually visible there. This is a pre-existing doc-drift bug independent of Knowledge Edge;
Packet 0B should not treat `.env.example` as accurate and should expect to add the KE
provider env-var names to it once real names are chosen (not this packet's job to fix the
existing drift).

## 7. Obsidian integration — confirmed absent

Searched `src/`, `tests/`, `migrations/`, and current (non-archived) `docs/`/`governance/`
for any occurrence of "obsidian" (case-insensitive). **Zero hits in code, tests, or
migrations.** The only mentions anywhere in the repo are in **archived** v0.2 documents
(`docs/archive/PRD-v0.2.md`, six occurrences, e.g. line 12 "Durable notes / memory:
PersonalOS / Obsidian / Markdown"; `docs/archive/ARCHITECTURE-v0.2.md:29`) — both explicitly
superseded and moved to `docs/archive/` per `docs/PRD.md:3` ("replaces v0.2; v0.2 →
`docs/archive/`") — and one live mention in
`governance/living/agent-writable/OPEN_QUESTIONS.md:74-75` (Q-PO-008, describing the
not-yet-built Podcast/Media routine's eventual output as "stored in Obsidian"). **There is
no "Personal OS Obsidian boundary" of any kind in the current, canonical repo state.** The
amendment's phrasing ("Use the existing Personal OS Obsidian boundary if one exists" — its
own §19 Packet 5B) correctly anticipates this might not exist; confirmed: it does not.
Packet 0B/Phase 5 planning should treat Obsidian integration as fully new work with no
existing boundary, path convention, or write-path to extend.

## 8. Existing data model — `state/` package structure and migrations

State is one SQLite database, migrated via sequential numbered files in `migrations/`
(15 files as of this packet: `0001_bootstrap.sql` through `00015_routine_first_class_
cadence_columns.sql`; `migrations/0001_bootstrap.sql:1-3` shows the pattern — plain `.sql`
files, additive by convention, e.g. `migrations/00015_...sql:4-8` uses `ALTER TABLE ...ADD
COLUMN` rather than destructive changes). Application code accesses state through
`src/personalos/state/` — a package (not a single module) that re-exports a "full historical
public API of the former `personalos.state` module (now split by domain across submodules)"
(`src/personalos/state/__init__.py:1-7`), with real domain submodules already in place:
`state/routines.py`, `state/priorities_projects_followups.py`, `state/composer.py`,
`state/briefings.py`, `state/synthesis_import.py`, `state/permissions.py`,
`state/execution_rails_dev_state.py`, plus two modules (`state/fitness.py`,
`state/reports.py`) whose top-level, non-`state/`-package counterparts were ordered deleted
by D-PO-012 (`DECISIONS.md:113-121`) as dead/orphaned — note this is a *different* pair of
files (top-level `src/personalos/fitness.py`/`reports.py` vs. the `state/` package modules
of similar name); this packet did not attempt to resolve whether the `state/` package
versions carry the same disposition, since that is unrelated to Knowledge Edge and outside
this packet's scope.

This is exactly the kind of "existing module" structure the amendment's §13 fallback clause
anticipates choosing between: "If no suitable module exists, use a local SQLite-backed
bounded context with migrations and clear ownership." Given the 22-entity Knowledge Edge
model (amendment §13.1) shares almost no domain overlap with the existing entities
(routines, priorities, projects, followups, composer packets, briefings, permissions) and
given `docs/ARCHITECTURE.md:41-46`'s layering rule that "`state.py`... knows nothing of rails
or briefings" (i.e., domains are already kept structurally separate even within one
package), the more consistent-with-precedent choice for Packet 0B to evaluate is a **new
domain submodule/package** (e.g. `src/personalos/state/knowledge_edge/` or a sibling
top-level package) with its own numbered migrations appended to the existing sequential
`migrations/` directory (continuing from `00016_...`) — reusing the existing
migration-runner and single-database convention rather than standing up a second SQLite
file. This packet does not decide this; it names the real precedent Packet 0B should weigh
it against.

## 9. Tests — structure and conventions

Flat `tests/` directory (confirmed: `find tests -maxdepth 1 -type d` returns only `tests`
itself — no subdirectories), 35 `test_*.py` files as of this packet. Canonical run command,
verified by actually executing it in this sandbox:
`PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py"`
(`governance/QUALITY_GATES.md:16`) → **543 tests, all passing, ~65s** (see §3 above for the
staleness note on the doc's own "809" baseline figure). `governance/QUALITY_GATES.md:50-53`
states the network rule explicitly: "The suite must run with the network unreachable. Any
test that opens a socket to a real service is a defect... Live-rail adapters are tested
against fakes; live verification happens only inside G5-gated activation packets, never in
the suite." `audits/test-strategy.md` defines the actual per-phase acceptance/boundary
pattern already used (Phase A/B/C/D/E boundaries, each with a named acceptance test set and
a Fable checkpoint description — e.g. `audits/test-strategy.md:37-46` for the rails phase).
Knowledge Edge's later validation-strategy packet (Packet 0B item 8) should map its own
phases directly onto this existing per-phase-boundary convention (fake-client contract
tests + gating-order tests + fixture-based end-to-end, matching the amendment's own §20
structure almost exactly) rather than invent a new test-strategy document format.

## 10. Open branches / active PRD-amendment work in flight

**Could not be directly verified — stated plainly rather than guessed.** This sandbox has no
git tooling at all (`git status` → `git: command not found`) and no `.git` directory exists
in the working tree (`ls -la /work/.git` → "No such file or directory"). This is consistent
with D-PO-007's own documented design (`DECISIONS.md:30-40`): "the agent build-sandbox
receives a git-free export of THIS repo." There is therefore no way from inside this packet
to enumerate real open branches, open GitHub PRs, or CI status.

What **can** be determined from the living docs themselves: `governance/living/agent-writable/
STATUS.md`'s own narrative (see §3 above) describes work through P-DESIGN-01 as the most
recent entry it records, but `DECISIONS.md` and `OPEN_QUESTIONS.md` both show real,
committed decisions and closed questions dated as recently as 2026-07-14 (D-PO-016 itself,
the Knowledge Edge acceptance decision, dated 2026-07-14) — meaning packets have continued
to merge past STATUS.md's last update. **There is no evidence anywhere in the docs of any
other in-flight PRD-amendment-sized initiative besides Knowledge Edge itself.**
`governance/ROADMAP.md` (last major edit describing Phase A–E packet decomposition) and
`governance/living/agent-writable/OPEN_QUESTIONS.md` describe only small, already-scoped
follow-on work (Q-PO-006 richer briefing rendering, Q-PO-007's composer/live-model-briefing
idea, both explicitly "not scheduled to a packet number" per `OPEN_QUESTIONS.md:29,55`) —
none of these rise to "active PRD-amendment work" in the sense the amendment's own §0 asks
about (a competing large structural change this should fold into). **Conclusion: there is no
other active PRD-amendment branch/PR to fold this into. Knowledge Edge is genuinely new,
standalone amendment work**, to be integrated into the canonical `docs/PRD.md` directly
(per item 1 above), not merged into some other in-flight initiative.

---

## Conflicts and reconciliation points

1. **Scheduler pattern mismatch (confirmed, highest-confidence finding).** The amendment's
   §15.1 due-work dispatcher (`RunAtLoad` + fixed 1–15 min interval, polling a due-work
   table) is architecturally incompatible with the existing, already-authored
   `com.personalos.morning.plist`'s fixed-time-only `StartCalendarInterval` pattern, which
   was deliberately designed *without* `RunAtLoad`/`KeepAlive` specifically to keep
   `launchctl unload` clean (`docs/com.personalos.morning.plist:36-38`). See §4 above for
   the three reconciliation options; none is free, and Packet 0B must pick one and update
   `docs/ARCHITECTURE.md`'s invariant #5 ("No background execution other than the one
   P-SCHED LaunchAgent") explicitly rather than silently violate it.

2. **The amendment's Session-1/2/3 gate-batching model has no existing counterpart in
   `governance/HUMAN_GATES.md`.** The real gate table is G0–G-RECOVERY, each triggered
   mechanically by file/content patterns (`RISK_REGISTER.md`), not by named human sessions.
   The Session model is a genuinely new governance concept for this repo; Packet 0B needs an
   explicit mapping (not assumed compatibility) from "Session 1 pre-authorizes X" to "which
   G-numbered gate(s) X would otherwise trip," so the orchestrator's existing mechanical
   RISK_REGISTER checks keep functioning underneath the new session vocabulary.

3. **"Fable phase-end audit" is NOT actually a conflict** once verified against real files —
   it is close to a verbatim match for this repo's existing, already-proven
   `audits/PHASE-END-AUDITOR-BRIEF-fable.md` role. Flagging this explicitly because a naive
   read of the amendment before checking the repo could easily mistake it for something to
   build; it is not. (D-PO-016 already anticipated this and pre-empted the misreading.)

4. **STATUS.md is stale and must not be relied on as "current state."** Its own header
   calls it "not trusted"; its narrative ends around P-DESIGN-01 while DECISIONS.md/
   OPEN_QUESTIONS.md document real merged work (rail credentials, Calendar OAuth identity,
   seed routine list) through 2026-07-14. Any future packet (including Packet 0B) should
   read DECISIONS.md + OPEN_QUESTIONS.md as the living source of truth for "what's actually
   happened," not STATUS.md's "Current" section.

5. **`.env.example` is stale** (still Phase-14C-era variable names, still lists a cut
   OpenClaw model-provider key) relative to the real, in-use `PERSONALOS_RAIL_*` convention
   documented in the rails modules themselves. Not a Knowledge Edge-caused problem, but
   Packet 0B should not copy `.env.example`'s existing content as a naming template — it
   should copy the rails modules' actual constants instead, and expect to add (not
   necessarily fix pre-existing drift in) the new KE provider variable names to this file
   when real names are chosen.

6. **`governance/QUALITY_GATES.md`'s "809 tests" baseline is stale** (543 actually observed
   in this sandbox as of this run) — a pre-existing, tracked drift (STATUS.md's own carry
   item R5), not something this packet should fix, but Packet 0B's validation-strategy work
   should not cite "809" as the current baseline in any of its own planning artifacts.

7. **`docs/ARCHITECTURE.md`'s "Missing" list is stale relative to what actually exists.**
   `docs/ARCHITECTURE.md:94-96` (dated 2026-07-08) still lists "rails/ (Phase D), scheduler
   (P-SCHED)" as missing, but `src/personalos/rails/{todoist,gmail,calendar}.py` and the
   real `com.personalos.morning.plist` both already exist, and DECISIONS.md/OPEN_QUESTIONS.md
   confirm rail packets have merged. `docs/ARCHITECTURE.md` was last substantively updated
   for the routine-model design (D-PO-010) and was not revisited for the Phase D rail work
   that followed — a pre-existing doc-currency gap Packet 0B should be aware of when reading
   ARCHITECTURE.md's "current-state delta" section as ground truth.

## Reuse opportunities

- **The rails four-gate pattern** (permission → ledger/dedupe → rail-state → credentials,
  fail-closed, `docs/ARCHITECTURE.md:32-34` invariant #3) is a directly reusable template
  for any Knowledge Edge external-source adapter that itself performs a write-shaped action
  (e.g., none of the read-only discovery adapters need this exact pattern, but any future
  Obsidian-write or notification-send path should follow the identical shape: gate order,
  structured refusal object, fail-closed on missing credential — see
  `src/personalos/rails/todoist.py:1-18`'s own docstring for the canonical description of
  the pattern).
- **The `PERSONALOS_RAIL_<NAME>_<FIELD>` env-var convention** (§6 above) — directly reusable
  naming scheme for EDGAR/YouTube/broad-person-search credentials (FMP retired per
  D-PO-019), with real precedent
  (D-PO-013, D-PO-015) for how to resolve "which account holds the credential vs. which
  target it operates on" questions.
- **The `state/` package's domain-submodule structure** (§8 above) — precedent for adding
  Knowledge Edge as a new domain submodule/package inside the existing single-SQLite-database
  convention rather than standing up a second database file, reusing the existing migration
  runner and numbering sequence.
- **The harness's actual, already-proven audit flow** (Codex per-packet + third-reviewer +
  Fable phase-end, §3 above) — already built, already run live multiple times this session;
  Knowledge Edge packets should plug into this exactly as-is, with no new audit tooling.
- **The per-phase acceptance/boundary pattern in `audits/test-strategy.md`** — Knowledge
  Edge's own phase structure (amendment §19) already maps closely onto this document's
  existing phase-boundary-plus-Fable-checkpoint convention; Packet 0B should extend this
  file (or add a parallel Knowledge-Edge-specific section to it) rather than invent a new
  validation-strategy document format.
- **The activation ladder concept** (`inert | soaking | live` per rail,
  `governance/HUMAN_GATES.md:53-58`) is structurally identical to the amendment's own §14.4
  feature-mode ladder (`disabled → fixture → shadow_live → active_read_only →
  active_with_obsidian_handoff`) — Packet 0B should consider whether Knowledge Edge's modes
  are literally new entries in the same `RAIL_STATES`-shaped mechanism
  (`src/personalos/status.py`) rather than a parallel, separately-implemented state machine.

## Fold-into-active-amendment-work statement

**No other active PRD-amendment-sized work is in flight in this repo right now.** Per item
10 above, this could not be verified via git (no tooling/`.git` in this sandbox), but every
living document available (STATUS.md, DECISIONS.md, OPEN_QUESTIONS.md, ROADMAP.md) shows
only Knowledge Edge itself as amendment-scale work; all other open items in
OPEN_QUESTIONS.md are small, unscheduled follow-ons (richer briefing rendering, a future
composer/live-model design pass), not competing amendments. **Knowledge Edge should be
integrated directly into the canonical `docs/PRD.md`/`docs/ARCHITECTURE.md`** (per item 1
above) as new top-level content, not merged into some other in-flight initiative — there is
none to merge into.

---

## Safety assertions (per the amendment's own §20.4 format, scoped to this packet)

- Live external calls occurred: **no.**
- Credentials created, read, installed, or stored: **no** (existing env-var names were read
  as strings from source files for citation purposes only; no credential values exist in
  this sandbox and none were referenced).
- Production DB paths accessed: **no** (only read the DB path string itself, `/Users/
  coldstake/PersonalOS/personal_os.db`, from `DECISIONS.md`/the plist comment, for citation).
- Real Obsidian paths accessed: **no** (confirmed none exist to access — see item 7).
- Scheduler/background components installed or activated: **no.**
- Notifications enabled: **no** (confirmed none exist — see item 5).
- Todoist/Gmail/Calendar/brokerage/other external services accessed: **no.**
- OpenClaw invoked: **no.**
- Live generative-model inference calls occurred: **no** (this packet is itself Builder
  reasoning/writing, not a Knowledge Edge model-inference call).
- Media/transcripts downloaded: **no.**
- Protected paths accessed: **no** (`GOVERNANCE_MANIFEST.yaml` protected_paths and RUNBOOK/
  RISK_REGISTER protected external paths were read-only inspected, never written).
- Readiness or activation status changed: **no.**
- A merge occurred: **no** (this packet does not merge anything; it produces documents for
  Packet 0B/Session 1 review).
- Files changed: two new files created under `docs/knowledge_edge/`
  (`PRD_AMENDMENT_KNOWLEDGE_EDGE.md`, `PHASE0_CURRENT_STATE.md`); zero existing files
  modified.
- Test suite run for verification purposes only (read-only; no product code touched):
  543 tests, all green, per §3/§9 above.
