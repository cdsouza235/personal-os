# OPEN_QUESTIONS.md — Personal OS

- ~~**Q-PO-001** P-DEBT-03 orphan disposition~~ **CLOSED (D-PO-012, 2026-07-10)**: delete
  `fitness.py`, `reports.py`, `completion.py` (zero product imports, no roadmap packet ever
  planned to wire any in). `runtime_bootstrap.py` excluded — it's actively used by test
  infrastructure, not actually orphaned.
- ~~**Q-PO-002** Production DB path/backup design~~ **CLOSED (D-PO-011, 2026-07-10)**:
  `/Users/coldstake/PersonalOS/personal_os.db`, SQLite Online Backup API for the primary backup
  mechanism (not a raw file copy — corruption risk), Time Machine as secondary safety net.
  Unblocks HI-09 for P-SCHED-02.
- ~~**Q-PO-003** Briefing content quality bar for MVP~~ **CLOSED, 2026-07-09**: Chris reviewed
  the real generated `readable_text` (multiple due routines, mixed new/carried-over priorities
  and followups) and accepted the deterministic-template baseline as good enough to ship the
  loop — approved P-BRIEF-01 to merge as-is. He separately shared a richer target format (see
  **Q-PO-006**) as future direction, not a blocker for this packet.
- **Q-PO-006** Richer briefing format + reply-code progress logging (Chris's own example,
  2026-07-09, explicitly "not stuck to it... want the most intuitive design"): checkbox-style
  routine blocks with calendar TIME ranges + per-routine INSTRUCTION text (not just names);
  weekly-target/GTG routines showing exact per-exercise progress (`18/45 complete — 27
  remaining`, not just a shortfall count); a text/email REPLY-CODE system (e.g. `901` = "add one
  GTG micro-round", `pike 5` = "add 5 reps to Pike Push-Up only") that parses a reply and maps it
  to a routine completion update. Two genuinely separate pieces of work: (a) richer RENDERING
  over data already flowing through the pipeline (routine notes/instructions,
  `compute_due_and_owed`'s owed-amount numbers) — straightforward follow-on to P-BRIEF-01; (b)
  the reply-code parser/mapper — a real new feature (this is the mechanism D-PO-010 already named
  as "GTG progress reporting is reply-based (email or Todoist reply)" but nothing has built yet),
  needs its own design pass, not a bolt-on to a rendering packet. Deferred, not scheduled to a
  specific ROADMAP packet number yet — surface this when scoping the next briefing-related
  packet. Owner: Chris (design input) / next briefing packet's builder task.
- **Q-PO-007** Go-live pre-flight + model-generated briefing direction (2026-07-13): with
  every ROADMAP.md packet merged, Chris decided NOT to flip any rail live yet — three real
  gaps surfaced first. (1) **HI-05** (seed routine list) is genuinely unresolved: no seed
  data exists anywhere in the repo/DB right now, confirmed by direct search, not inferred.
  Chris will provide his real routine list. (2) **HI-04** (cadence/missed-behavior model
  matches how Chris actually lives) needs a dedicated working session once the list
  arrives: inventory his real routines against the model's actual fields (cadence, missed-
  day behavior, rotation type, GTG mechanics) one by one. (3) Chris wants to pull forward
  the "Composer/live-model briefings (PRD §18)" future-enhancement (previously "recorded,
  not planned" in ROADMAP.md) — replacing or augmenting the deterministic-template
  briefing with a model call (OpenRouter, GLM 5.2 or Grok 4.5 — same infra pattern as the
  third-reviewer seat) that reviews a co-designed "gold standard template" plus real system
  state and authors the briefing. Chris explicitly wants this carefully spec'd before any
  code, matching the P-DESIGN-01 precedent (a real G6 design decision, not an ad hoc
  build). The real technical stakes flagged in this conversation: a deterministic template
  cannot say anything false (it only renders real data); a model-authored briefing
  introduces a genuinely new failure mode (hallucinated numbers, misstated routines,
  invented instructions) that needs an explicit answer — how the model gets grounded in
  verified state ONLY, and what happens on a failed/malformed call (fail closed to the
  deterministic template, never send unverified content, was Claude's stated recommendation
  in this conversation, not yet a ratified decision). Relates to but is broader than
  Q-PO-006 (which is rendering-richness + reply-codes on the EXISTING deterministic
  pipeline) — this is a different generation mechanism, not just richer output. Not
  scheduled to a packet number. Owner: Chris (design input, including where this design
  conversation itself happens — this repo's governance docs vs. a separate chat) / a future
  G6-shaped design packet.
- **Q-PO-008** HI-05 partial progress + multi-touchpoint reply-driven email loop, sourced
  from Chris's older "White Space Planner — Home + Mind/Body Pilot PRD" v0.1 (2026-05-14,
  OpenClaw-era, uploaded 2026-07-14). That document's execution layer (OpenClaw, cut per
  D-PO-004) does not carry over, but its routine content and Section 11 reply-command
  grammar are real, useful input:
  - **Cleaning** (its Section 7.1, 12 named tasks with rotation order/duration/description)
    maps directly onto the CURRENT confirmed seed list's "Cleaning: rotating pool of 15-20
    tasks, one rotation_group" (D-PO-010) — close to a ready-to-use starting set, pending
    Chris's own adjustment pass (his own words: "baseline... I'll need to adjust").
  - **Reading** (4x/wk) and **Stillness/Prayer/Meditation** (2x/wk) in that document match
    the current confirmed seed list's cadence exactly — independent confirmation Chris's
    thinking has been consistent across this whole gap in time.
  - **Grease-the-Groove**: **CLOSED, 2026-07-14 (R-PO-001)** — moved OUT of the routine-model
    schema entirely. No clean fit emerged for rep-accumulation under the Todoist-as-state
    design (discrete "round" tasks were offered, declined); Chris will fold GTG into a
    separate, more comprehensive fitness-tracking system on his own timeline instead. Not a
    PersonalOS routine-engine concern going forward.
  - **Podcast/Media routine**: NOT in the current confirmed seed list at all (dropped
    somewhere between the old document and D-PO-010). Chris says it's "gotten more
    important" since — now 4x/week, Monday–Thursday evenings, curated YouTube/podcast
    material on markets/AI/crypto, output is interpretation/synthesis notes stored in
    Obsidian. **UPDATE 2026-07-14**: Chris will write a dedicated mini-PRD for this routine
    given how impactful he expects it to be — superseding Claude's earlier proposed
    `specific_days` cadence-type guess; wait for the mini-PRD rather than building against
    the guess.
  - **Monthly thesis review** (consumes the podcast routine's Obsidian notes): **CLOSED for
    now, 2026-07-14** — Chris: keep it outside PersonalOS scope. Not a tracked routine.
  - **Workflow direction — SIMPLIFIED, 2026-07-14 (supersedes the "reply-driven" framing
    below the original 2026-07-13 entry).** Still four daily emails (8am sets up the day;
    12pm/4pm/8pm are check-ins), still no OpenClaw — but Chris eliminated reply-processing
    entirely. Todoist itself is the state: as Chris marks a task complete in the Todoist app
    directly, it drops out of scope for the rest of that day's emails. No reply grammar, no
    ambiguity handling, no matching a free-text reply back to a routine instance.
    This is a MUCH smaller, well-contained addition, not the phase-sized effort the original
    reply-driven framing was. One real gap confirmed by direct code check (not assumed):
    `rails/todoist.py` can currently only CREATE tasks — no code anywhere queries Todoist for
    live completion status. Needs one new capability: a read-only Todoist API call
    (same four-gate rail pattern as every other call, just reading instead of writing), plus
    making sure the morning task-creation step consistently labels what it creates so the
    later queries can filter to "today's routine tasks" specifically and never touch
    anything else in Chris's Todoist account.
  Not scheduled to a packet number. Owner: Chris (podcast mini-PRD, GTG session scheduling)
  / a future design packet for the 4x/day check-in loop (now right-sized, not phase-sized).
- ~~**Q-PO-004** Harness B-00 timing~~ **CLOSED (D-PO-009, 2026-07-07): B-00 first**,
  then P-DESIGN-01 under the orchestrator-driven loop.
- ~~**Q-PO-005** Harness-side third-reviewer gap~~ **CLOSED (2026-07-08)**: the third-reviewer
  seat (GLM 5.2 via OpenRouter) was built, activated, and proven live the same day this was
  raised — every packet since P-CORE-01 has run high-stakes passes through it unattended, with
  real findings caught (P-CORE-02's weekly-target undercounting, P-RAIL-TD-01's idempotency gap,
  P-RAIL-TD-02's kill-doc restart-claim error). No override path was ever needed; this is the real
  fix.
