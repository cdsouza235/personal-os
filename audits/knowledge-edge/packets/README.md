# Per-packet harness audit records (D-PO-020 convention, adopted 2026-07-16)

One directory per harness-run packet: the FINAL-round Codex audit report (AUDIT.md)
and the last run-record digest (digest.json). Committed as Conductor records before
each phase closes. Retroactive caveat for P-KE-00B through P-KE-1D: the harness
overwrites AUDIT.md per round, so only each packet's final-round report survives;
intermediate-round findings are narrated in STATUS.md's phase entries and the
phase-end checkpoint report. From Phase 2 onward, round-by-round reports are copied
out at each iteration.
