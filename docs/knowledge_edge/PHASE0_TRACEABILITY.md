# Knowledge Edge — Packet 0B: Requirements Traceability Matrix

Status: proposed, for Session 1 approval. Owner: Builder (Packet 0B) · Date: 2026-07-15
Maps every requirement section of `docs/knowledge_edge/PRD_AMENDMENT_KNOWLEDGE_EDGE.md`
to the packet that delivers it and the validation that proves it, per amendment §19
Packet 0B. Packet IDs follow `P-KE-<phase-letter>` (e.g. `P-KE-2B`), matching the
amendment's own Phase/Packet lettering exactly — see `PHASE0_PLAN.md` for the full
packet-to-repo-artifact mapping this table references. "Disposition" is one of:
**delivered** (a named packet implements and tests it), **deferred** (post-launch
candidate, with the amendment's own §22 or explicit text supporting the deferral), or
**descoped-with-support** (narrowed at launch, with the amendment's own revision-log
disposition supporting the narrowing — always cited).

---

## 1-6. Front matter (executive summary, problem, thesis, goals, non-goals, principles)

| Section | Requirement | Packet(s) | Validation | Disposition |
|---|---|---|---|---|
| §1 Executive summary | Four-lane Daily Intelligence Queue, 4:30pm scan / 6:15am refresh / manual scan-now, launch-blocking | P-KE-1C (queue UX), P-KE-4A (schedule), all phases (launch-blocking gate) | Phase 6 activation acceptance (§21) | delivered |
| §2 Problem statement | Drift failure mode named as the thing the product must prevent | Informs P-KE-1C queue-cap design (§12) | Queue-cap/expiry tests (20.1) | delivered (design input, not a standalone test) |
| §3 Product thesis | Discover→Triage→Consume→Interpret→Synthesize→Store→Review; system owns Discover+Triage only | P-KE-1C, P-KE-5A (handoff boundary) | E2E test "Watched → synthesis handoff" (§20.3) | delivered |
| §4.1 User goals | Evening finite menu, decision controls, coverage honesty, etc. | P-KE-1C, P-KE-2C (coverage report) | §20.3 E2E four-lane queue test | delivered |
| §4.2 System goals | Reliable schedule, local-first, bounded registries, idempotent cursors, no live-LLM requirement | P-KE-1A (registries), P-KE-1B (cursors/idempotency), P-KE-4A (schedule) | §20.2 idempotent-scan / cursor-commit tests | delivered |
| §4.3 Launch outcome | Autonomous queue build + triage + earnings lifecycle at go-live | Phase 6 acceptance (all packets feed this) | Phase 6 pre-activation + activation acceptance (§19 Phase 6, §21) | delivered |
| §5 Non-goals/prohibited behavior | No trades, no auto-thesis-change, no media download, no exhaustive monitoring, etc. | Enforced as negative acceptance criteria across every phase; explicit boundary in `docs/PRD.md` §7.2 | Safety assertions every major-phase report (§20.4) | delivered (as standing constraint, not a feature) |
| §6 Product principles (1-12) | Queue not feed; human judgment authoritative; primary before commentary; etc. | Cross-cutting; principle 3 (primary before commentary) → P-KE-3B link hierarchy; principle 7 (bound backlog) → P-KE-1C caps; principle 10 (coverage honesty) → P-KE-2C/§10.5 | Distributed across §20.1/20.2 unit/integration tests per principle | delivered |

## 7. User experience and daily operating model

| Section | Requirement | Packet(s) | Validation | Disposition |
|---|---|---|---|---|
| §7.1 Primary daily schedule | 4:30pm scan, 6:15am refresh, T-60/T-15 checks, scan-now | P-KE-4A (due-work dispatcher) | §20.2 due-work dispatcher tests (missed-run, DST, time-zone) | delivered |
| §7.2 Evening queue layout | 6 named sections incl. earnings-separate-from-media-cap | P-KE-1C | §20.3 full four-lane queue test | delivered |
| §7.3 Standard media decisions | Watch/Save/Skip/Watched | P-KE-1C | §20.1 valid/invalid decision-transition tests | delivered |
| §7.4 Earnings/event decisions | Watch live/Save replay/Skip/Watched | P-KE-1A (event transition tables), P-KE-3C | §20.1 transition tests; §20.3 T-1 earnings E2E | delivered |
| §7.5 Minimum viable triage | Card information density requirements | P-KE-1C | Manual UI check + P-KE-1C acceptance | delivered |
| §7.6 Knowledge handoff | Copy synthesis packet / Obsidian draft / no-impact / promote-to-session-note | P-KE-5A | §20.3 Watched→synthesis-handoff E2E | delivered |

## 8. Lane requirements

| Section | Requirement | Packet(s) | Validation | Disposition |
|---|---|---|---|---|
| §8.1 Lane A — Curated Podcasts | 9-feed launch roster + adapter requirements (stable IDs, grouping, corrected-episode handling, cadence expectation) | P-KE-1A (schema/seed), P-KE-2A (live adapter) | Phase 2 acceptance: "all nine core podcasts monitored or documented exception" | delivered |
| §8.2 Lane B — Market Voices | 8-person roster; alias/spelling variants; affiliation as effective-dated attribute, not hardcoded label | P-KE-1A (schema), P-KE-2B (live search) | Phase 2 acceptance: ground-truth precision/recall by lane | delivered |
| §8.3 Lane C — Consequential Leaders + P0 rule | Named individuals + role-based watches; role model preserves history; deterministic "substantive" rule (5-min default) | P-KE-1A (role/occupancy schema, seeded from Session 1 launch role appendix), P-KE-2B | Phase 2 acceptance; §20.1 direct-vs-commentary classification tests | delivered |
| §8.4 Lane D — Earnings & Corporate Events | Event types, 3-track lifecycle, T-minus workflow, link hierarchy, primary materials, schedule confidence, material-change taxonomy | P-KE-1A (transition tables), P-KE-3A/3B/3C | Phase 3 acceptance (T-1→T-0→replay lifecycle in shadow mode) | delivered |

## 9. Priority company universe

| Section | Requirement | Packet(s) | Validation | Disposition |
|---|---|---|---|---|
| §9.1 Tier A (20 companies) | Must-surface-T-1 cap | P-KE-3A (verify identifiers/IR roots) | Phase 3 acceptance: "every Tier A company has verified identifiers" | delivered |
| §9.2 Tier B (conditionally surfaced) | Tracked, conditionally surfaced | P-KE-3A | Phase 3 acceptance | delivered |
| §9.3 Required company fields | 15 fields incl. CIK, aliases, IR URLs | P-KE-1A (schema), P-KE-3A (live verification — "must verify current tickers/identifiers... not assumed static") | Schema validation tests (§20.1) | delivered |
| §9.4 Roster governance | Caps, no auto-promote/demote, monthly review | P-KE-5C (monthly yield/roster review) | Phase 5 acceptance: "no automatic policy mutation" | delivered |

## 10. Source strategy and precedence

| Section | Requirement | Packet(s) | Validation | Disposition |
|---|---|---|---|---|
| §10.1 Approved source classes | 8 adapter classes | P-KE-2A/2B/3A/3B (per-class adapters) | Per-adapter fixture + live-shadow tests | delivered |
| §10.2 Source precedence | 5-level precedence for schedule/identity/location claims | `knowledge_edge/engine/ranking.py` design (`PHASE0_ARCHITECTURE_DECISIONS.md` AD-1) | §20.1 deterministic ranking tests | delivered |
| §10.3 Launch video/network allowlist | CNBC/Bloomberg/Yahoo/official channels/gov channels | Session 1 approval (`PHASE0_PROVIDERS_AND_ACCESS.md` §6); P-KE-2B implements | Coverage report (§10.5) shows allowlist health | delivered |
| §10.4 Candidate technical sources + D-YT | Provider comparison; D-YT decision; quota budget; cache/TTL rules | **This packet** (`PHASE0_PROVIDERS_AND_ACCESS.md` §2-5) | Session 1 ratification; Packet 2B/3A implement against the ratified choice | delivered (decision), implementation delivered P-KE-2B/3A |
| §10.5 Coverage reporting | Per-adapter health string, "never imply completeness" | P-KE-2C, P-KE-4C (health dashboard) | §17.3 health-surface acceptance | delivered |

## 11. Discovery, normalization, matching, and deduplication

| Section | Requirement | Packet(s) | Validation | Disposition |
|---|---|---|---|---|
| §11.1 Scan cursor behavior | Per-adapter cursor, overlap window, catch-up, idempotent commit | P-KE-1B | §20.2 idempotent-scan + overlap-window-catch-up tests | delivered |
| §11.2 Canonicalization | URL/GUID/alias/timestamp normalization | `knowledge_edge/engine/canonicalize.py` (P-KE-1B) | §20.1 URL/GUID canonicalization tests | delivered |
| §11.3 Directness classification | 7-class deterministic classifier | `knowledge_edge/engine/directness.py` (P-KE-1B) | §20.1 direct-vs-commentary tests | delivered |
| §11.4 Deduplication | Suppress on deterministic evidence only; `suspected_duplicate` for weaker signals; no completeness claim | `knowledge_edge/engine/dedup.py` (P-KE-1B) | §20.1 stale-repost suppression; §18.1 duplicate-rate metric | delivered |
| §11.5 Ranking | Deterministic factors incl. active-thesis match; no opaque ML | `knowledge_edge/engine/ranking.py` (P-KE-1B); thesis match per `PHASE0_THESIS_MATCHING.md` | §20.1 deterministic ranking/explanation tests | delivered |

## 12. Queue and backlog policy

| Section | Requirement | Packet(s) | Validation | Disposition |
|---|---|---|---|---|
| §12.1 Evening media caps | Tonight cap 3 / 90min, Saved cap 12 / 14-day expiry, resurfacing ≤2, explicit-Watch-only, candidate caps with overflow section | P-KE-1C | §20.1 Tonight/Saved caps + expiry/pin tests | delivered |
| §12.2 Earnings caps | Confirmed-only T-1 visibility, ≤2-recommended Watch-live/day, 7-day replay expiry | P-KE-1A (schema), P-KE-3C | §20.1 event caps/expiry tests | delivered |
| §12.3 Empty state | Coverage-qualified wording, never asserts absence | P-KE-1C, P-KE-2C | Manual/UI acceptance | delivered |

## 13. Data model

| Section | Requirement | Packet(s) | Validation | Disposition |
|---|---|---|---|---|
| §13.1 Required entities (22) | Full entity list | P-KE-1A (`PHASE0_ARCHITECTURE_DECISIONS.md` AD-1 module layout + migrations 00017-00021) | Migration application + FK tests | delivered |
| §13.2 Media item fields | Full field list incl. queue-visibility state (R3-03) | P-KE-1A schema | Schema validation tests | delivered |
| §13.3 Scheduled event fields | Full field list incl. nullable fiscal period, time-precision indicator, queue-visibility state (R3-03) | P-KE-1A schema | Schema validation tests | delivered |
| §13.4 Audit history | Append-only, excludes refreshable provider metadata | P-KE-1A schema + P-KE-2A/2B cache-lifecycle tests | §20.2 cache expiry/refresh/deletion tests | delivered |

## 14. Personal OS integration

| Section | Requirement | Packet(s) | Validation | Disposition |
|---|---|---|---|---|
| §14.1 Architectural rule | Extend existing primitives; no standalone app unless proven unsafe | `PHASE0_ARCHITECTURE_DECISIONS.md` AD-1/AD-2 (module placement decision) | This packet's own design review | delivered |
| §14.2 Required surfaces | Dashboard, 7-day view, saved queue, watched history, registries, source health, scan-now, kill switch, synthesis handoff, yield report, mode indicator | P-KE-1C (most surfaces), P-KE-4C (health/kill switch), P-KE-5C (yield report) | Per-surface UI acceptance across Phases 1/4/5 | delivered |
| §14.3 Configuration | Rosters/thresholds human-readable, schema-validated, version-controlled | P-KE-1A | Schema validation tests | delivered |
| §14.4 Feature modes | `disabled/fixture/shadow_live/active_read_only/active_with_obsidian_handoff`, scheduler activation orthogonal | Mapped onto the existing `RAIL_STATES`-shaped ladder (`PHASE0_CURRENT_STATE.md` reuse-opportunities note); implemented P-KE-1A/4A | Mode-change logging tests | delivered |

## 15. Mac mini scheduling and notifications

| Section | Requirement | Packet(s) | Validation | Disposition |
|---|---|---|---|---|
| §15.1 Scheduler | Due-work dispatcher contract, bounded 1-15min interval, America/Chicago deadlines, declared operating conditions | P-KE-4A; scheduler-reconciliation ADR in `PHASE0_ARCHITECTURE_DECISIONS.md` AD-6 (second LaunchAgent, ARCHITECTURE.md invariant #5 reworded) | §20.2 due-work dispatcher test list (missed-run, DST, time-zone change, logged-out, post-reboot) | delivered |
| §15.2 Notifications | Queue-ready, watched-event reminder, material-change notice, failure-threshold notice, no storm | P-KE-4B | §20.2 notification-deduplication-per-material-change-class tests | delivered |

## 16. Security, privacy, licensing, operational boundaries

| Section | Requirement | Packet(s) | Validation | Disposition |
|---|---|---|---|---|
| §16.1 Credentials | Read-only APIs, existing secrets convention, no secrets in repo/logs, redact headers | Session 1 bundle (`PHASE0_PROVIDERS_AND_ACCESS.md` §6); P-KE-2A/2B/3A adapters | §20.1 no-secret-logging tests | delivered |
| §16.2 Network controls | Allowlist incl. vendor-domain list, documented APIs, rate/robots/SEC compliance, timeouts/retries/circuit breakers, isolated failure | P-KE-2A/2B/3A/3B | §20.2 quota/rate-limit degradation, partial-source-failure tests | delivered |
| §16.3 Content storage | Metadata/links/notes only; no full video/audio/unlicensed transcript | Enforced by adapter design (no download code path exists) | Safety assertions (§20.4) every phase | delivered |
| §16.4 Financial boundary | No buy/sell instructions, no brokerage, no unlabeled materiality claims | `docs/PRD.md` §7.2 boundary; enforced across all packets | Safety assertions (§20.4) | delivered |

## 17. Reliability and failure handling

| Section | Requirement | Packet(s) | Validation | Disposition |
|---|---|---|---|---|
| §17.1 Required failure cases (19 cases) | Powered-off, quota exhaustion, credential revoked, malformed feed, DB locked/corrupted, etc. | Distributed: P-KE-1B (cursor/catch-up), P-KE-2A-3B (per-adapter failure), P-KE-4C (recovery/kill switch) | §20.2 full failure-case test list (R2-24 mapped all 19 cases to explicit tests) | delivered |
| §17.2 Degraded behavior | Partial queue, preserve decisions, never erase on empty response, never advance failed cursor | P-KE-1B, P-KE-4C | §20.2 partial-source-failure tests | delivered |
| §17.3 Health surface | Last-scan status, per-adapter success, rate-limit state, next-run, redacted errors | P-KE-4C | Phase 4 acceptance | delivered |

## 18. Metrics and controlled improvement

| Section | Requirement | Packet(s) | Validation | Disposition |
|---|---|---|---|---|
| §18.1 Product reliability metrics | Scan completion %, queue-ready-by-4:45pm, source-health rate, duplicate rate, precision/recall, link-acquisition metrics (3 separate), schedule-change detection, MTTR | P-KE-2C (measurement), P-KE-6B (reconciliation) | Phase 6 pre-activation acceptance thresholds | delivered |
| §18.2 Habit/usefulness metrics | Decision completion rate, triage time, W/S/S distribution, conversion rates, yield | P-KE-5C | Phase 5 acceptance | delivered |
| §18.3 Recommendations | Deterministic roster/threshold suggestions; never auto-applied; ≤1 major change/monthly review | P-KE-5C | Phase 5 acceptance: "no automatic policy mutation" | delivered |

## 19. Major phases and packets

Restated in full, with concrete repo mapping, in `PHASE0_PLAN.md` — not duplicated here to
avoid two documents drifting out of sync. Every packet named in the amendment's §19
(0A/0B/0C, 1A/1B/1C, 2A/2B/2C, 3A/3B/3C, 4A/4B/4C, 5A/5B/5C, 6A/6B/6C) appears in
`PHASE0_PLAN.md`'s packet table with allowed_paths, acceptance criteria, and audit
requirements. **Disposition: delivered (planning artifact complete this packet; execution
begins Packet 0C post-Session-1).**

## 20. Test and validation requirements

| Section | Requirement | Packet(s) | Validation | Disposition |
|---|---|---|---|---|
| §20.1 Unit tests (16 areas) | Schema validation through no-secret-logging | Distributed across P-KE-1A/1B/1C | New `tests/test_knowledge_edge_*.py` files, one family per `knowledge_edge/` submodule | delivered |
| §20.2 Integration tests (22 areas) | Idempotent scan through cache lifecycle | Distributed across P-KE-1B/2A-2C/3A-3C/4A-4C | Integration test suite additions, network-free (fake clients) per `governance/QUALITY_GATES.md`'s standing network rule | delivered |
| §20.3 E2E tests (8 areas) | Full four-lane queue through uninstall/rollback | P-KE-1C, P-KE-2C, P-KE-3C, P-KE-4C, P-KE-5A | Fixture-based E2E suite | delivered |
| §20.4 Safety assertions | 12-item per-phase safety statement | Every major-phase final report (P-KE-0 through P-KE-6) | Report template in `PHASE0_PLAN.md` | delivered |

## 21. Launch definition of done

All 16 items map 1:1 onto Phase 6 acceptance criteria already itemized in the amendment's
own §19 Phase 6 section and restated in `PHASE0_PLAN.md`'s Phase 6 table. **Disposition:
delivered (tracked as the final gate, not a separate deliverable).**

## 22. Post-launch candidates (explicitly excluded from launch gate)

| Item | Disposition | Support |
|---|---|---|
| Transcript-assisted claim extraction | deferred | amendment §22, explicit |
| Automated pre-call question packets | deferred | amendment §22, explicit |
| Live-model semantic relevance classification | deferred | amendment §22 + §5 non-goal ("no live model for discovery/ranking at launch") |
| Broader podcast-person indexing | deferred | amendment §22; coverage-impact of the §3 broad-search deferral (`PHASE0_PROVIDERS_AND_ACCESS.md` §3) is the concrete near-term instance of this |
| More TV networks / international sources | deferred | amendment §22 |
| Product-launch / regulatory-hearing event types | deferred | amendment §22 + §8.4 "not required for launch unless already covered by Consequential Leaders" |
| Google Calendar / Todoist integration | deferred | amendment §22 + §5 non-goal |
| Mobile companion interface | deferred | amendment §22 |
| Adaptive ranking | deferred | amendment §22 + §11.5 "must not use opaque ML personalization" |
| Automatic source/roster recommendations beyond deterministic reports | deferred | amendment §22 + §18.3 "no recommendation is applied automatically" |
| Contributor forecast extraction/calibration automation | deferred | amendment §22 |
| Automatic monthly thesis-review drafts | deferred | amendment §22 + §7.6 "canonical interpretation remains manual" |

None of these are silently dropped — every row cites the amendment's own text
authorizing the deferral, per this packet's own disposition rule.

## 23. Open decisions for Phase 0 planning

All 11 items answered by this packet's documents:

| # | Question | Answered in |
|---|---|---|
| 1 | Which module owns queue UI/data? | `PHASE0_ARCHITECTURE_DECISIONS.md` AD-1 |
| 2 | Does the harness provide safe scheduled-job semantics already? | `PHASE0_CURRENT_STATE.md` §4 (no — confirmed absent/mismatched); AD-6 (reconciliation) |
| 3 | Which secrets mechanism is already used? | `PHASE0_CURRENT_STATE.md` §6 (`PERSONALOS_RAIL_*` env-var convention); `PHASE0_PROVIDERS_AND_ACCESS.md` §6 (KE naming) |
| 4 | Which earnings-calendar provider? | Originally decided by D-PO-016 (FMP); **FMP rejected at real price, replaced by a bounded market-cap-ranked company roster sourced via SEC EDGAR + official IR pages (D-PO-019)** — evaluation record `PHASE0_PROVIDERS_AND_ACCESS.md` §2, roster definition `PHASE0_ROSTER.md` |
| 5 | Initial official channel/network allowlist? | `PHASE0_PROVIDERS_AND_ACCESS.md` §6 (restates amendment §10.3; Session 1 ratifies) |
| 6 | Achievable precision/recall thresholds? | `PHASE0_THESIS_MATCHING.md` Part 3 (provisional; Session 2 finalizes) |
| 7 | Obsidian staging/final path boundary? | Confirmed absent (`PHASE0_CURRENT_STATE.md` §7); new work, Packet 5A/5B |
| 8 | Local notification mechanism already present? | Confirmed absent (`PHASE0_CURRENT_STATE.md` §5); new work, Packet 4B |
| 9 | One module or bounded separate packages? | `PHASE0_ARCHITECTURE_DECISIONS.md` AD-1/AD-2 (one top-level package + adapters inside `rails/**`) |
| 10 | Pre-launch soak environment/dataset? | `PHASE0_PLAN.md` Phase 6 table; `PHASE0_THESIS_MATCHING.md` Part 3 (ground-truth procedure) |
| 11 | D-YT option selection + storage/TTL implications? | `PHASE0_PROVIDERS_AND_ACCESS.md` §4 |

## 24. Required major-phase final report format

Adopted as-is; the report template is restated in `PHASE0_PLAN.md`'s "Reporting" section
so every future packet's Builder has one place to copy it from. **Disposition: delivered
(process requirement, not a product requirement).**

## 25. External reference notes

Informational only (planning inputs); no traceability row needed — each reference is
already cited inline at its relevant section above (§10.4, §15.1, §16.2).

## 26. Revision change log — R2/R3 reconciliation cross-reference

Every finding in the amendment's own Revision 1.1/1.2/1.3 change logs already resulted in
a specific section edit (the amendment states which section each ref modified). This
table confirms each ref's resulting requirement is captured above, by pointing at the
section row that carries it — no new content, a cross-reference only, per this packet's
own "every R2-xx row must appear" instruction.

| Ref | Amendment section(s) it modified | Captured in this table at |
|---|---|---|
| A1 | §0, §14.4, §15.1, §19 Phases 4/6 | §15.1, §19 (this doc); AD-6 |
| A2 | §7.1, §8.4 | §7.1, §8.4 |
| A3 | §0, §19, §24 | §19, §24 |
| B1 | §10.4, §25 | §10.4 |
| B2 | §8.4 | §8.4 |
| B3 | §8.3 | §8.3 |
| B4 | §21 | §21 |
| B5 | §10.3 | §10.3 |
| B6 | §19 (Packet 5A) | §7.6, §19 |
| B7 | §10.4, §23 | §10.4, §23 item 11 |
| R2-01 | §0, §19 | §19 (Phase 0 closes after 0C) |
| R2-02 | §0, §20.4 | §20.4 |
| R2-03 | §0, §19 0B | `PHASE0_ARCHITECTURE_DECISIONS.md` AD-4 |
| R2-04 | §0, §8.3, §19 | `PHASE0_THESIS_MATCHING.md` Part 3 |
| R2-05 | §21 | §21 |
| R2-06 | §8.4, §19 1A | §8.4, §13 |
| R2-07 | §12.1 | §12.1 |
| R2-08 | §7.1, §8.4, §12.2, §13.3 | §7.1, §8.4, §12.2, §13.3 |
| R2-09 | §8.4, §20 | §8.4 |
| R2-10 | §0, §8.3, §19 | §8.3 (launch role appendix), `PHASE0_PROVIDERS_AND_ACCESS.md` §3/§6 |
| R2-11 | §18, §19 | §18.1, `PHASE0_THESIS_MATCHING.md` Part 3 |
| R2-12 | §12.3 | §12.3 |
| R2-13 | §11.4 | §11.4 |
| R2-14 | §10.4 | `PHASE0_PROVIDERS_AND_ACCESS.md` §4 |
| R2-15 | §10.4, §13.4, §19 0C, §20.2 | §10.4, §13.4, §20.2 |
| R2-16 | §10.4, §19 0B | `PHASE0_PROVIDERS_AND_ACCESS.md` §5 |
| R2-17 | §0, §10.4 | `PHASE0_PROVIDERS_AND_ACCESS.md` §2 |
| R2-18 | §15.1, §19 4A, §20.2 | §15.1, `PHASE0_ARCHITECTURE_DECISIONS.md` AD-6 |
| R2-19 | §0, §19 | §19 Phase 3C/4B in `PHASE0_PLAN.md` |
| R2-20 | §0, §8.4, §16.2 | §8.4, §16.2, `PHASE0_PROVIDERS_AND_ACCESS.md` §6 |
| R2-21 | §11.5, §19 0B | `PHASE0_THESIS_MATCHING.md` Part 1-2 |
| R2-22 | §18.1, §19 Phase 6 | §18.1 |
| R2-23 | §19 6A | `PHASE0_PLAN.md` Phase 6 table |
| R2-24 | §17.1, §20.2 | §17.1 |
| R3-01 | §10.4 | `PHASE0_PROVIDERS_AND_ACCESS.md` §4 (option 3 rejected) |
| R3-02 | §0, §19 | `PHASE0_PLAN.md` gate-mapping section |
| R3-03 | §13.2, §13.3 | §13.2, §13.3 |
| R3-04 | §19 2C | `PHASE0_THESIS_MATCHING.md` Part 3 (freeze procedure) |
| R3-05 | §15.1 | §15.1, AD-6 |

**Coverage check:** every amendment section (1 through 26, including all lettered
subsections) has a row above; every R2-xx/R3-0x ref has a cross-reference row. No
requirement in the amendment is unaccounted for.
