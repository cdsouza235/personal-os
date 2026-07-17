# Knowledge Edge — Packet 2B YouTube Supervised Smoke Procedure

Status: proposed procedure, for execution post-merge under direct Conductor-session
supervision only. Owner: Builder (P-KE-2B) · Date: 2026-07-17
Zero network requests, zero credentials touched in producing this document (hard
constraint) — this is a plan to be executed later, by a human-supervised session, not
a script run by this packet. Mirrors
`docs/knowledge_edge/PACKET_2A_PODCAST_SUPERVISED_SMOKE.md`'s structure and STOP-rule
discipline, applied to `src/personalos/rails/knowledge_edge/youtube.py`'s two Lane
B/C mechanisms.

---

## 0. Prerequisite this document cannot itself satisfy — read before scheduling this smoke

Unlike the 2A podcast smoke (whose 9 feed endpoints migration 00023 already seeded),
**this packet seeds no rows for either YouTube mechanism.** Per P-KE-2B's own scope:

- The `youtube_channel` source registry is empty — no channel_id endpoint exists for
  §1's channel-polling procedure to run against.
- No `ke_sources` row exists for `youtube.py`'s
  `DEFAULT_PERSON_SEARCH_SOURCE_ID` (`ke-source-youtube-person-search`) either — no
  migration in this packet inserts one. Conductor scope amendment #2 (iteration 4)
  authorized additive migration 00025 for the provider-metadata cache tables that
  F1 required, so migrations are no longer categorically forbidden in this packet —
  but that authorization was scoped to the cache tables only, not to seeding
  reference/endpoint rows. YouTube channel and person-search reference rows remain
  deliberately unseeded pending a future Conductor-verified migration +
  acknowledgment, exactly like the podcast endpoints (00022/00023) went through.

**Section 2 (person-search) of this procedure therefore cannot run yet either.**
Before it can, a future packet must, via its own migration:
1. Insert a `ke_sources` row of `source_type='person_search_provider'` (id
   `ke-source-youtube-person-search`, matching
   `DEFAULT_PERSON_SEARCH_SOURCE_ID`), `status='trial'`.
2. Insert a matching `ke_source_endpoints` row (`endpoint_type='api_endpoint'`, `url`
   = `https://www.googleapis.com/youtube/v3/search`, `is_primary=1`,
   `status='active'`, `endpoint_verified_at`/`verified_by` both `NULL`) — exactly the
   "seed the URL, leave it unverified" shape migration 00023 used for the 9 podcast
   feeds.

Once that lands, §2 below is executable exactly as written. Until then, §2 is a
procedure specification only — do not attempt to run it; there is nothing seeded to
run it against, and `LiveYoutubePersonSearchClient._evaluate_gates` will refuse with
`STATUS_SEARCH_BLOCKED_SOURCE_NOT_FOUND` regardless of feature_mode or credential
presence.

**Section 1 (channel polling) is `n/a` until a future packet's Conductor-verified
migration seeds real `channel_id` endpoints and requests the specific acknowledgment
`PHASE0_PROVIDERS_AND_ACCESS.md` §6 requires** ("any addition later ... requires an
explicit Conductor acknowledgment of the specific added source before it is fetched
from"). This document's §1 is retained as the procedure specification that future
packet's own smoke will follow, not something to execute today.

---

## 1. Channel-upload RSS polling — procedure specification (n/a until channels seeded)

For each `channel_id` endpoint a future packet seeds:

```
GET https://www.youtube.com/feeds/videos.xml?channel_id=<channel_id>
User-Agent: PersonalOS-KnowledgeEdge-YoutubeChannelPoll/1.0
```

**Success criteria (all must hold), mirroring the 2A podcast smoke's own three:**

1. HTTP 200 response, no redirect to a different host than `www.youtube.com`.
2. Response body parses as well-formed Atom `<feed>` with at least one `<entry>`.
3. At least one entry carries a non-empty `yt:videoId` and `<title>`.

**Bound:** exactly one GET per channel; no retries within the same session — a feed
that fails its smoke is left exactly as seeded (`trial`, `endpoint_verified_at` still
`NULL`).

**Recording a PASS** (the only path from `trial` to `active`, via the state-layer
helpers this packet adds — `personalos.knowledge_edge.state.record_endpoint_verification`
and `personalos.knowledge_edge.state.update_source_status`):

1. `record_endpoint_verification(connection, source_id=<source_id>,
   endpoint_url=<channel_id>, verified_at=<UTC timestamp of the successful GET>,
   verified_by=<identifying session string, e.g. "conductor:YYYY-MM-DD">)` —
   `endpoint_url` here is the `channel_id` value itself, since that is what
   `ke_source_endpoints.url` holds for a `channel_id`-type endpoint (see
   `youtube.py`'s module docstring for why).
2. `update_source_status(connection, source_id=<source_id>, new_status="active")`.
3. Append a row to this packet's own smoke transcript
   (`audits/knowledge-edge/<date>-packet-2b-youtube-smoke-transcript.md`, mirroring
   the 2A transcript's format) recording the request, response status, and what
   parsed.

Until both steps 1 and 2 land for a given channel, `LiveYoutubeChannelAdapter`
continues to refuse every fetch attempt against it.

---

## 2. `search.list` person search — ONE call, plus the §5 quota screenshot

**Precondition:** §0's seeding step has landed (a `ke-source-youtube-person-search`
row exists, `status='active'`, endpoint verified via the same
`record_endpoint_verification`/`update_source_status` helpers as §1, following this
same document's own procedure applied once to that one source).

**Scope:** exactly ONE `search.list` call, against one roster person already seeded
by P-KE-1A (e.g. `ke-person-kevin-warsh`, "Kevin Warsh" — any single seeded
`ke_people` row is an equally valid choice; the point is *one* call, not a specific
person), `maxResults=5`:

```
GET https://www.googleapis.com/youtube/v3/search
    ?part=snippet&type=video&q=Kevin%20Warsh&maxResults=5&key=<PERSONALOS_RAIL_KE_YOUTUBE_API_KEY>
```

**Success criteria:**

1. HTTP 200 response, `application/json` content-type, no redirect to a different
   host than `www.googleapis.com`.
2. Response body parses as JSON with a top-level `items` array.
3. Each `items[]` entry carries a non-empty `id.videoId` and `snippet.title`.

**Required artifact — closes §5's TBC:** a Google Cloud Console screenshot (Quotas
page for the YouTube Data API v3, scoped to this project) taken in the same session,
showing (a) the actual per-call unit cost `search.list` charged for this one call and
(b) the project's current default daily quota. `PHASE0_PROVIDERS_AND_ACCESS.md` §5
marks both figures **TBC — reconfirm at Session 1** and the 348-call/day worst-case
budget's own headroom conclusion depends on them; this screenshot is what turns that
TBC into a confirmed number. Save it (or a description of it, if the image itself
carries account-identifying chrome that should not be committed) alongside this
procedure's own transcript.

**Recording a PASS:** identical two-step flip to §1 step 1-2, against the
person-search source_id and its `api_endpoint` endpoint's URL
(`https://www.googleapis.com/youtube/v3/search`).

**Bound:** exactly one call, no retries, no pagination (`youtube.py`'s
`search_person` never auto-paginates — see its module docstring). This is
deliberately the smallest possible live-fire test of the mechanism, not a
representative-load test; §5's steady-state 348-call/day worst case is a separate,
already-documented budget question this one call does not itself validate.

---

## 3. Combined STOP conditions

Each mechanism's smoke halts independently of the other on its own first failure;
one mechanism's outcome never blocks the other. No source is fetched from again
inside the same session after either a PASS (recorded, done) or a STOP (left exactly
as seeded, not retried). Any non-200 response, any redirect to a host other than the
request's own host, or any response that does not parse per §1/§2's own criteria
halts that source's smoke immediately.
