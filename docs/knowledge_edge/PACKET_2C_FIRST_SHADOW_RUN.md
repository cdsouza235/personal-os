# Knowledge Edge — Packet 2C First Shadow Run Procedure

Status: proposed procedure, for execution post-merge under direct Conductor-session
supervision only. Owner: Builder (P-KE-2C) · Date: 2026-07-17
Zero network requests, zero credentials touched, zero sample/report content produced
in writing this document (hard constraint) — this is a plan to be executed later, by a
human-supervised session, not a script run by this packet. Mirrors
`PACKET_2A_PODCAST_SUPERVISED_SMOKE.md`/`PACKET_2B_YOUTUBE_SUPERVISED_SMOKE.md`'s
structure and STOP-rule discipline, applied to the `personalos knowledge-edge shadow
bootstrap|scan|sample-freeze|report` tooling this packet ships (all inert/unreachable
by the test suite; see each module's own docstring for why).

---

## 0. What this packet built, and what it deliberately did not run

P-KE-2C ships, inert until this procedure runs it:

- `shadow_mode.py` — the §14.4 `shadow_live` admission fence (shadow DB path only;
  notifications/Obsidian/scheduler refused structurally).
- `shadow_bootstrap.py` — idempotent shadow-DB migration + re-application of the nine
  Lane A verification flips from
  `audits/knowledge-edge/2026-07-16-packet-2a-podcast-smoke-transcript.md` (literal
  config, no re-fetching).
- `ground_truth_sample.py` — deterministic sample construction (`PHASE0_THESIS_MATCHING.md`
  Part 3) + freeze artifact rendering + the R3-04 acknowledgment gate.
- `shadow_report.py` — per-lane precision/recall/duplicate-leakage math + coverage
  reporting, reading a hand-graded, acknowledged sample.
- `personalos knowledge-edge shadow bootstrap|scan|sample-freeze|report` — the CLI
  surface wiring all of the above together.

This packet's own test suite exercises every one of these against fixtures and a
migrated-but-unverified (or verified-with-no-credential) registry — proving the wiring
is structurally reachable without ever making a live request. **Nothing in this
packet's build or tests touches a real network.** This document is what a Conductor
session runs, by hand, after merge, to produce the FIRST real shadow data.

---

## 1. Known scope limits going in (read before starting — these are not defects to fix mid-run)

- **Lane A (curated podcasts) is the only lane with a live-reachable adapter today.**
  The nine feeds `PACKET_2A_PODCAST_SUPERVISED_SMOKE.md`'s transcript already verified
  in the dev DB are what `shadow bootstrap` re-applies here.
- **Lane B/C (YouTube channel polling) has zero seeded channels.** Per
  `rails/knowledge_edge/youtube.py`'s own module docstring, the `youtube_channel`
  source registry ships empty — no §10.3-approved channel has a Conductor-verified
  `channel_id` endpoint yet. This shadow run's Lane B/C precision/recall sample will
  therefore be **empty by construction**, not a bug — it is the §10.3 gap this
  procedure's sample-freeze step names explicitly (§4 below).
- **Person-search (`search.list`) is still blocked at the source-not-found gate.**
  `PACKET_2B_YOUTUBE_SUPERVISED_SMOKE.md` §0 already found that no packet has seeded
  `ke-source-youtube-person-search` (seeding a reference row is not a schema gap, so
  P-KE-2B/2C's own "no migrations unless a genuine schema gap exists" constraint
  correctly refused to add it). §2 below is therefore a specification only, run to
  confirm the expected refusal, not a live call, until a future packet's own migration
  + acknowledgment seeds that row.
- **Lane D (earnings/EDGAR) has no live adapter yet at all** (Phase 3 territory). This
  shadow run's Lane D sample will show **zero events**, honestly, not a documented
  exception in the Phase 2 sense — Lane D coverage is simply out of this phase's scope.

Given the above, this run proves Lane A's precision/dedup mechanics end to end and
proves the §14.4 fence holds under a real invocation; it does **not** produce a
Lane B/C precision/recall measurement — that remains owed to a future packet once
§10.3 channels and/or the person-search source are seeded and verified. State this
plainly in whatever report this run produces; do not let the report's structure imply
completeness it does not have.

---

## 2. Execution constraints (non-negotiable)

- **Who runs this:** the Conductor session, directly and supervised, in real time.
  **Not any packet builder, and not scheduled** — no automation, no cron, no
  unattended run. `shadow_live` scheduled execution requires the Session 2
  shadow-scheduler gate, which has not happened; every command below is run by hand.
- **Database:** exactly `var/shadow/personalos-shadow.sqlite3`
  (`shadow_mode.SHADOW_DB_PATH`) for every command — the tooling refuses any other
  path, including the dev/test DBs and the production path, structurally (tested in
  `tests/test_knowledge_edge_shadow_mode.py`).
- **Credentials:** `PERSONALOS_RAIL_KE_PODCAST_USER_AGENT` must already be set in the
  canonical `~/.config/personal-os/ke.env` (per the 2A transcript — the same
  credential, no new one). No credential value is ever pasted into a transcript,
  sample, or report.
- **Scope:** live reads only (Lane A RSS); no notification, no Obsidian write, no
  scheduler activation, no production database — all four are structurally refused by
  `shadow_mode.py` and covered by dedicated tests.
- **Transcript:** append this run's command invocations, timestamps, and summarized
  outcomes (not full response bodies) to a new file under `audits/knowledge-edge/`,
  mirroring the 2A/2B transcripts' format.
- **STOP rule, no exceptions:** any command's non-zero exit halts that step; the next
  step is never started against a state the prior step did not confirm succeeded. A
  single source's live-fetch failure does not halt other sources' fetches within the
  same scan (the scan orchestrator already isolates per-source failures) but does halt
  this *procedure* from treating that source as monitored in the coverage report.

---

## 3. Step 1 — bootstrap the shadow database

```
personalos knowledge-edge shadow bootstrap --db var/shadow/personalos-shadow.sqlite3 --json
```

Expect `sources_flipped_to_active` to list all 9 Lane A source_ids on the first run
(or `already_bootstrapped` on a re-run — idempotent, safe to repeat). This applies
every pending migration and re-records the 9 verification flips from the 2A transcript
as literal config; it makes no live request.

**STOP if:** any of the 9 sources is not present after this step, or the command exits
non-zero — do not proceed to Step 2 against a registry this step did not confirm.

---

## 4. Step 2 — one bounded shadow scan

### 4a. Lane A live RSS (the live part of this run)

```
personalos knowledge-edge shadow scan --db var/shadow/personalos-shadow.sqlite3 \
  --date <today's date> --now <current UTC instant> --json
```

This constructs `LivePodcastFeedAdapter` in `shadow_live` mode and performs exactly one
GET per Lane A source with a due cursor (mirrors the 2A smoke's own "one GET per feed"
ceiling for a fresh cursor; a re-run only fetches items newer than the last successful
cursor). Record `sources_healthy`/`sources_failed` and any `error_summary` for a failed
source in the transcript. A feed's transient failure here does not retry within this
same invocation — re-run this exact command later if a feed needs a second attempt.

Because each RSS feed's own historical `<item>`/`<entry>` list already spans weeks to
months of prior episodes (not just "since last checked"), a single scan already yields
enough historical `published_at` spread to draw a 14-day sampling window from it
retroactively — this procedure does not require running the scan daily for two weeks.
Running it two or three times over a few days (to also catch anything newly published
during that span) is good practice but not a hard requirement.

### 4b. Person-search — specification only, expected to refuse (§1)

```
personalos knowledge-edge shadow scan ...  # does NOT include person-search — see below
```

`LiveYoutubePersonSearchClient.search_person` is not wired into `shadow scan` (matching
`youtube.py`'s own "neither class is wired into scan_orchestrator.py or
cli/knowledge_edge.py" note) and its one seed-able source row does not exist yet (§1).
If a future packet has since seeded `ke-source-youtube-person-search` and verified it,
this section becomes: call `search_person` once per Lane B/C roster person (≤29
subjects × ≤3 alias variants = ≤87 calls, well under the §5 174-call per-scan budget),
record `calls_made` from each `PersonSearchOutcome`, sum them, and pass that sum to
`shadow report --person-search-calls-made <sum>` in Step 6. Until then, this step is
skipped and the report is generated with `--person-search-calls-made` omitted (reported
as "not yet run this scan").

**STOP if:** Step 4a's exit code is non-zero for a reason other than expected
individual-source failures already isolated by the scan orchestrator (e.g. the shadow
admission fence itself refusing) — investigate before proceeding.

---

## 5. Step 3 — choose the sampling window, then freeze the sample (R3-04)

Choose `--window-start`/`--window-end` as a 14-consecutive-calendar-day span
(`PHASE0_THESIS_MATCHING.md` Part 3) that the Lane A data from Step 4a actually covers
(check the `published_at` spread of discovered items first — e.g. via `personalos
knowledge-edge queue show` or a direct read of `ke_media_items`). Since Lane D has no
live data this phase, `--lane-d-window-end` may be left at its default (equal to
`--window-end`) — there is nothing to extend it to yet.

```
personalos knowledge-edge shadow sample-freeze --db var/shadow/personalos-shadow.sqlite3 \
  --window-start <YYYY-MM-DD> --window-end <YYYY-MM-DD> \
  --sample-date <today's date> \
  --markdown-output-file docs/knowledge_edge/GROUND_TRUTH_SAMPLE_<date>.md \
  --json-output-file docs/knowledge_edge/GROUND_TRUTH_SAMPLE_<date>.json \
  --coverage-gap "No §10.3-approved YouTube channel seeded yet -- Lane B/C sample is empty this cycle." \
  --coverage-gap "Person-search source not yet seeded (see PACKET_2B_YOUTUBE_SUPERVISED_SMOKE.md §0) -- person-search coverage not measured this cycle." \
  --coverage-gap "Lane D (earnings/EDGAR) has no live adapter yet (Phase 3) -- zero events this cycle, not a documented exception in the Phase 2 sense." \
  --json
```

This writes both files but marks the sample `PENDING CONDUCTOR ACKNOWLEDGMENT (R3-04)`
— it never marks itself acknowledged.

---

## 6. STOP — Conductor + Codex sample acknowledgment (R3-04), before any grading

Per R3-04, the sample's **contents and construction procedure** (not just eventual
precision/recall numbers) must be Codex-reviewed and Chris-acknowledged **before any
threshold tuning — including grading — begins against it.** Concretely:

1. Send the frozen markdown doc (and, if useful, this procedure doc + the
   `ground_truth_sample.py` construction code) to Codex for review: does the sample
   look fairly drawn (not cherry-picked), does it match Part 3's strata/sizes, is the
   deterministic-hash selection method sound?
2. Chris reviews the sample's actual contents (titles, source_ids, the named coverage
   gaps) and either accepts it as representative or rejects it (in which case: fix
   whatever made it unrepresentative — e.g. widen the window — and re-run Step 3 with
   a fresh `--sample-date`, never edit a frozen file's *contents* in place).
3. On acceptance, Chris hand-edits the frozen markdown file's header:
   `status: "PENDING CONDUCTOR ACKNOWLEDGMENT (R3-04)"` → `status: "ACKNOWLEDGED"`,
   plus `acknowledged_by`/`acknowledged_at`, and commits that edit. **Do not edit the
   paired JSON file's contents at this step** — its checksum is fixed at freeze time
   and `shadow report` verifies it byte-for-byte (`require_acknowledged_sample`).

**STOP — do not proceed to grading (§7) or report generation (§8) until this
acknowledgment commit exists.**

---

## 7. Grading — hand-editing the acknowledged sample (real review work, no shortcuts)

Once acknowledged, grade each item by editing the **frozen JSON file** (not the
markdown — the JSON is the machine-read source of truth for §8):

- Each `lane_a_precision_check`/`lane_b_precision_check`/`lane_c_precision_check` item:
  add `"verdict"`, one of `"confirmed"`, `"rejected"`, `"duplicate_leak"` (see
  `shadow_report.py`'s module docstring for exact semantics of each).
- Each `lane_b_recall_check`/`lane_c_recall_check` item: this array starts **empty** —
  Part 3's recall check requires the reviewer to *independently* identify known
  appearances during the window (e.g. by checking 2-3 known sources by hand), not just
  grade what the system already surfaced. Add one object per independently-found
  appearance: `{"description": "...", "found_by_system": true|false}` —
  `found_by_system: true` only if that exact appearance also shows up in the
  corresponding `*_precision_check` list; `false` if the system missed it entirely.
  `lane_b_recall_check_minimum`/`lane_c_recall_check_minimum` in the sample record the
  required minimum count (15 / 10) — falling short is a real, reportable gap, not
  something to pad artificially.
- An item left ungraded (no `"verdict"`/`"found_by_system"` key) is fine — `shadow
  report` excludes it from every metric and reports it honestly as `ungraded`.

No LLM assistance, no automation for this step — this is exactly the "operate without
... an LLM" appearance-quality judgment `PHASE0_THESIS_MATCHING.md` reserves for a
human.

---

## 8. Step 4 — generate the shadow report

```
personalos knowledge-edge shadow report --db var/shadow/personalos-shadow.sqlite3 \
  --sample-markdown-file docs/knowledge_edge/GROUND_TRUTH_SAMPLE_<date>.md \
  --sample-json-file docs/knowledge_edge/GROUND_TRUTH_SAMPLE_<date>.json \
  --report-date <today's date> \
  --person-search-calls-made <sum from §4b, or omit> \
  --output-file docs/knowledge_edge/SHADOW_REPORT_<date>.md \
  --json
```

This refuses (`SampleAcknowledgmentError` → `CliError`, exit 1) unless the sample's
header says `ACKNOWLEDGED` and its checksum still matches the frozen JSON file
byte-for-byte. Commit the resulting `SHADOW_REPORT_<date>.md` alongside the sample
files. This report measures against Phase 0's *provisional* thresholds only — it does
not itself ratify anything; final thresholds remain a Session 2 decision.

---

## 9. Combined STOP conditions

- Step 1 (bootstrap) exit ≠ 0, or fewer than 9 sources present after it → halt, do not
  proceed.
- Step 2 (scan) exit ≠ 0 for a reason other than an individually-isolated source
  failure → halt, investigate the shadow admission fence / credential setup before
  retrying.
- Step 3 (sample-freeze) window does not actually satisfy the ≥14-day minimum (the
  tooling itself refuses this — `GroundTruthSampleError`) → halt, pick a valid window.
- §6's acknowledgment has not landed as a commit → halt; §7/§8 never proceed on an
  unacknowledged sample (the tooling also refuses this mechanically).
- §8 (report) exit ≠ 0 → halt; do not hand-edit the report output to force a result the
  tool refused to produce.

No step in this procedure is scheduled, retried automatically, or run unattended.
