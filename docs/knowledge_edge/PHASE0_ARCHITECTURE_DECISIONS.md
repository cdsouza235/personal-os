# Knowledge Edge — Packet 0B: Architecture Decision Record

Status: proposed, for Session 1 ratification alongside the rest of the Phase 0 plan.
Owner: Builder (Packet 0B) · Date: 2026-07-15
Scope: module boundaries and ownership, exact database paths (amendment §19 Packet 0B
item 3), and the migration/rollout/rollback approach (item 7). Zero code, zero
credentials, zero network requests, zero scheduler/Obsidian work — this is a design
record only; Packet 1A implements against it.

This document assumes the current-state findings in `PHASE0_CURRENT_STATE.md` (Packet
0A) without re-deriving them, and makes the decisions 0A identified as open.

---

## AD-1. Module layout: a new top-level package, not a `state/` subpackage

0A's §8 named two candidates: `src/personalos/state/knowledge_edge/` or a sibling
top-level package. **Decision: sibling top-level package**, because Knowledge Edge's own
components do not fit the `state/` package's contract. `docs/ARCHITECTURE.md`'s layering
rule is explicit: `state.py` "knows nothing of rails or briefings." Knowledge Edge's scan
orchestrator *must* know about `rails/knowledge_edge/**` (it calls the adapters) and about
its own engine and state — that is a briefing-generator-shaped component, not a
state-shaped one. Folding it into `state/` would either violate the layering rule or
force an awkward split where half of Knowledge Edge lives in `state/` and half doesn't,
for no benefit. A sibling package keeps the existing `state/` package's contract
(network-blind) intact and gives Knowledge Edge the same three-layer shape the rest of
Personal OS already has (state → engine → orchestrator/rails), at its own scope.

### Layout

```
src/personalos/knowledge_edge/            # new top-level package
    __init__.py
    state/                                # persistence only; network-blind; mirrors
        __init__.py                       # src/personalos/state/'s own domain-submodule
        registries.py                     # source, source_endpoint, person, role,
                                           #   role_occupancy, affiliation, company,
                                           #   company_identifier, topic
        media.py                          # media_item, discovery_occurrence,
                                           #   entity_match, canonical_group
        events.py                         # scheduled_event + the three transition
                                           #   tables (status / decision / queue
                                           #   visibility) for both media and events
        decisions.py                      # user_decision, decision_history,
                                           #   queue_snapshot
        scan.py                           # scan_run, scan_cursor, source_health,
                                           #   coverage_report
        roster.py                         # roster_change_proposal
        synthesis.py                      # synthesis_handoff
    engine/                                # pure functions, no I/O, no clock reads
        __init__.py                       # (mirrors ARCHITECTURE.md invariant #2)
        canonicalize.py                   # §11.2 canonicalization
        directness.py                     # §11.3 directness classification
        dedup.py                          # §11.4 deduplication / canonical grouping
        ranking.py                        # §11.5 deterministic ranking
        matching.py                       # thesis/topic matching grammar — see
                                           #   PHASE0_THESIS_MATCHING.md
    scan_orchestrator.py                  # composes engine/ + state/ +
                                           #   rails/knowledge_edge/*, analogous to
                                           #   cli/today.py's role for the morning cycle
    dashboard.py                          # KE dashboard data providers; wired as new
                                           #   routes into the existing
                                           #   src/personalos/dashboard.py shell (not a
                                           #   standalone app — amendment §14.1)

src/personalos/rails/knowledge_edge/      # new subpackage INSIDE the existing rails/**
    __init__.py                           #   glob — see AD-2
    podcasts.py                           # Lane A: RSS/Atom
    youtube.py                            # Lane B/C: Data API (person search only,
                                           #   per D-YT option 1) + channel RSS/
                                           #   upload-playlist polling
    earnings_calendar.py                  # Lane D: roster/EDGAR/official-IR earnings
                                           #   coverage (D-PO-019; FMP rejected, see
                                           #   PHASE0_ROSTER.md)
    sec_edgar.py                          # Lane D: SEC EDGAR public APIs
    person_search.py                      # Lane B/C: broad person-search provider —
                                           #   see PHASE0_PROVIDERS_AND_ACCESS.md
                                           #   (currently: deferred, module stubs only)

src/personalos/cli/knowledge_edge.py      # CLI surface, mirrors cli/routines.py /
                                           #   cli/priorities.py conventions

migrations/00017_knowledge_edge_registries.sql
migrations/00018_knowledge_edge_media_events.sql
migrations/00019_knowledge_edge_decisions_queue.sql
migrations/00020_knowledge_edge_scan_health.sql
migrations/00021_knowledge_edge_roster_synthesis.sql
```

Five migrations rather than one, split along the same lines as `state/`'s own submodules
(AD-3), so each is small, independently reviewable, and matches its owning `state/`
submodule one-to-one.

## AD-2. Network adapters live inside the existing `rails/**` glob — no manifest edit

`GOVERNANCE_MANIFEST.yaml`'s `protected_paths` and `RISK_REGISTER.md`'s network-primitive
tripwire both already exempt `src/personalos/rails/**` from the "any module importing
`urllib`/`socket`/etc. that isn't on the manifest's network-capable list is a new-rail
G5 trigger" rule. Placing Knowledge Edge's adapters at `src/personalos/rails/
knowledge_edge/**` reuses that existing glob exactly — **no edit to
`GOVERNANCE_MANIFEST.yaml` or `RISK_REGISTER.md` is required to grant network
capability**, because the pattern `src/personalos/rails/**` already matches any depth of
subpackage. This is a direct application of 0A's own reuse-opportunities note (the rails
four-gate pattern) at the placement level, even though the *gating* itself differs (AD-4).

This does NOT avoid every future manifest touch: Phase 2/3 packets will still trip the
existing `src/personalos/rails/**` → G5 + high-stakes RISK_REGISTER row (as intended —
first live network execution is meant to be high-stakes), and `docs/ARCHITECTURE.md`'s
invariant #5 rewording (this packet) and any later HUMAN_GATES.md Session-mapping
addendum (PHASE0_PLAN.md, open item) are their own, separate G-GOV edits.

## AD-3. Read-only adapters do not need the full four-gate write pattern

`docs/ARCHITECTURE.md` invariant #3 (permission → ledger/dedupe → rail-state →
credentials, fail-closed) exists to gate *writes to Chris's real accounts*
(Todoist/Gmail/Calendar) where a mistaken call has irreversible external consequences.
Knowledge Edge's adapters are read-only discovery pulls with no effect on any external
account. Applying the full four-gate pattern to them would gate nothing real (there is no
Todoist-style "permission to write" or "ledger of Chris-visible side effects" for a GET
request) and would invite a builder to invent a hollow permission check purely for
shape-matching. **Decision:** Knowledge Edge adapters keep only the parts of the pattern
that are real for a read path:
- **rail-state gate** — reuse the existing `inert|soaking|live`-shaped ladder (mapped onto
  the amendment's own `disabled → fixture → shadow_live → active_read_only →
  active_with_obsidian_handoff` feature-mode ladder, per 0A's reuse-opportunities note);
- **credentials-present, fail-closed gate** — identical in shape to the rails/ convention:
  presence-checked via `os.environ`, never logged, structured refusal object on any
  unsatisfied gate, exactly like `rails/todoist.py`'s existing pattern;
- no permission-evaluator or ledger/dedupe leg, because there is no Chris-facing account
  write to permission-gate or ledger-dedupe here. (Deduplication of *content* — §11.4 — is
  an engine concern, not the idempotency-ledger's write-dedupe concern, and stays in
  `knowledge_edge/engine/dedup.py`.)

Any future Knowledge Edge write path that *does* touch something externally visible
(production notifications, real Obsidian writes) must use the full four-gate pattern
unmodified — those are exactly the Session 3-gated actions, and they are write-shaped in
the way the existing invariant #3 was designed for.

## AD-4. Database paths

Per the amendment's own Session-1 stop-gate list: *"the Phase 0 plan must name the exact
development, shadow, and production database paths or schemas; Session 1 authorizes only
the isolated shadow path."* Named exactly, grounded in `src/personalos/config.py` and
`path_safety.py`:

| Environment | Path | Status |
|---|---|---|
| Development | `config.DEV_DB_PATH` = `var/dev/personalos-dev.sqlite3` (existing, unchanged) | Knowledge Edge tables land here via the same additive migrations every other dev iteration uses — no new dev path. |
| Test | `config.TEST_DB_PATH` = `var/test/personalos-test.sqlite3` (existing, unchanged) | Same reasoning; the existing test suite's DB. |
| **Shadow (new)** | `config.SHADOW_DB_PATH` = `var/shadow/personalos-shadow.sqlite3` (proposed; Packet 1A adds the constant) | **Session 1 authorizes this path only** for `shadow_live`-mode runs (live discovery + persistence, no production notification, no Obsidian write — amendment §14.4). |
| Production | `config.PRODUCTION_DB_PATH` = `/Users/coldstake/PersonalOS/personal_os.db` (existing, D-PO-011-approved, unchanged) | Knowledge Edge adds its own tables to this SAME single production file via the same additive migrations — **there is no second production database.** Session 3 authorizes writes here. |

### Why the shadow path is safe under the existing path-safety layer, stated explicitly

`path_safety.validate_existing_sqlite_path` (the function every DB-path-accepting CLI
surface calls) admits `var/shadow/personalos-shadow.sqlite3` through the **same branch
that already admits `DEV_DB_PATH` and `TEST_DB_PATH` today**: the `is_under_repo(resolved)`
check (`path_safety.py:131`), which tests the path against `REPO_ROOT` as a whole, not
against `var/dev` or `var/test` specifically. Concretely, for the proposed shadow path:

- `reject_protected_path` (`path_safety.py:64`) — does not match `~/PersonalOS`,
  `~/.openclaw`, or `LaunchAgents`; passes.
- `reject_sensitive_path` (`path_safety.py:86`) — `"shadow"` is not in
  `SENSITIVE_PATH_MARKERS` or `DEMO_OUTPUT_DIR_CREDENTIAL_MARKERS`; passes.
- `reject_production_path` (`path_safety.py:95`) — `PRODUCTION_MARKERS =
  {"prod", "production", "live"}` does not match any path component or stem token of
  `var/shadow/personalos-shadow`; passes. **This is the one rule a future rename must
  respect: the shadow path (and any of its parent directories) must never contain the
  literal tokens `prod`, `production`, or `live`, or this same rule will legitimately
  reject it** — exactly the behavior that currently protects `DEV_DB_PATH`/`TEST_DB_PATH`
  from accidentally drifting toward a production-looking name.
- suffix check — `.sqlite3` is in `DATABASE_SUFFIXES`; passes.
- final admission test (`path_safety.py:131`) —
  `is_approved_production_path or is_under_repo(resolved) or is_under_temp(resolved)`:
  `is_approved_production_path` is `False` (it is not `config.PRODUCTION_DB_PATH`), but
  `is_under_repo(resolved)` is `True` because `var/shadow/...` resolves under
  `REPO_ROOT`. **This is the same branch, unmodified, that already admits the dev and
  test paths** — zero new logic in `path_safety.py` is needed.

**What stays fenced, explicitly:** the shadow path is never treated as production. It
never receives the `allow_production_path=True` exemption (`path_safety.py:106-124`) —
that exemption is keyed on an exact match against `config.PRODUCTION_DB_PATH`, and the
shadow path is a different value entirely, so it always goes through the ordinary
`reject_protected_path`/`reject_sensitive_path`/`reject_production_path` checks like any
other repo-local file, with no special-casing. `config.py`'s `_ensure_production_runtime_path`
(the strict-equality guard used only for `Environment.PRODUCTION`) is never invoked for
shadow; shadow instead reuses `_ensure_repo_local_runtime_path` (the same relative-to-
`RUNTIME_DIR` check dev/test already use), because `var/shadow/` sits under
`RUNTIME_DIR` (`var/`) exactly like `var/dev/` and `var/test/` do. Packet 1A's concrete
implementation task: add `SHADOW_DB_PATH = RUNTIME_DIR / "shadow" /
"personalos-shadow.sqlite3"` next to `DEV_DB_PATH`/`TEST_DB_PATH` in `config.py`, and
either a fourth `Environment.SHADOW` enum member routed through
`_ensure_repo_local_runtime_path` in `_database_path_for`, or a Knowledge-Edge-specific
loader that calls `_ensure_repo_local_runtime_path` directly — Packet 1A's own call,
not decided here, since it is an implementation-code choice, not an architecture one.

### Production rollout: no bulk data copy from shadow

At Session 3, production KE tables start **empty** — the same additive migrations that
ran against the shadow database run against the one production file, but no shadow data
is copied over. Shadow's entire purpose is pre-production validation and the Phase 6 soak
(amendment §19 Packet 6A); its data is disposable. Production begins accumulating its own
scan history from the first live production scan onward. This avoids a bulk-migration
step the amendment never asked for and that would itself be a new, unreviewed risk
surface (stale shadow data landing in the one real production database).

## AD-5. Migration and rollback approach

All five Knowledge Edge migrations (`00017`–`00021`, AD-1) are purely additive `CREATE
TABLE` statements — no `ALTER TABLE` on any existing table, no `DROP`, following the same
non-destructive-by-convention pattern the existing 16 migrations already use (e.g.
`00015_routine_first_class_cadence_columns.sql`'s additive `ALTER TABLE ... ADD COLUMN`).
They run through the existing, unmodified `src/personalos/db/migrations.py` runner
(`apply_migrations`, checksum-tracked in `schema_migrations`) — no new migration
mechanism, no second runner.

**Rollback, by target:**
- **Dev/test:** delete the SQLite file and re-run `apply_migrations`; zero-cost, exactly
  today's existing dev/test workflow.
- **Shadow:** identical — the shadow database holds no data anyone depends on outside the
  soak itself; if a soak needs to restart, delete `var/shadow/personalos-shadow.sqlite3`
  and re-run migrations from empty. This is also the Packet 6A "an incorrectly handled
  outage restarts the seven-cycle count" reset mechanism at the database level, not just
  the cycle-count level.
- **Production:** because the migrations are additive-only, applying them carries no data
  loss risk to the existing (non-Knowledge-Edge) production tables — there is nothing to
  "roll back" at the schema level in the destructive sense `governance/HUMAN_GATES.md`'s
  G4 gate is worried about. If a Knowledge Edge production defect requires disabling the
  feature, the rollback mechanism is the feature-mode ladder (drop to `disabled` or
  `fixture`, amendment §14.4) plus the scheduler kill switch (Packet 4C), not a schema
  rollback. Disaster-level recovery (corrupted production file) uses the same D-PO-011
  Online Backup API restore-drill procedure already approved for the rest of Personal
  OS — Knowledge Edge does not need its own backup mechanism because it shares the one
  production file.

## AD-6. Scheduler reconciliation (0A conflict #1) — decision

0A found the amendment's §15.1 due-work dispatcher (`RunAtLoad` + fixed 1–15 minute
interval) architecturally incompatible with the existing `com.personalos.morning.plist`'s
deliberately `RunAtLoad`-free, fixed-`StartCalendarInterval`-only design, and offered
three reconciliation options without picking one (0A's own scope). **Decision for this
packet: Option 1 — a second, independent LaunchAgent.**

Knowledge Edge gets its own LaunchAgent (proposed label: `com.personalos.knowledgeedge`)
implementing the due-work dispatcher contract (§15.1: `RunAtLoad` + fixed 1–15 minute
interval, default 5, consulting a local due-work table covering the 4:30pm scan, 6:15am
refresh, and T-60/T-15 checks), running alongside — never replacing — the existing
`com.personalos.morning` fixed-time agent. Each is independently `launchctl unload`-able
and independently unload-proof-verifiable per its own label, satisfying
`governance/RUNBOOK.md`'s acceptance criterion for each agent separately.

**Why Option 1 over Options 2/3:** Option 2 (multiple fixed `StartCalendarInterval`
entries plus a short-lived dynamically-loaded agent for T-60/T-15 windows) adds more
runtime complexity to reason about "unload-proof" for a dynamically loaded/unloaded
second agent than a single always-loaded dispatcher does, for no real benefit — the
amendment's own §15.1 already specifies the due-work dispatcher pattern as the
preferred design, not a fallback. Option 3 (redesigning down to fixed intervals only,
dropping T-60/T-15) would cut a named required behavor (§7.1, §8.4) that R2-18's own
disposition already rejected reopening — the amendment's revision history (R2-18) already
settled on the due-work dispatcher contract as the answer to this exact tension, so this
packet is applying that settled contract to the existing-repo scheduler, not re-litigating
it. This is why `docs/ARCHITECTURE.md` invariant #5 is reworded (this packet's edit) to
say "LaunchAgent(s)" rather than "the one P-SCHED LaunchAgent" — a real, explicit, called-
out deviation from the prior invariant wording, not a silent break.

**What this does NOT decide:** the LaunchAgent's exact plist content, install/load/unload
scripting, and the due-work table's schema are Packet 4A implementation work, gated at
Session 2 (shadow load) and Session 3 (production load) exactly as the amendment
specifies — this ADR only settles that two independently-managed agents are the target
shape, so Packet 4A has an unambiguous design to build against.

## AD-7. Open follow-up this packet does not resolve (out of scope, flagged for later)

- `governance/HUMAN_GATES.md` has no "Session 1/2/3" concept and no line item for "local
  notifications in the production user context" under its G5 row (which currently
  enumerates Todoist/Gmail/Calendar/model-API writes only) — both are real gaps 0A
  identified and this packet cannot close, because `governance/**` is outside this
  packet's `allowed_paths`. Tracked as an explicit required action in
  `docs/knowledge_edge/PHASE0_PLAN.md`'s gate-mapping section, to land as its own small
  G-GOV edit before or alongside Session 1.
- `audits/test-strategy.md` will need a "Phase F — Knowledge Edge" section (mirroring its
  existing Phase A–E sections) once Packet 1A lands; also a `governance/**`-adjacent file
  this packet cannot touch. Flagged in `PHASE0_PLAN.md`.
