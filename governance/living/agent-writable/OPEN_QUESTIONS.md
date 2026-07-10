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
- ~~**Q-PO-004** Harness B-00 timing~~ **CLOSED (D-PO-009, 2026-07-07): B-00 first**,
  then P-DESIGN-01 under the orchestrator-driven loop.
- ~~**Q-PO-005** Harness-side third-reviewer gap~~ **CLOSED (2026-07-08)**: the third-reviewer
  seat (GLM 5.2 via OpenRouter) was built, activated, and proven live the same day this was
  raised — every packet since P-CORE-01 has run high-stakes passes through it unattended, with
  real findings caught (P-CORE-02's weekly-target undercounting, P-RAIL-TD-01's idempotency gap,
  P-RAIL-TD-02's kill-doc restart-claim error). No override path was ever needed; this is the real
  fix.
