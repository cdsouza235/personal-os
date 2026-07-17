# DECISIONS.md — Personal OS (durable decisions; Builder-owned; reversals per SPEC §16.9)

## Locked
- **D-PO-001 Re-baseline in place.** Keep the code (291 commits); replace the governance
  shape (doc-sprawl narrative process → harness-standard machine-checked gates); findings
  audit seeds the ROADMAP. Neither blind-continue nor restart. — Chris, 2026-07-07
- **D-PO-002 MVP = the live morning loop.** Cadence engine computes today; routine tasks
  → Todoist; 8am briefing → Gmail; unattended after P-SCHED-02. Calendar + midday/evening
  windows post-MVP. Flexibility-as-routines-change is a first-class design requirement;
  zero bias toward incumbent design. — Chris, 2026-07-07
- **D-PO-003 Docs retire freely.** No legacy doc is personally load-bearing; all ~25
  phase/readiness docs + old STATUS archive out in P-GOV-01. SAFETY_POLICY content folded
  into RISK_REGISTER/SECURITY (its posture-flag vocabulary is retired with the readiness
  machinery). — Chris, 2026-07-07
- **D-PO-004 OpenClaw is cut.** Its operator role is filled by the harness + P-SCHED
  scheduler; model calls (if ever) go through a rails adapter. The fitness CSV workflow it
  served stays untouched and out of product scope. Re-entry requires a new G6. — proposed
  by Phase 0 findings §7; Conductor "best proposal wins" (2026-07-07); **ratified by
  approving P-GOV-01**.
- **D-PO-005 Governance authorship seam.** The rulebook is authored by the Fable
  (architect/phase-end) seat + Conductor, audited cross-family by Codex; the production
  Builder (Opus) never authors governance (D-004 circularity principle). Same-family
  caveat (Fable/Opus both Anthropic) is carried openly; the Codex audit + live-loop
  adversarial audits are the designed backstop. — 2026-07-07
- **D-PO-006 `not_ready` is retired as a concept.** Replaced by the per-rail activation
  ladder (`inert | soaking | live`, HUMAN_GATES) with Conductor-gated transitions. The
  three by-construction not-ready mechanisms (Phase 0 §5, §8.5) are deleted with
  P-CLEAN-02 rather than satisfied. — 2026-07-07

- **D-PO-007 Governance lives in-repo (Model B) + templates adopted.** The rulebook is a
  self-contained overlay in this repo (`governance/**` + manifest) because the agent
  build-sandbox receives a git-free export of THIS repo — in-repo law is visible to the
  governed agent with no extra B-00 mounting; the portable doctrine (SPEC/LOOP_DOCTRINE)
  stays harness-side, so there is no rulebook duplication (SPEC §7 overlay split). The
  Conductor's `_harness_proposal/` bundle (archived at `archive/harness-proposal/`)
  recommended harness-side (Model A) as its lean; its two templates were adopted into
  `governance/templates/` and its principles were already convergent with the pack.
  Revisit at B-00 (recorded there as an explicit onboarding question); reversal would be
  a G-GOV migration packet. Also fixes Codex plan-audit F7/F9: approvals =
  `audits/signoffs/**`, Conductor-only, manifest-protected. — 2026-07-07

- **D-PO-008 R1(a) ratification.** The Conductor ratifies the P-GOV-01 sign-off embedded
  in packet commit `02951b5` as his own authorship ("I ratify the P-GOV-01 sign-off
  embedded in 02951b5 as mine" — Chris, 2026-07-07, transcribed by Builder per D-014).
  Context: the Fable phase-A checkpoint (R1) found the sign-off entered the tree inside
  the packet build commit — unavoidable bootstrap circularity, as the sign-off store was
  created by that same packet. With this ratification the Phase A approval trail is
  complete. — 2026-07-07
- **D-PO-009 HI-11/Q-PO-004: B-00 first (Option B).** Phase B is preceded by **B-00**
  (harness repo: production CLI + project onboarding, hand-built + Codex/Fable audited,
  NOT dogfooded per SPEC §11). Rationale: the manual loop spent three audit rounds on
  approval-provenance issues that B-00's OS-permissioned approval store prevents by
  construction (closes checkpoint carry R1(b)); the upcoming product stretch
  (P-DESIGN-01 → P-CORE, migrations + engine) is exactly what the orchestrator should
  mechanically enforce. P-DESIGN-01 starts after B-00 drives its first personal-os
  packet. — Chris, 2026-07-07
- **D-PO-010 Routine model + cadence engine design.** Replaces the semantics-free
  `settings_json` blob (Phase 0 finding) with first-class columns on the routine record:
  `cadence_type`, `cadence_config_json` (cadence-specific parameters only, not
  general-purpose state), `missed_behavior_default`, `rotation_group`, `weekly_target`.
  Carries forward the PRD §3.1 baseline cadence types (`daily`, `weekdays`,
  `x_times_per_week`, `weekly`, `every_n_days`, `specific_days`, `rotating_sequence`,
  `manual_only`) and baseline missed-behavior types (`combine_with_next`,
  `bump_schedule_by_one_day`, `carry_forward_within_week`, `skip_and_continue`,
  `escalate_to_review`); adds three new cadence types: `weekly_target_count` (N
  completions anywhere in the week, order-independent), `weekly_target_reps` (a
  rep/quantity target per week, not just a completion count), and
  `rotating_weekday_pool` (a pool of tasks rotating across specific weekdays, distinct
  from the existing generic `rotating_sequence`). Fixed ISO week: all
  `weekly`/`weekly_target_*` accounting uses a fixed Monday–Sunday calendar week, not a
  rolling trailing-7-days window; a weekly target resets at the Monday boundary
  regardless of when in the prior week it was completed. Grease-the-Groove is modeled as
  individual routine rows (one per exercise), all sharing `rotation_group = "gtg"`;
  monthly focus is expressed purely via each row's existing `enabled` flag (enabled rows
  are this month's focus set; no new focus/month field). GTG progress reporting is
  reply-based (email or Todoist reply), the same channel used for the cleaning
  missed-behavior mechanism below, not a dashboard/CLI primary path. Cleaning is a pool
  of 15-20 distinct tasks sharing one `rotation_group` (e.g. `"cleaning"`), advancing
  through the pool one task per due occurrence; unlike routines with a static
  `missed_behavior_default`, a missed cleaning occurrence's handling is chosen
  dynamically, per-occurrence, by Chris's reply (email or Todoist reply) at the time it's
  missed — `missed_behavior_default` is the fallback if no reply arrives, the reply when
  given overrides it for that one occurrence only, carried by the engine's
  `occurrence_overrides` parameter. Engine contract (pure function, no I/O, exhaustively
  table-tested): `compute_due_and_owed(routines, completions, *, as_of_date,
  occurrence_overrides={})` — takes routine definitions, completion history, the date to
  compute for, and an optional per-occurrence override map (keyed by routine+due-date);
  returns the due-today set and any "owed" make-up debt from weekly-target shortfalls;
  deterministic. Seed list confirmed unchanged from PRD §3.1: Cleaning (rotating pool,
  1/day weekdays) · Reading (4x/wk, `weekly_target_count`) · Prayer/Meditation (2x/wk,
  `weekly_target_count`) · Grease-the-Groove (per-exercise rows, `rotation_group="gtg"`,
  `weekly_target_reps` for 45 reps/exercise/wk) · Fitness/Strength (tracked externally,
  surfaced only, unchanged, no schema involvement) · Shutdown/Review (daily evening,
  unchanged `daily`). Scope note: the orphaned `src/personalos/fitness.py` module's
  disposition (Q-PO-001, a P-DEBT-03 decision) is explicitly NOT part of this decision —
  GTG and Fitness/Strength above are routine-engine seed data only. Formalizes the
  Conductor design decision ahead of P-CORE. — Chris, 2026-07-08

- **D-PO-011 Production DB location + backup design (HI-09, closes Q-PO-002).** The production
  SQLite database lives at `/Users/coldstake/PersonalOS/personal_os.db` — the existing protected
  external path already reserved in `governance/SECURITY.md`/`RISK_REGISTER.md` ("never inside
  any packet scope"), not a new location. Backup mechanism: SQLite's own Online Backup API
  (`sqlite3 <source> ".backup <dest>"`, or the equivalent `sqlite3.Connection.backup()` call),
  run on a schedule — NOT a raw filesystem copy, which risks capturing a torn/inconsistent
  snapshot if a write is in progress when the copy happens; the Online Backup API guarantees a
  consistent copy regardless of concurrent activity. Time Machine (or equivalent existing Mac
  backup) remains a SECONDARY safety net for catastrophic disk loss, not the primary defense
  against backup corruption. A restore-drill procedure (documented steps a human follows to
  restore from the `.backup` snapshot) is part of P-SCHED-02's own acceptance, not a separate
  decision. Unblocks P-SCHED-02 (background scheduler activation), which requires HI-09 resolved
  per `audits/human-input-manifest.md`. — Chris, 2026-07-10

- **D-PO-012 P-DEBT-03 orphan disposition (closes Q-PO-001, HI-03).** `fitness.py` (1207 LOC),
  `reports.py` (1252 LOC), `completion.py` (155 LOC) — all "dev/test-only foundation" modules with
  zero non-test imports anywhere in the product code, and no roadmap packet ever planned to wire
  any of them in (unlike `routines.py`/`todoist.py`, which both had real follow-up packets).
  Delete all three. `runtime_bootstrap.py` (1086 LOC) is explicitly OUT of this decision — unlike
  the other three, it IS actively used, by multiple test files' own bootstrap/setup path
  (`test_briefings.py`, `test_synthesis_import.py`, `test_today_dashboard.py`, `test_scheduler.py`,
  `test_cli.py`) — it stays, already correctly disposed as dev/test infrastructure, not a product
  orphan. — Chris, 2026-07-10

- **D-PO-013 Calendar rail OAuth identity + target calendar (closes HI-12).** The OAuth
  credentials (`PERSONALOS_RAIL_CALENDAR_CLIENT_ID`/`_CLIENT_SECRET`/`_REFRESH_TOKEN`) authenticate
  as the sandboxed account (`cdsouza.bot@gmail.com`), not Chris's personal Google account — the
  bot identity holds the credentials, keeping blast radius contained to whatever's been explicitly
  shared with it. `PERSONALOS_RAIL_CALENDAR_CONTROLLED_CALENDAR_ID` is set to Chris's real personal
  calendar (`cdsouza235@gmail.com`), not the bot's own — writable because that calendar has been
  explicitly shared with the bot account with edit permission. Chris chose to point at the real
  calendar from the first live test rather than soak on a throwaway calendar first (the
  lower-risk option offered), given the bot-identity/personal-calendar split already contains most
  of the risk a fully personal-account setup would carry. Unblocks P-RAIL-CAL-02. — Chris,
  2026-07-13

- **D-PO-014 Finalized seed routine list: Cleaning/Reading/Stillness (closes HI-05 for
  these three; Podcast/Media and GTG remain separately tracked/deferred).** Cleaning is a
  13-task rotating pool (sourced from Chris's older White Space Planner PRD Section 7.1,
  plus one addition): Furniture Surfaces, Fabric Vacuum, Stovetop, Kitchen Counters, Living
  Room Floor, Dining Area Floor, Bedroom Floor, Office Floor, Water Leafy Plants, Towels +
  Mats, Master Bathroom Floor, Second Bathroom Floor, and **Kitchen and Foyer Floor**
  (Chris's addition, 2026-07-14: vacuum and Swiffer) — final count, not the "15-20" range
  D-PO-010 estimated; Chris confirmed 13 is sufficient. Missed-cleaning-occurrence handling
  is `bump_schedule_by_one_day` (not the per-occurrence-reply mechanism D-PO-010 originally
  assumed — reply-parsing was eliminated project-wide per Q-PO-008's 2026-07-14 update),
  triggered by a plain state check: the Todoist task for that occurrence is not marked
  complete by end of day. No reply, no dashboard/CLI action needed to trigger the bump —
  purely derived from Todoist completion state, same mechanism as the 4x/day check-in
  loop. Reading (4x/wk) and Stillness (2x/wk) are unchanged from the prior draft —
  `skip_and_continue`, no automatic backfill. **Shutdown/Review is DROPPED** — was never
  fleshed out beyond a name + `daily` cadence type, Chris chose to drop it rather than
  define it now. Podcast/Media awaits Chris's own mini-PRD (Q-PO-008); GTG is out of scope
  per R-PO-001. — Chris, 2026-07-14

- **D-PO-015 Todoist/Gmail live credentials provided, closing HI-06/HI-07.**
  `PERSONALOS_RAIL_TODOIST_TOKEN` is Chris's own personal Todoist account (tasks need to
  live where he actually completes them, not a bot's). Gmail follows the SAME
  bot-identity-holds-the-credential pattern D-PO-013 established for Calendar:
  `PERSONALOS_RAIL_GMAIL_SENDER_ADDRESS` is the sandboxed `cdsouza.bot@gmail.com` (an app
  password, not OAuth — Gmail's simpler auth path), `PERSONALOS_RAIL_GMAIL_CONTROLLED_
  RECIPIENT` is Chris's real personal inbox (`cdsouza235@gmail.com`) — the bot sends, Chris
  reads. All four env vars confirmed set on the Mac Mini, 2026-07-14. Unblocks nothing new
  by itself (TD-02/GM-02 already merged without requiring these — they only ever built
  scaffolding, never made a real call) but these are now genuinely available for real use
  whenever a rail is flipped live. — Chris, 2026-07-14

- **D-PO-016 Knowledge Edge Daily Intelligence Queue — launch-blocking amendment accepted;
  earnings-calendar provider = Financial Modeling Prep (closes part of the PRD's own §10.4/
  §23.4 Phase 0 open decision).** Chris reviewed the full "Personal OS PRD Amendment —
  Knowledge Edge Daily Intelligence Queue" (revision 1.3, uploaded 2026-07-14 — this IS the
  "mini PRD" for the Podcast/Media routine from Q-PO-008, turned out much larger than either
  side expected). Three decisions made in this conversation, before Packet 0A/0B formally
  start:
  1. **Launch-blocking is intentional, not a default to question.** Personal OS's existing,
     already-soak-ready core (routines → Todoist → Gmail briefing, credentials confirmed set
     2026-07-14) will NOT go live independently — Chris chose to wait for Knowledge Edge to
     be ready too, because he considers this potentially "the most high-value part of
     Personal OS" for him. Product fit: the PRD IS the structuring layer for the 4x/week PM
     knowledge-download routine — Chris's own role narrows to listening, interpretation,
     synthesis, and note formation; discovery/curation/dedup/queue-management is what the
     amendment builds.
  2. **No new "Fable" role.** Wherever the amendment says "Fable phase-end audit," use the
     harness's actual existing audit setup as-is (the auditor role + third-reviewer seat
     already proven this session) — not a new, separate role.
  3. **Earnings-calendar provider = Financial Modeling Prep, paid tier**, not the free-only
     IR-page-scraping + SEC EDGAR alternative Claude offered. Chris's own reasoning: "keeps
     it cleaner" — avoids building/maintaining ~20-40 separate per-company IR-page parsers
     (no two company IR sites are structured the same way, and site redesigns silently break
     scrapers) in exchange for a subscription cost. Exact plan tier, entitlement rights
     (§10.4's display/persistence/fixture-rights requirement), and confirmed current pricing
     are explicitly NOT resolved here — real, evidence-based provider-entitlement work is
     Packet 0B's job, not a chat-level guess (Claude's own web research hit FMP's pricing
     page being blocked to automated fetching; only third-party-sourced approximate numbers
     were available, not authoritative). This decision fixes WHICH provider, not its terms.
  Packets 0A–0B (current-state synthesis + repo-grounded plan, per the amendment's own §19)
  have not yet been run through the harness as of this decision. — Chris, 2026-07-14

- **R-PO-001 (2026-07-14) partially reverses D-PO-010's Grease-the-Groove disposition.**
  D-PO-010 modeled GTG as individual routine rows sharing `rotation_group = "gtg"`, cadence
  type `weekly_target_reps` (45 reps/exercise/wk), in-schema like Cleaning/Reading. When
  actually working through how rep progress would get logged day to day (given R-PO-001's
  same-day context: the 4x/day check-in loop dropped reply-based state updates in favor of
  Todoist-completion-as-state), no clean fit emerged — GTG is fundamentally incremental/
  rep-accumulating, not a single completable unit, and modeling it as many small discrete
  "round" tasks was offered but Chris declined it. Chris's call: GTG moves OUT of the
  routine-model schema entirely and gets folded into a separate, more comprehensive fitness-
  tracking system he'll design on his own timeline — the SAME disposition D-PO-010 already
  gave "Fitness/Strength (tracked externally, surfaced only, unchanged, no schema
  involvement)," just extended to cover GTG too. PersonalOS's own routine engine/schema has
  no GTG involvement going forward; if/when the external fitness system exists, PersonalOS
  may surface a read-only summary of it, matching the existing Fitness/Strength pattern —
  not decided yet, not blocking anything. D-PO-010's OTHER content (cadence types, Cleaning/
  Reading/Stillness/Shutdown-Review modeling, the `compute_due_and_owed` engine contract)
  is UNCHANGED and still in force — only the GTG-specific portion is reversed. — Chris,
  2026-07-14

- **D-PO-017 H2 rail-dispatch design decided.** Closes H2 (found independently by two
  phase-end Fable audits: no code routes the morning cycle's computed candidates through
  the rail adapters, even if a rail were live). Fable ran an independent design consult
  (`audits/h2-rail-dispatch-design-consult-fable-report.md`), which Chris and the Builder
  then converted directly into decisions rather than re-litigating each as an open
  question:
  1. **Per-rail independence.** A rail dispatches if it's live; an inert rail still
     previews. No all-or-nothing "whole day" gate — matches the existing activation
     ladder's explicit "one rail at a time, never bundled" posture
     (`governance/HUMAN_GATES.md`).
  2. **New sibling command, not a scheduler mode.** The dispatcher is a new module +
     CLI command (not threaded through `run_scheduler_job_simulated`), because the
     scheduler is a fail-closed simulation harness that actively rejects live-shaped
     job types (`_FORBIDDEN_JOB_TYPE_MARKERS`) and unconditionally stamps
     `SCHEDULER_SAFETY_FLAGS` — weakening that to fit dispatch through it would degrade
     the guarantee for every existing simulated job. `run morning`'s no-send preview
     stays byte-for-byte unchanged.
  3. **Idempotency bug fixed as part of this work, not deferred.** Candidate
     `dedupe_key`/`source_id` currently derive from a per-run `packet_id` (embeds
     wall-clock `started_at`), so two `run morning` invocations for the same date would
     mint different idempotency keys and could silently double-create Todoist tasks —
     contradicting what `TODOIST_ACTIVATION_REVIEW.md` §2 already tells the operator to
     verify. Fix: derive dedupe identity from the day-stable `daily_plan['id']`, not the
     per-run packet id. No separate cycle-level idempotency guard is added — the
     rail-level record becomes sufficient once keyed correctly.
  4. **Gmail dispatch scoped to self-delivery only.** `send_live_gmail_message` hard-
     refuses any recipient but the single configured controlled address
     (`gmail.py:291-307`) — it structurally cannot message third parties. H2 dispatches
     the morning briefing to Chris's own inbox only; "messages to other people" is
     explicitly out of scope, deferred to a future packet if ever wanted.
  5. **Report-and-stop on partial failure, no auto-retry.** If Todoist dispatch
     succeeds and Gmail then fails, the run stops and reports the asymmetry
     explicitly ("Todoist: N dispatched. Gmail: FAILED, not retried.") rather than
     retrying automatically — matches this project's safety-first posture for
     irreversible external actions, and since Todoist dispatches first, a Gmail
     failure never costs Chris visibility into his day.
  6. **Ledger-honesty migration scoped as a separate, sequenced packet, not deferred
     indefinitely.** `migrations/00011` hard-`CHECK`s `live_write = 0` on both
     `external_write_intents`/`external_write_attempts`, and `idempotency_records.status`
     has no `'completed_live'` value — so a real live write today has no honest way to
     record itself in the ledger (both rails currently write `completed_simulated` as a
     workaround). Rather than accept that mislabeling indefinitely, a follow-on packet
     adds the live-capable ledger states before any rail is actually flipped live.
  7. **Building the dispatcher is its own G5 reachability event**, separate from any
     actual rail flip (`HUMAN_GATES.md`'s "ANY code path that can write Todoist / send
     Gmail … becoming reachable" clause) — it merges through the normal harness
     high-stakes path (same as H1/F1/F4), not a lighter one, even though no rail goes
     live as part of it. — Chris + Builder, 2026-07-15
- **D-PO-018 Knowledge Edge Session 1 decisions (partial — credentials pending).** P-KE-00B
  merged (`57bdff4`); Chris then ratified the Session 1 bundle items that need no browser
  work, via structured prompts in the Conductor session (2026-07-15, mobile):
  1. **Source/channel allowlist approved as listed** in `PHASE0_PROVIDERS_AND_ACCESS.md` §6
     (9 podcast feeds §8.1 + video/network channels §10.3). Later additions require explicit
     Conductor acknowledgment before first fetch — never silent.
  2. **IR/webcast redirects: mechanism-only approved.** Concrete vendor-domain list is
     assembled at Packet 3A and returns as its own named approval gate ("Packet 3A
     vendor-domain-list approval") before any live fetch; until then unknown destinations
     quarantine as `Link pending (unknown vendor)`.
  3. **Scope limits approved** for every Session 1 credential: read-only, named endpoints
     only, shadow DB only (`var/shadow/personalos-shadow.sqlite3`), no production writes /
     notifications / Obsidian / scheduler before Sessions 2–3.
  4. **SEC EDGAR user-agent approved:** app name `PersonalOS` + Chris's contact email
     (exact string lives ONLY in `PERSONALOS_RAIL_KE_EDGAR_USER_AGENT` in `.env.local`,
     uncommitted — this repo is public, so the email itself is not recorded here).
  5. **Launch role appendix ratified — 5 seats** (occupants web-verified 2026-07-15):
     Federal Reserve Chair = Kevin Warsh (eff. 2026-05-22, succeeded Powell); U.S. Treasury
     Secretary = Scott Bessent (eff. 2025-01); SEC Chair = Paul Atkins (eff. 2025-04-21);
     CFTC Chair = Michael Selig (confirmed 2025-12-18, sworn in 2025-12-22 — date
     precision corrected 2026-07-16 against CFTC press release 9164-25 during the
     P-KE-1A audit; the original record said "early 2026"); Apple CEO =
     Tim Cook, with **John Ternus effective 2026-09-01** (transition announced 2026-04-20).
     Company-head seats (OpenAI/Anthropic/DeepMind/NVIDIA/AMD) deliberately NOT created —
     current holders are already tracked as named Lane B/C individuals; a seat is added
     via the normal roster gate only if one changes hands. Packet 1A seeds from this list.
  6. **Broad person-search deferral stands** as documented (§3 of the providers doc).
  **Still open before Session 1 closes:** FMP account + API key + entitlement artifacts
  (§2 items 1–6), YouTube Data API key (search.list-restricted) + current quota
  confirmation, both keys into `.env.local` (placeholders already written). Packet 0C's
  bounded probe waits on these. — Chris (Conductor approvals) + Fable seat (record),
  2026-07-15
- **D-PO-019 FMP rejected at real price; earnings coverage moves to a bounded manual
  roster (amends D-PO-016 item 3, closes D-PO-018's FMP open item).** At Session 1
  credential creation Chris verified FMP's actual pricing: earnings/corporate-events
  access requires a ~$50/month tier — the figure D-PO-016 explicitly could not confirm
  when it chose paid-FMP-over-scrapers. Chris rejected it as over budget ("not down with
  that"). Replacement, defined by Chris: a **bounded, rule-defined company roster** —
  top 10 Nasdaq-100 companies + top 3 publicly listed crypto-native companies + top 5
  WGMI-ETF (CoinShares/Valkyrie Bitcoin Miners) constituents, all ranked by market cap
  (~18 names, overlap deduped) — with the roster **refreshed quarterly** (Chris allowed
  quarterly or semi-annual; quarterly recorded as default, aligned to earnings seasons).
  Earnings dates for this universe come from already-approved free sources: SEC EDGAR
  (approved Session 1, no key) + the companies' official IR pages, which the §10.3
  allowlist already admits as "official company/investor-relations channels." D-PO-016's
  anti-scraper rationale targeted an unbounded 20-40-company universe; a fixed ~18-name
  roster with quarterly human refresh does not reopen it. Consequences: the FMP key
  created today is NOT adopted (commented inert in `.env.local`; Chris may cancel the
  account); Packet 0C's probe scope drops FMP and probes EDGAR + YouTube only; the
  concrete roster seed list is built and web-verified in the next KE packet and returns
  to Chris for confirmation (same pattern as the launch role appendix); the providers
  doc + plan get a corresponding docs amendment in that packet, not ad-hoc. — Chris
  (Conductor decision) + Fable seat (record), 2026-07-15
- **D-PO-020 Audit-record convention for harness-run packets (closes phase-end
  checkpoint C5's decision half).** Adopted by Chris ("adopt the audit-record
  convention", Conductor session 2026-07-16). Every harness-run packet commits its
  final-round Codex audit report + last run-record digest to
  `audits/knowledge-edge/packets/<packet>/` (KE track; parallel dirs for other tracks)
  as a Conductor-record commit before the phase closes, with one AUDIT-LOG.md line per
  packet. From Phase 2 onward, per-ROUND reports are copied out at each iteration
  (the harness overwrites AUDIT.md per round). Retroactive backfill for P-KE-00B
  through P-KE-1D carries the final-round-only caveat (see
  `audits/knowledge-edge/packets/README.md`); intermediate-round findings are narrated
  in STATUS.md's Phase 1 entry and the phase-end checkpoint report. C5's other half
  (STATUS catch-up + truthful traceability) closed in P-KE-1D. — Chris (adoption) +
  Fable seat (record), 2026-07-16
- **D-PO-021 Ground-truth sampling window runs ALL-LANES-CONCURRENTLY (Conductor
  sequencing ruling, 2026-07-17).** The formal 14-day sampling window starts when the
  LAST lane goes live (Lane B/C channel + person-search seeding, Lane D adapters —
  Phase 3 + seeding packets), so every lane is measured concurrently by one clock —
  not lane-by-lane as built. Chris's reasoning: one clean measurement of the system
  as it will actually run; one grading effort. Standing guardrail: daily shadow
  collection RUNS ANYWAY from 2026-07-17 as REHEARSAL (bug-flush + Conductor daily
  digest + practice triage) — rehearsal days are excluded from the formal window,
  which begins at last-lane-live. Phase 2's report deliverable and the Phase 2/3
  phase-end checkpoint + Session 2 queue behind the all-lane window. The 14-day
  minimum itself is UNCHANGED (a 7-day variant was considered and dropped as moot
  under this sequencing). — Chris, 2026-07-17
- **D-PO-022 Shadow-scheduler gate GRANTED early (Conductor, "Authorize the shadow
  scheduler", 2026-07-17).** Scope: SCHEDULED (unattended) daily shadow scans ONLY —
  shadow database only, live reads from Conductor-verified-active sources only; the
  §14.4 fence stands in full (no notifications, no Obsidian, no production DB, no
  other scheduled work). Session 2's remaining content (threshold ratification from
  the all-lane report) is NOT granted here. Mechanism note: until P-KE-4A ships the
  product-native dispatcher, the authorized mechanism is Conductor-operated host
  scheduling (launchd) invoking the sanctioned `knowledge-edge shadow scan` CLI —
  operator tooling outside the repo, same class as the supervised-smoke scripts;
  P-KE-4A supersedes it. — Chris, 2026-07-17
