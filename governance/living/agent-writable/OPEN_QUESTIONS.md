# OPEN_QUESTIONS.md — Personal OS

- **Q-PO-001** P-DEBT-03 orphan disposition: keep-and-wire vs delete for `fitness.py`
  (1.2k LOC, CSV contract), `reports.py` (1.25k), `runtime_bootstrap.py` (1.1k),
  `completion.py`. Per-module Chris call at the P-DEBT-03 gate.
- **Q-PO-002** Production DB path/backup design — needed before P-SCHED-02 (unattended
  writes need a real DB home + restore drill). Owner: P-SCHED-02 G0 plan.
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
- **Q-PO-005** Harness-side: every high-stakes personal-os packet with no third-reviewer
  configured hits `route.STOP_TO_HUMAN` with no built override path (discovered live at
  P-DESIGN-01, 2026-07-08; tracked in the harness repo's `projects/mis/ROADMAP.md` under F1).
  Personal-os's unfamiliar paths are broadly high-stakes-classified, so this recurs on the
  NEXT novel-path packet, not just this one. P-DESIGN-01 was unblocked by a one-time Conductor
  sign-off + manual merge outside the loop — not repeatable. Owner: harness repo (a real
  third-reviewer seat, possibly OpenRouter-backed, or an audited override gate); blocks
  P-CORE-01..03 running unattended through the loop until resolved.
