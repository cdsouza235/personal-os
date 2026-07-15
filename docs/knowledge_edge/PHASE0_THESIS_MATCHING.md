# Knowledge Edge — Packet 0B: Active-Thesis Snapshot Source, Matching Grammar, and
# Ground-Truth Procedure

Status: proposed, for Session 1 approval. Owner: Builder (Packet 0B) · Date: 2026-07-15
Covers amendment §19 Packet 0B items: "Name the approved local source or versioned
snapshot for active thesis/topic links... and define the deterministic matching grammar"
(R2-21) and "Define the ground-truth procedure for appearance quality." Precise enough
for Packet 1A/2B to implement directly; zero code, zero vault access, zero LLM calls in
this packet or in the design itself.

---

## Part 1 — Active-thesis snapshot source

### The problem this solves

The real Obsidian vault is unavailable until Session 3 (amendment §19 Packet 5B), but the
ranking engine's "active thesis/topic match" factor (§11.5) is needed from Phase 2
onward, well before Session 3. Packet 0B must name what stands in for the vault during
Phases 1-5, and the matching logic must operate on it "without vault access or an LLM."

### Decision: a hand-authored, versioned local snapshot file, owned by Chris

A single YAML file, **`docs/knowledge_edge/thesis_snapshot/active_theses.yaml`**,
version-controlled in the repo (inside this packet's own `docs/knowledge_edge/**` scope,
so no path-safety or governance-manifest question arises — it is a plain repo file, not a
database or a vault path). Chris hand-maintains it directly (edits are a normal repo
commit, reviewed like any other content change) until Session 3, at which point the same
schema is regenerated from a real vault export instead of hand-authored — **the matching
grammar (Part 2) does not change when the source changes from hand-authored to
vault-derived; only how the file's rows get populated changes.** This mirrors the
amendment's own principle that automation proposes and the human maintains authority: the
thesis list itself is never inferred by Knowledge Edge, only consumed by it.

This packet does not commit a populated file — that is Chris's own content (his actual
theses), not something this packet should invent on his behalf. This packet specifies the
exact schema and a worked example below so Packet 1A can implement the loader against a
concrete, unambiguous shape, and so Chris has a template to populate before Phase 2 needs
real data.

### Schema (version 1)

```yaml
version: 1
updated: "2026-07-15"          # ISO date; the loader rejects a file with no updated field
theses:
  - topic_id: "ai-compute-buildout"     # stable slug; referenced by other config, never
                                        # renamed once in use — rename = new topic_id +
                                        # explicit migration note in this file's own log
    display_name: "AI Compute Buildout"
    status: active                      # active | dormant — only active topics score in
                                        # ranking (§11.5); dormant topics are kept for
                                        # history/display, never deleted
    tokens:
      companies: ["NVDA", "MSFT", "GOOGL", "AMZN", "META", "AVGO", "CRWV"]
      people: ["jensen-huang", "satya-nadella", "sundar-pichai"]
      keywords: ["data center", "gpu capex", "power demand", "capex guidance"]
    aliases:
      "NVDA": ["NVIDIA", "Nvidia Corp", "Nvidia Corporation"]
    negative_terms: ["gaming gpu", "consumer graphics card"]
    precedence: 10
  - topic_id: "stablecoin-rails"
    display_name: "Stablecoin Payment Rails"
    status: active
    tokens:
      companies: ["CRCL", "COIN"]
      people: []
      keywords: ["stablecoin", "payment rail", "on-chain settlement"]
    aliases: {}
    negative_terms: []
    precedence: 5
```

Field notes:
- `tokens.companies` and `tokens.people` hold **stable internal IDs** (ticker for
  companies per §9.3's `company_identifier`; a stable `person` slug per §13.1's `person`
  entity), never free-text names — matching against already-resolved entity links (from
  §11.3's directness/entity-match step), not a second independent text search over raw
  names. This is what keeps the grammar deterministic and avoids re-deriving entity
  resolution logic inside the matching grammar itself.
- `tokens.keywords` and `negative_terms` are free-text tokens/phrases matched against
  title + description text only (Part 2, rule 3).
- `aliases` maps a token (company ticker or person ID) to literal alternate strings; this
  reuses the same alias concept the amendment already requires for entity matching
  itself (§8.2's "spelling variants such as Mohamed/Mohammed El-Erian"), not a second,
  parallel alias system — Packet 1A should share one alias-resolution helper between
  entity matching and thesis matching wherever the same alias table applies.
- `precedence` is an integer; higher wins for "which single topic leads the why-surfaced
  explanation" when an item matches more than one active topic (Part 2, rule 5).

---

## Part 2 — Deterministic matching grammar

Inputs to one evaluation: a single `media_item` or `scheduled_event` record, already
carrying its resolved `company`/`person`/`role` entity links (from the upstream §11.3
directness-classification step) and its `title` + `description` text fields. Output: the
set of `topic_id`s this item matches, each tagged with its match strength, plus (if the
caller needs a single leading label) the winning `topic_id` by the precedence rule.

### Evaluation order (deterministic, no ambiguity, no ranking by "relevance score")

1. **Entity-company match (strength: `entity`).** For each `active` topic, if the item's
   resolved `company` entity (or any of that company's `company_identifier` aliases, per
   §9.3) appears in `topic.tokens.companies` (matching against `topic.aliases` entries
   too), record a HIT at strength `entity`.
2. **Entity-person match (strength: `entity`).** Same rule, against `topic.tokens.people`
   and the item's resolved `person` entity/entities.
3. **Keyword match (strength: `keyword`).** Normalize `title + " " + description` (see
   Normalization rule below). For each `active` topic, if any token in
   `topic.tokens.keywords` (or its `topic.aliases` entries) appears as a normalized
   whole-word-or-exact-phrase match in the normalized text, record a candidate HIT at
   strength `keyword`.
4. **Negative-term suppression.** For each topic with a candidate `keyword`-strength HIT
   from rule 3, if any token in that topic's `negative_terms` also appears (same
   normalized-match rule) in the item's normalized text, DISCARD that topic's
   `keyword`-strength HIT for this item. **Negative terms never suppress an
   `entity`-strength HIT** (rules 1-2) — a negative term only qualifies the weaker
   text-only signal, never an already-resolved entity link, because an entity link is a
   fact about the item (this company/person is really in it), not a fuzzy text guess.
5. **Leading-label tie-break.** An item may end with zero, one, or multiple surviving
   topic HITs (from rules 1-3 minus rule-4 discards) — all are retained and shown as tags
   and all feed the ranking factor in §11.5. If the UI needs one leading "why this
   surfaced" topic label, pick the surviving HIT with the highest `topic.precedence`;
   ties break by `topic_id` lexical ascending order. This tie-break is cosmetic
   (display ordering only) — it never discards a HIT, unlike rule 4.

### Normalization rule (shared by keyword and negative-term matching)

Lowercase the text; strip punctuation to single spaces; collapse repeated whitespace.
Match a keyword/negative-term token as either (a) a whole word within the normalized
text (`\btoken\b`-shaped, for single-word tokens) or (b) an exact contiguous phrase match
(for multi-word tokens, e.g. `"data center"` must appear as that exact three-token
sequence, not `"data"` and `"center"` separately elsewhere in the string). **No stemming,
no fuzzy/edit-distance matching, no embeddings, no synonym expansion beyond the explicit
`aliases` table, no LLM call of any kind** — this is the concrete implementation of the
"operate without vault access or an LLM" requirement.

### Worked example

Item: title `"NVIDIA Q3 Earnings: Jensen Huang on Data Center Demand"`, resolved company
entity = NVDA, resolved person entity = jensen-huang, no negative terms present.

- Rule 1: NVDA ∈ `ai-compute-buildout.tokens.companies` → HIT (`entity`).
- Rule 2: jensen-huang ∈ `ai-compute-buildout.tokens.people` → HIT (`entity`, same topic).
- Rule 3: normalized text contains `"data center"` → candidate HIT (`keyword`, same
  topic — already has an `entity` HIT, so this is redundant information, not a new topic
  match; a topic is either matched or not, strength is recorded per-rule for audit/
  explanation purposes, not summed into a score).
- Rule 4: no negative terms present → nothing discarded.
- Result: item matches `ai-compute-buildout` (multiple corroborating signals); does not
  match `stablecoin-rails` (no company/person/keyword overlap). Why-surfaced explanation
  can cite the `entity`-strength company+person match as the primary reason (strongest
  signal available), per §7.5's "concise deterministic 'Why this surfaced' explanation"
  requirement.

---

## Part 3 — Ground-truth procedure for appearance quality

Per amendment §19 Packet 0B: sample size, sampling window, strata by lane and source,
provisional empirical thresholds. This defines the *procedure* Packet 2C executes and
freezes (per R3-04, Codex-reviewed and human-acknowledged before any threshold tuning
begins) — Packet 0B does not draw the actual sample, because no live discovery data
exists yet in Phase 0.

### Strata (by lane and source-class, per the amendment's own four-lane structure)

| Stratum | Universe | Sampling approach |
|---|---|---|
| Lane A — Curated Podcasts | 9 launch feeds (§8.1) | Deterministic RSS matching; low classification ambiguity. Risk is duplicate/reissue handling, not appearance classification. |
| Lane B — Market Voices | 8 launch people (§8.2) | Highest classification risk (direct-appearance vs. mentioned-only vs. commentary-about). |
| Lane C — Consequential Leaders | Named individuals + role-based watches (§8.3) | Same risk profile as Lane B, plus role-occupancy correctness. |
| Lane D — Earnings & Corporate Events | 20 Tier A companies (§9.1) | Bounded, enumerable universe — every event in the window is checked, not a random sample (matches the Phase 6 acceptance criterion's "100% of officially announced Tier A events," not a sampled subset). |

### Sampling window

**Minimum 14 consecutive calendar days**, drawn during Packet 2C's `shadow_live` run —
long enough to span more than one release cycle for every core podcast (the
least-frequent core podcast releases at least weekly) and to very likely intersect at
least one earnings-adjacent period for cross-checking Lane D's interaction with Lane B/C
(a company's earnings often coincides with a burst of Market Voice commentary about it).
If the chosen 14-day window happens to contain zero Tier A earnings events, extend the
Lane D stratum's window (only) until at least one Tier A event has completed, so Lane D
is never evaluated on zero events.

### Minimum per-stratum sample sizes (provisional, Phase 0)

| Stratum | Minimum manually-reviewed sample | Basis |
|---|---|---|
| Lane A | 10 releases spot-checked for correct grouping/dedup | Low ambiguity; sample validates mechanics, not judgment calls. |
| Lane B | ≥30 surfaced candidate appearances manually confirmed/rejected (precision) **and** ≥15 independently-identified known appearances checked for whether the system found them (recall) | Precision and recall must be measured separately (R2-11) — precision alone, without a recall check, cannot be graded from surfaced results only; the recall check requires the reviewer to independently know of appearances during the window (e.g. from manually checking 2-3 known sources), not just grade what the system already surfaced. |
| Lane C | Same structure as Lane B, sized to the smaller launch roster: ≥20 surfaced candidates (precision), ≥10 independently-identified known appearances (recall) | Smaller named-individual roster than Lane B's per-person volume, but role-based watches add irregular-cadence risk. |
| Lane D | 100% of Tier A events scheduled within the window (not a sample) | Matches the Phase 6 acceptance criterion directly; a bounded, enumerable universe does not need sampling. |

### Provisional empirical thresholds (Phase 0 placeholders — distinct from the
### Session-1 TBC category)

These are **not** "verify against a live external source" TBCs (`PHASE0_PROVIDERS_AND_ACCESS.md`'s
category) — they are deliberately provisional per the amendment's own instruction ("Phase
0 sets only provisional empirical values plus fixed policy thresholds... final empirical
thresholds are approved at Session 2"). Packet 2C measures real numbers against these
starting points; Session 2 approves the final values, which may differ substantially:

| Metric | Provisional Phase 0 value | Finalized at |
|---|---|---|
| Person-appearance precision (Lane B/C) | 85% | Session 2, from Packet 2C's frozen-sample measurement |
| Person-appearance recall (Lane B/C) | 70% (metadata-only, no-transcript constraints bound this lower than precision by design) | Session 2 |
| Duplicate leakage (all lanes) | ≤10% of surfaced items are undetected duplicates | Session 2 |
| Substantive-segment duration threshold (§8.3 P0 rule) | 5 minutes (amendment's own stated default) | Session 2 |
| Material schedule-change threshold (§8.4) | 30 minutes (amendment's own stated default) | Session 2 |

### Freeze procedure (R3-04)

Packet 2C constructs the actual sample (real discovered items + the independently-
identified recall-check appearances) following the strata/sizes above, then the sample's
**contents and construction procedure** (not just the resulting precision/recall numbers)
are Codex-reviewed and Chris-acknowledged asynchronously *before* any threshold tuning
begins against it — preventing the sample itself from being cherry-picked or flawed in a
way that would make subsequent tuning look better than real-world performance.
