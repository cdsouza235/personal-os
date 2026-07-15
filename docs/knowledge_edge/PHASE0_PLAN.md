# Knowledge Edge — Packet 0B: Phase/Packet/PR Plan and Validation Matrix

Status: proposed, for Session 1 approval. Owner: Builder (Packet 0B) · Date: 2026-07-15
Maps the amendment's 7 phases / ~20 packets (§19) onto concrete harness packets, gates,
and repo artifacts. Zero code, zero credentials, zero network requests in producing this
plan.

---

## 1. Packet-to-repo mapping

Packet IDs follow `P-KE-<phase-letter>` (matching the amendment's own lettering
exactly, e.g. amendment "Packet 2B" = `P-KE-2B`), appended to `governance/ROADMAP.md`'s
existing Phase A-E sequence as a new Phase F once a G-GOV packet lands it there (out of
this packet's scope — `governance/**` is forbidden here; flagged as a required follow-up
below). One PR per major phase (0, 1, 2, 3, 4, 5, 6), per the amendment's own "prefer one
coherent PR per major phase" instruction — packets are commits/sub-scopes within that PR,
not separate PRs, avoiding the micro-PR pattern the amendment explicitly warns against.

| Packet | Amendment ref | Repo artifacts | `allowed_paths` (sketch) | Codex | Fable | G-flags |
|---|---|---|---|---|---|---|
| P-KE-0A | Packet 0A | `docs/knowledge_edge/PHASE0_CURRENT_STATE.md` | `docs/knowledge_edge/**` | per-packet | — | G-GOV (docs) |
| **P-KE-0B** | Packet 0B | **this packet's five docs + PRD/ARCHITECTURE edits** | `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/knowledge_edge/**` | per-packet | — | **G-GOV** (PRD/ARCHITECTURE are manifest-listed) |
| P-KE-0C | Packet 0C | Synthetic golden fixtures under `tests/fixtures/knowledge_edge/` (or equivalent); no production tables, no scheduler, no Obsidian | `tests/**` (fixtures only), read-only credentialed probes | per-packet | — | **S1** (uses Session 1 credentials); G3-adjacent (first credentialed use) |
| P-KE-1A | Packet 1A | `src/personalos/knowledge_edge/state/**`, `migrations/00017-00021*.sql` | `src/personalos/knowledge_edge/**`, `migrations/**`, `tests/**` | per-packet | — | high-stakes (`migrations/**`) |
| P-KE-1B | Packet 1B | `src/personalos/knowledge_edge/engine/**`, fixture adapter contracts | `src/personalos/knowledge_edge/**`, `tests/**` | per-packet | — | routine (no network) |
| P-KE-1C | Packet 1C | `src/personalos/knowledge_edge/dashboard.py`, `src/personalos/cli/knowledge_edge.py` | `src/personalos/knowledge_edge/**`, `src/personalos/cli/**`, `src/personalos/dashboard.py`, `tests/**` | per-packet | **Phase 1 end** | routine |
| P-KE-2A | Packet 2A | `src/personalos/rails/knowledge_edge/podcasts.py` | `src/personalos/rails/knowledge_edge/**`, `tests/**` | per-packet | — | **G5** (`rails/**` reachability) + high-stakes |
| P-KE-2B | Packet 2B | `src/personalos/rails/knowledge_edge/youtube.py` (+ `person_search.py` stub, deferred per `PHASE0_PROVIDERS_AND_ACCESS.md` §3) | same | per-packet | — | **G5** + high-stakes |
| P-KE-2C | Packet 2C | Frozen ground-truth sample construction + shadow-report | `docs/knowledge_edge/**` (sample record), `tests/**` | per-packet, **+ human-acknowledgment of the sample itself (R3-04)** | **Phase 2 end** | **G5** (first live shadow run) |
| P-KE-3A | Packet 3A | `src/personalos/rails/knowledge_edge/earnings_calendar.py`, company registry | `src/personalos/knowledge_edge/**`, `src/personalos/rails/knowledge_edge/**`, `migrations/**` | per-packet | — | **G5** + high-stakes (migrations) |
| P-KE-3B | Packet 3B | `src/personalos/rails/knowledge_edge/sec_edgar.py`, IR/webcast resolution | `src/personalos/rails/knowledge_edge/**`, `tests/**` | per-packet | — | **G5** |
| P-KE-3C | Packet 3C | Event decision workflow, notification-intent-to-fake-sink | `src/personalos/knowledge_edge/**`, `tests/**` | per-packet | **Phase 3 end** | routine |
| P-KE-4A | Packet 4A | LaunchAgent staging (`docs/com.personalos.knowledgeedge.plist`, authored-only), due-work dispatcher | `docs/**` (plist), `src/personalos/knowledge_edge/**` | per-packet | — | high-stakes (scheduler-shaped) |
| P-KE-4B | Packet 4B | Notification delivery, staging-context validation | `src/personalos/knowledge_edge/**`, `tests/**` | per-packet | — | high-stakes |
| P-KE-4C | Packet 4C | Recovery, kill switch, operator runbook | `src/personalos/knowledge_edge/**`, `docs/**` (runbook) | per-packet | **Phase 4 end** | high-stakes |
| P-KE-5A | Packet 5A | Synthesis handoff, versioned ChatGPT instruction template | `src/personalos/knowledge_edge/**`, `docs/knowledge_edge/**` (template) | per-packet | — | routine |
| P-KE-5B | Packet 5B | Staging-vault Obsidian integration (no real vault) | `src/personalos/knowledge_edge/**`, `tests/**` | per-packet | — | high-stakes (Obsidian boundary) |
| P-KE-5C | Packet 5C | Monthly yield/roster review reports | `src/personalos/knowledge_edge/**`, `tests/**` | per-packet | **Phase 5 end** | routine |
| P-KE-6A | Packet 6A | 7-day soak under shadow scheduler (post-Session 2) | none (operational packet) | per-packet | — | **S2** |
| P-KE-6B | Packet 6B | Reconciliation, defect remediation, roster/threshold freeze | `src/personalos/knowledge_edge/**` (fixes only) | per-packet | — | routine-to-high-stakes per fix |
| P-KE-6C | Packet 6C | Final readiness package, go-live checklist | `docs/knowledge_edge/**` (readiness doc) | per-packet | **Phase 6 final + Session 3** | **S3** |

---

## 2. Phase acceptance criteria (repo-mapped restatement)

Each phase's acceptance criteria are already fully itemized in the amendment (§19); this
table adds the concrete repo-side proof for each, so a future auditor can check a command
output rather than re-read prose:

| Phase | Amendment acceptance (summary) | Concrete repo proof |
|---|---|---|
| 0 | PRD contains amendment; Session 1 held; Packet 0C fixtures exist | `docs/PRD.md` §7 present (this packet); `tests/fixtures/knowledge_edge/**` populated (P-KE-0C) |
| 1 | Fixture E2E four-lane queue; idempotent; caps enforced | `tests/test_knowledge_edge_*.py` green; declared test-count delta matched exactly (per `governance/QUALITY_GATES.md` convention) |
| 2 | 9/9 podcasts monitored or documented exception; ground-truth precision/recall/leakage reported by lane | P-KE-2C shadow report committed under `docs/knowledge_edge/**`; frozen sample referenced by path + checksum |
| 3 | Every Tier A company verified; T-1→T-0→replay lifecycle proven in shadow | P-KE-3C shadow-mode E2E test log |
| 4 | Scheduler package passes fixture+staging tests; no scheduler installed yet | P-KE-4A/4B/4C test suite green; LaunchAgent plist authored-only (mirrors `com.personalos.morning.plist`'s own current staged-not-loaded state) |
| 5 | Watched item reaches synthesis loop without re-entering metadata; staging vault only | P-KE-5A/5B E2E test; no real Obsidian path referenced anywhere in code (grep-proof, mirrors `PHASE0_CURRENT_STATE.md` §7's own verification method) |
| 6 | 7 healthy soak days; 100% announced Tier A T-1 coverage; thresholds met; no critical/high defect | P-KE-6A soak log + P-KE-6B reconciliation report + P-KE-6C readiness package |

---

## 3. Session-to-gate mapping (closes `PHASE0_CURRENT_STATE.md`'s flagged gap)

0A found that the amendment's Session 1/2/3 batching has no existing counterpart in
`governance/HUMAN_GATES.md`'s G0-G-RECOVERY table. This table makes the mapping explicit,
so the orchestrator's mechanical RISK_REGISTER path-triggers keep functioning underneath
the new session vocabulary rather than being silently bypassed by it.

| Session | Pre-authorizes (existing gate) | New concept, no exact existing gate | Packets it gates |
|---|---|---|---|
| **Session 1** | G3 (Secrets — FMP/YouTube credential creation); G5-reachability (network capability becoming reachable in `rails/knowledge_edge/**`, not yet "live" until actually exercised); the G-GOV review this very packet's PRD/ARCHITECTURE diff requires (Session 1 is the vehicle for that Conductor review, per amendment §0's "Session 1... closes Packets 0A-0B") | The "external-access bundle as one pre-authorized batch" concept itself — HUMAN_GATES.md has no "approve N future G3/G5 triggers in one sitting" mechanism today | P-KE-0C onward through P-KE-3B (first live network execution) |
| **Session 2** | G4+G5 (scheduler/background activation — HUMAN_GATES.md's activation-ladder concept already anticipates "soaking" as a state, which is a close analog to shadow-configuration activation) | Threshold-finalization-as-a-gate has no existing G-number (closest existing shape is G6 Design, but G6 is for irreversible design decisions, not empirical-threshold ratification) | P-KE-4A (shadow load) through P-KE-6A (soak) |
| **Session 3** | G4 (production DB path activation — HUMAN_GATES.md's G4 row already names this exact trigger); G5 (production rail-shaped activation + kill procedure) | Local-notifications-in-production has no line in G5's trigger enumeration today (G5's row currently lists "write Todoist / send Gmail / write Calendar / call a model API" — macOS local notifications are not on that list) | P-KE-6B/6C, go-live |

**Required follow-up this packet cannot execute (out of scope — `governance/**` is not in
this packet's `allowed_paths`):** a small, explicit G-GOV edit to `governance/
HUMAN_GATES.md` adding (a) a "Batched session" subsection cross-referencing this table,
and (b) widening G5's trigger enumeration to include "enabling macOS notifications in the
production user context." This should land as its own tiny G-GOV packet before or
alongside Session 1 — flagged here and in `PHASE0_ARCHITECTURE_DECISIONS.md` AD-7 so it
is not lost.

---

## 4. Migration, rollout, and rollback approach (summary; full detail in
## `PHASE0_ARCHITECTURE_DECISIONS.md` AD-4/AD-5)

- **Migration:** five additive-only migrations (`00017`-`00021`), applied through the
  existing unmodified `src/personalos/db/migrations.py` runner, continuing the existing
  numbering sequence from `00016_live_write_ledger_states.sql`.
- **Rollout sequencing:** dev/test (Packet 1A onward, every packet) → shadow database
  (Packet 2A onward, Session-1-authorized) → production database (Session 3 only, same
  additive migrations applied fresh, no data copied from shadow).
- **Rollback:** dev/test/shadow — delete the SQLite file, re-apply migrations from empty
  (zero cost, no dependents). Production — migrations are additive-only, so schema
  rollback carries no data-loss risk; feature disablement uses the feature-mode ladder
  (`disabled`/`fixture`) plus the Packet 4C kill switch, not a schema rollback; disaster
  recovery reuses D-PO-011's existing Online Backup API restore-drill procedure (one
  production file, one recovery mechanism, no Knowledge-Edge-specific backup needed).

---

## 5. Launch-blocking linkage

Per D-PO-016 item 1: **personal-os rail activation (the existing Todoist/Gmail/Calendar
MVP loop) does not go live independently of Knowledge Edge.** Concretely: even though the
existing MVP loop (`governance/ROADMAP.md` Phase D: P-RAIL-TD-02, P-RAIL-GM-02,
P-SCHED-02) is already built and merged (per `DECISIONS.md`/`OPEN_QUESTIONS.md`, confirmed
current as of `PHASE0_CURRENT_STATE.md` §3), Chris has explicitly chosen not to flip any
rail live yet (Q-PO-007), and will not, until Knowledge Edge's own Phase 6 activation gate
(Session 3) also clears. This is a Chris-level product-sequencing decision, not a
technical dependency between the two systems' code — the routine/briefing loop and
Knowledge Edge do not share write paths or gate each other's tests. `docs/PRD.md` §2 now
states this explicitly (this packet's edit) so it is not lost as tribal knowledge.

---

## 6. Validation matrix (test-file mapping)

New test files, one family per `knowledge_edge/` submodule (mirrors the existing
`tests/test_<module>.py` flat-directory convention — no new subdirectory):

| Test file | Covers |
|---|---|
| `tests/test_knowledge_edge_registries.py` | §20.1 schema validation, alias matching, effective-dated role/ticker resolution |
| `tests/test_knowledge_edge_engine_canonicalize.py` | §20.1 URL/GUID canonicalization |
| `tests/test_knowledge_edge_engine_directness.py` | §20.1 direct-vs-commentary classification |
| `tests/test_knowledge_edge_engine_dedup.py` | §20.1 stale-repost suppression, audio/video/replay grouping |
| `tests/test_knowledge_edge_engine_ranking.py` | §20.1 deterministic ranking/explanations |
| `tests/test_knowledge_edge_engine_matching.py` | `PHASE0_THESIS_MATCHING.md` Part 2 grammar rules |
| `tests/test_knowledge_edge_events.py` | §20.1 event schedule confidence, decision transitions, caps/expiry |
| `tests/test_knowledge_edge_scan.py` | §20.2 idempotent scan, overlap-window catch-up, cursor commit semantics |
| `tests/test_knowledge_edge_rails_podcasts.py` | Fake-client contract tests for `rails/knowledge_edge/podcasts.py` |
| `tests/test_knowledge_edge_rails_youtube.py` | Fake-client contract + quota-budget-shape tests |
| `tests/test_knowledge_edge_rails_earnings_calendar.py` | Fake-client contract tests for FMP adapter |
| `tests/test_knowledge_edge_rails_sec_edgar.py` | Fake-client contract tests |
| `tests/test_knowledge_edge_scheduler.py` | §20.2 due-work dispatcher: missed-run, DST, time-zone change, logged-out/post-reboot |
| `tests/test_knowledge_edge_notifications.py` | §20.2 notification dedup per material-change class |
| `tests/test_knowledge_edge_synthesis.py` | §20.3 Watched→synthesis-handoff E2E |
| `tests/test_knowledge_edge_dashboard.py` | UI surface acceptance (§14.2) |
| `tests/test_knowledge_edge_cli.py` | CLI surface parity with dashboard |

**Standing rule (mirrors `audits/test-strategy.md`'s existing convention):** each
packet's expected tests are named in its own plan before building; this table is the
floor, not the ceiling. **Required follow-up this packet cannot execute:** append a
"Phase F — Knowledge Edge" section to `audits/test-strategy.md` mirroring its existing
Phase A-E sections (a `governance/**`-adjacent manifest-listed file, out of this packet's
`allowed_paths`) — flagged here for the packet that lands Phase F, not invented as a fait
accompli now.

---

## 7. Required major-phase final report format (adopted, per amendment §24)

Every future Knowledge Edge packet's final report must include: scope completed;
packets/subphases completed; files changed; migrations/configuration added; validation
commands and results; exact test counts; coverage/precision findings when applicable;
safety assertions (§20.4's 12-item list); deviations from the PRD; unresolved risks;
next human decision required; branch; commit; PR URL; a human-review excerpt (what
changed, what files changed, what safety boundaries remain true, what approving/merging
would and would not mean, what Chris should double-check); and Codex/Fable audit status
with reconciliation notes. No new template is invented — this restates the amendment's
own §24 requirement so every future packet's Builder has it in one place.

---

## 8. Branch/PR strategy

One PR per major phase (0 through 6), per the amendment's own instruction to avoid
micro-PRs. Packet-level commits within each phase's branch, each individually
Codex-audited per the standing harness convention (`PHASE0_CURRENT_STATE.md` §3), with
the Fable phase-end audit gating the phase's PR merge. Branch naming follows the existing
repo convention (`packet/<id>`, per `governance/ROADMAP.md`'s own header) —
`packet/P-KE-0B` for this packet, `packet/P-KE-1` (covering 1A-1C) for Phase 1, and so on.
