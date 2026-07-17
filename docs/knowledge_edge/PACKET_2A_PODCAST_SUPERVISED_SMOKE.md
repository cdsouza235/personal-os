# Knowledge Edge — Packet 2A Podcast Endpoint Supervised Smoke Procedure

Status: proposed procedure, for execution post-merge under direct Conductor-session
supervision only. Owner: Builder (P-KE-2A) · Date: 2026-07-16
Zero network requests, zero credentials touched in producing this document (hard
constraint) — this is a plan to be executed later, by a human-supervised session, not a
script run by this packet. Mirrors `PHASE0_PROBE_PLAN.md`'s structure and STOP-rule
discipline, narrowed to the 9 Lane A (curated podcasts) feed endpoints migration 00023
seeds.

---

## 1. Why this document exists

Migration `00023_knowledge_edge_lane_a_endpoints.sql` records the 9 launch-roster
podcast feed URLs against their `ke_sources` rows, resolved 2026-07-16 via the Apple
podcast directory. Per this packet's own hard constraint, seeding a URL is not the same
as verifying it: every `ke_sources` row stays `status='trial'` and every
`ke_source_endpoints.endpoint_verified_at`/`verified_by` stays `NULL` after that
migration runs. `src/personalos/rails/knowledge_edge/podcasts.py`'s own gating
(`LivePodcastFeedAdapter._evaluate_gates`) refuses to fetch from any source whose row is
not `active` or whose endpoint has no recorded verification, regardless of feature mode
— so nothing in this repo can reach any of these 9 URLs until this exact procedure runs
and a Conductor session records its result.

---

## 2. Execution constraints (non-negotiable)

- **Who runs this:** the Conductor session, directly and supervised, in real time. **Not
  any packet builder, and not scheduled** — no automation, no cron, no unattended run.
- **When:** post-merge of this packet only, and only after the explicit Conductor
  acknowledgment this packet's own handoff flags as still pending (per
  `PHASE0_PROVIDERS_AND_ACCESS.md`'s "any addition later ... requires an explicit
  Conductor acknowledgment of the specific added source before it is fetched from").
- **Scope:** read-only; shadow-scope (no production database, no production writes);
  one plain `GET` per feed, identified by a descriptive `User-Agent` string set via
  `PERSONALOS_RAIL_KE_PODCAST_USER_AGENT` in `.env.local` (never invented ad hoc,
  never a bare Python default — SEC's own fair-access norm that "identify yourself"
  applies here too, even though these are open podcast feeds with no stated policy
  requiring it).
- **Transcript:** results (request URL, response status, content-type, and a short
  summary of what parsed — not the full raw feed body) saved under
  `audits/knowledge-edge/` by the supervising session itself, not by this packet,
  mirroring `audits/knowledge-edge/2026-07-15-packet-0c-probe-transcript.md`.
- **STOP rule, no exceptions:** any non-200 response, any redirect to a host other than
  the feed URL's own host (the exact thing `podcasts.py`'s
  `_HostConfinedRedirectHandler` refuses to follow silently), or any response that does
  not parse as well-formed RSS/Atom **halts that feed's smoke immediately**. No
  retries. Each feed's smoke is independent — one feed's failure does not block
  attempting the next.

---

## 3. Per-feed procedure — exactly one GET per feed, 9 GETs total ceiling

For each of the 9 rows migration 00023 seeded (`ke-source-dwarkesh-podcast`,
`ke-source-latent-space`, `ke-source-no-priors`, `ke-source-unchained`,
`ke-source-bankless`, `ke-source-forward-guidance`, `ke-source-odd-lots`,
`ke-source-macro-voices`, `ke-source-compound-and-friends`):

```
GET <ke_source_endpoints.url for this source_id>
User-Agent: <PERSONALOS_RAIL_KE_PODCAST_USER_AGENT from .env.local>
```

**Success criteria (all must hold):**

1. HTTP 200 response, no redirect to a different host than the request URL's own host.
2. Response body parses as well-formed XML with a recognized RSS (`<rss><channel>`) or
   Atom (`<feed>`) root.
3. At least one `<item>`/`<entry>` is present and carries a non-empty stable identifier
   (`<guid>`/`<id>`) and title.

**Bound:** exactly one GET per feed; 9 GETs is the hard ceiling for this procedure, not
a target to reach. A feed that fails its smoke is left exactly as seeded (`trial`,
`endpoint_verified_at` still `NULL`) — it is not retried within the same session.

---

## 4. Recording a PASS — the only path from `trial` to `active`

A feed that meets all three success criteria is flipped from `trial` to `active`, one
feed at a time, only by the supervising Conductor session, via a direct, ordinary write
using the existing state-layer helpers (no new script, no bulk flip across all 9 at
once):

1. Update `ke_source_endpoints.endpoint_verified_at` to the UTC timestamp of the
   successful smoke GET, and `verified_by` to an identifying string for the session
   that ran it (e.g. `"conductor:2026-07-16"`), for that feed's endpoint row only.
2. Update the corresponding `ke_sources.status` from `trial` to `active` for that feed
   only.
3. Append a row to this packet's smoke transcript
   (`audits/knowledge-edge/<date>-packet-2a-podcast-smoke-transcript.md`, mirroring the
   0C transcript's format) recording the request, response status, and what parsed.

Until step 1 and step 2 both land for a given feed, `LivePodcastFeedAdapter` continues
to refuse every fetch attempt against it — seeding the URL (this packet) and running
the smoke (this procedure) are each necessary but neither is sufficient on its own.

---

## 5. Combined STOP conditions

Each feed's smoke halts independently of the others on its own first failure per §2's
STOP rule; a failure on one feed never blocks attempting the next. All 9 are one-shot,
supervised, read-only, and produce a saved transcript before the supervising session
ends. No feed is fetched from again inside the same session after either a PASS
(recorded, done) or a STOP (left exactly as seeded, not retried).
