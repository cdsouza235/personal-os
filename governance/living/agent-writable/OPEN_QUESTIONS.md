# OPEN_QUESTIONS.md — Personal OS

- **Q-PO-001** P-DEBT-03 orphan disposition: keep-and-wire vs delete for `fitness.py`
  (1.2k LOC, CSV contract), `reports.py` (1.25k), `runtime_bootstrap.py` (1.1k),
  `completion.py`. Per-module Chris call at the P-DEBT-03 gate.
- **Q-PO-002** Production DB path/backup design — needed before P-SCHED-02 (unattended
  writes need a real DB home + restore drill). Owner: P-SCHED-02 G0 plan.
- **Q-PO-003** Briefing content quality bar for MVP: is the deterministic template
  (P-BRIEF-01) good enough to ship the loop, with the model-composer as post-MVP upgrade?
  Chris judges on the P-BRIEF-01 soak artifacts.
- ~~**Q-PO-004** Harness B-00 timing~~ **CLOSED (D-PO-009, 2026-07-07): B-00 first**,
  then P-DESIGN-01 under the orchestrator-driven loop.
