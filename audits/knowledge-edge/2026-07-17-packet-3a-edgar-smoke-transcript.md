# Packet 3A EDGAR Earnings Supervised Smoke — Transcript

Executed 2026-07-17 (UTC) by the Conductor session per
docs/knowledge_edge/PACKET_3A_EARNINGS_SUPERVISED_SMOKE.md, post-merge of P-KE-3A
(daa80d5).

## Mechanism probe (one representative GET, per §3's bound)
GET data.sec.gov/submissions/CIK0000320193.json (Apple; approved UA) → HTTP 200,
valid JSON, entity "Apple Inc.", 1000 recent filings, latest Form 4 2026-06-17.
All success criteria met.

## Flip — sanctioned path
ke-source-sec-edgar-submissions: trial→active + endpoint verification recorded
(verified_by conductor:2026-07-17-edgar-smoke) via state.registries helpers in the
shadow DB (~/.personalos/shadow/). Per-company coverage validates through ordinary
scan runs and §10.5 coverage reporting from here, per the procedure's own scope.
Lane D now participates in the daily rehearsal scans.

— Conductor session (Fable seat)
