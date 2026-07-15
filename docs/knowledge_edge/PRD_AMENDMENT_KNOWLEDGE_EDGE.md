---
title: "Personal OS PRD Amendment — Knowledge Edge Daily Intelligence Queue"
document_type: prd_amendment
status: audited_approved_for_integration
revision: "1.3"
owner: Chris
last_updated: 2026-07-14
target_environment: Mac mini / Personal OS
launch_classification: launch_blocking
implementation_agent: existing Personal OS harness orchestrator session (Builder implements; Codex per-packet audit; Fable phase-end audit)
---

# Personal OS PRD Amendment: Knowledge Edge Daily Intelligence Queue

## 0. Harness orchestrator pickup directive

This document is a **normative amendment to the canonical Personal OS PRD**. It is not a separate product, a disposable prototype, or a post-launch idea list.

This amendment is executed inside the **existing Personal OS harness orchestrator session**. Do not create a new orchestrator, session, or parallel governance structure. Harness role conventions apply: the Builder implements packets, Codex audits every packet, and Fable performs the phase-end audit. Wherever this document says "the Builder," it means the implementing role inside the existing harness session.

The Builder must begin by inspecting the current repository and synthesizing:

- the canonical PRD and the active PRD-amendment work;
- the current handoff/checkpoint and readiness posture;
- open branches, pull requests, unresolved gates, and failing checks;
- the existing harness orchestrator and its packet conventions;
- existing Personal OS UI, data, scheduling, notification, secrets, logging, and Obsidian boundaries;
- any existing Knowledge Edge OS notes, source registries, prompts, schemas, or prior implementations.

The Builder must then produce a **repo-grounded implementation plan** that maps every requirement in this amendment to the current architecture and divides the work into the major phases and bounded packets defined below. It must not invent a parallel orchestrator, duplicate an existing service, or start from scratch when an existing Personal OS primitive can be extended safely.

The planning deliverable must include:

1. Current-state synthesis.
2. PRD integration diff or exact proposed amendment location.
3. Requirements traceability matrix.
4. Architecture decision record(s).
5. Source-adapter and credential plan.
6. Data migration plan.
7. Major-phase and packet plan.
8. Validation strategy and exact test layers.
9. Risk register and rollback plan.
10. Human decisions and stop gates.
11. Proposed branch/PR strategy that avoids micro-PRs.
12. Updated Personal OS go-live checklist showing this capability as launch-blocking.

Do not create a standalone status-refresh PR. Fold necessary status, checkpoint, discoverability, and governance updates into the active substantive PRD amendment or the next substantive implementation packet.

### Execution model — batched human gates

Human involvement is consolidated into three scheduled sessions plus lightweight asynchronous merge acknowledgments. All stop-gate obligations below remain in force; Session 1 satisfies the external-access gates upfront through an explicit, scoped pre-authorization bundle instead of mid-flight interruptions. Any action exceeding an approved scope re-opens the corresponding gate.

**Session 1 — Plan approval and external-access pre-authorization (closes Packets 0A–0B and authorizes Packet 0C; occurs before implementation).** Approves in one sitting: the Phase 0 repo-grounded plan, including the D-YT YouTube sourcing decision (§10.4); the external-access bundle (YouTube Data API credential where D-YT requires it, structured earnings-calendar provider selection and credential, broad person-search provider selection and credential if adopted, the source/channel allowlist, the approved IR/webcast vendor-domain list and redirect rules, SEC EDGAR user-agent identification, and provider entitlement artifacts identifying each paid provider's plan or agreement and its permitted fields, retention, derived use, local display, and test-fixture rights); the launch role appendix enumerating every role-based watch with initial occupant, effective date, and roster cap; and the scope limits attached to the bundle (read-only access, named endpoints and approved vendor domains only, isolated shadow database path only, no production notifications, no Obsidian writes, no scheduler installation).

**Autonomous run — Packet 0C through Phase 5.** The harness executes without scheduled human sessions. Each major-phase merge requires only an asynchronous human acknowledgment after Codex packet audits and the Fable phase-end audit are reconciled. Merge acknowledgments are drift checkpoints, not working sessions.

**Session 2 — Shadow-scheduler activation and threshold sign-off (precedes the Phase 6 soak).** Approves: installing and loading the scheduler in shadow configuration; final empirical quality thresholds (precision, recall, duplicate leakage, duration cutoffs) measured during Phases 2–3 against the frozen ground-truth sample — Phase 0 sets only provisional empirical values plus fixed policy thresholds such as caps and expiry; and the soak plan, including its named calendar window. Shadow-scheduler activation is an explicit, distinct gate. It authorizes scheduled autonomous runs in `shadow_live` mode only and does not authorize production operation.

**Session 3 — Readiness review and production activation (closes Phase 6).** Consists of three ordered steps: (1) authorize, execute, and verify a bounded production smoke test — production notifications and, if desired, first real Obsidian vault access on a limited sample — including its rollback path; (2) review Phase 6 pre-activation acceptance, which must already be satisfied before the session convenes; (3) approve the production mode change and Personal OS go-live. Steps may not be reordered or combined.

### Mandatory stop gates

The Builder must stop for explicit human review before the following. Gates marked **(S1)**, **(S2)**, or **(S3)** are satisfied by the corresponding session's approval when the action stays within the approved scope:

- merging any PR (asynchronous acknowledgment acceptable after audits reconcile);
- handling or installing credentials, secrets, OAuth, API keys, or tokens **(S1)**;
- enabling live external requests for the first time **(S1)**;
- accessing or writing the production Personal OS database **(S3)** — the Phase 0 plan must name the exact development, shadow, and production database paths or schemas; Session 1 authorizes only the isolated shadow path;
- accessing or writing the real Obsidian vault **(S3)**;
- installing, loading, or enabling a LaunchAgent, scheduler, daemon, watcher, background loop, or service — shadow configuration **(S2)**, production configuration **(S3)**;
- enabling macOS notifications in the production user context **(S3)**;
- performing live generative-model inference calls (approved source API requests within the Session 1 bundle are not model calls and are S1-authorized);
- invoking OpenClaw;
- changing readiness status to ready or activating Personal OS **(S3)**;
- making a scope or wording decision that could be interpreted as authorization for trading, external messaging, live execution, or autonomous thesis changes.

Human merge approval remains separate from technical validation and separate from live activation approval.

### Audit posture

Audits follow existing harness conventions: **Codex audits every packet, and Fable performs the phase-end audit. The Fable phase-end audit must be complete and reconciled before each major-phase PR merges.**

The implementing Builder session does not audit its own work. Bundle adjacent packets into one major-phase PR where safe so packet auditing does not create a micro-review loop.

---

## 1. Executive summary

Personal OS will include a local-first **Daily Intelligence Queue** that removes the daily friction of finding worthwhile material while preserving human judgment over what deserves attention and what changes a thesis.

The system runs automatically on the Mac mini, discovers and normalizes high-signal content, removes duplicates and low-value noise, and presents a finite queue with explicit decisions. The initial product has four lanes:

1. **Curated Podcasts** — new releases from a bounded, approved source roster.
2. **Market Voices** — direct appearances by a bounded list of investors, strategists, analysts, and recurring financial-media contributors.
3. **Consequential Leaders** — direct, substantive appearances by people or role occupants whose remarks may materially change an AI, crypto, infrastructure, or market thesis.
4. **Earnings & Corporate Events** — upcoming earnings calls and selected investor events for a bounded priority-company universe, surfaced before the event and updated with official live/replay links and primary materials.

The default daily full scan occurs at **4:30 p.m. America/Chicago**. The queue is ready for evening triage. A lightweight **6:15 a.m. America/Chicago** refresh verifies same-day earnings times, links, cancellations, and schedule changes. A manual "Scan now" action is always available.

The system automates discovery, normalization, ranking, deduplication, reminders, state tracking, and source health. The user remains responsible for watching/listening, interpretation, verification, synthesis with ChatGPT, and promotion into durable Obsidian knowledge, theses, or forecasts.

This capability is **launch-blocking for Personal OS**. Personal OS must not be declared live until the major phases in this amendment meet their acceptance criteria and the final activation gate is approved.

---

## 2. Problem statement

The current knowledge-building routine has a strong downstream method but a weak front end. It depends on manually opening several apps, remembering source rosters and people, searching across inconsistent feeds, judging what is new, avoiding duplicate clips, tracking unfinished material, and remembering upcoming calls. That creates decision fatigue before learning starts.

The predictable failure mode is drift:

- discovery becomes browsing;
- browsing becomes an unbounded feed;
- saved items accumulate without decisions;
- important events are found after they occur;
- the routine becomes cognitively expensive;
- missed days create catch-up pressure;
- the system is eventually abandoned.

The product must therefore make the next useful action obvious while keeping the queue finite, explainable, and easy to clear.

---

## 3. Product thesis

A knowledge routine becomes sustainable when the system does the recurring clerical work but does not outsource judgment.

The core loop is:

> **Discover → Triage → Consume → Interpret → Synthesize → Store → Review**

The Daily Intelligence Queue owns **Discover** and supports **Triage**. ChatGPT and Obsidian support the downstream interpretation and memory loop. No automated discovery result is itself evidence, and no repeated media narrative is allowed to update a thesis merely because it appeared frequently.

---

## 4. Goals

### 4.1 User goals

The user must be able to:

- open Personal OS in the evening and see a prepared, finite menu;
- know which core podcasts released new material;
- know whether a tracked market voice or consequential leader spoke directly in a new interview, panel, keynote, financial-media segment, or podcast;
- see tomorrow's relevant earnings calls before the event;
- access the best available official live or replay link without searching;
- decide **Watch**, **Save for later**, **Skip**, or **Watched** in seconds;
- avoid seeing the same content repeatedly across channels and clips;
- understand exactly why each item surfaced;
- trust that a missed scan will catch up without creating duplicates;
- preserve only watched, useful material in the durable knowledge system;
- review which sources, people, companies, and formats produce actual learning over time.

### 4.2 System goals

The system must:

- run reliably on the Mac mini on a declared schedule;
- operate locally except for approved read-only source requests;
- integrate with existing Personal OS architecture and harness conventions;
- use bounded, human-editable source/person/company registries;
- persist decisions and scan cursors idempotently;
- distinguish content status from user decision state;
- prioritize official and primary links;
- expose source failures and coverage gaps rather than implying completeness;
- keep queue and backlog sizes bounded;
- support safe disable, rollback, and uninstall;
- require no live LLM call for discovery, ranking, or queue generation at launch;
- generate an Obsidian-ready handoff only after the user marks an item watched or starts synthesis.

### 4.3 Launch outcome

At Personal OS go-live, the Mac mini must autonomously build the queue at the scheduled time, the user must be able to triage it in Personal OS, and the earnings lane must successfully complete the prior-evening-to-replay lifecycle for real tracked events.

---

## 5. Non-goals and prohibited behavior at launch

The launch version will not:

- place trades, recommend trades, or connect to a brokerage;
- interpret a surfaced item as financial advice;
- automatically change thesis confidence, thesis direction, forecasts, or source tiers;
- autonomously write final synthesis notes, contributor scores, or forecasts into Obsidian;
- download or archive full copyrighted video, audio, or unlicensed transcripts;
- bypass paywalls, authenticated sessions, CAPTCHAs, robots controls, or platform restrictions;
- attempt exhaustive monitoring of every television network, podcast, conference, or social account;
- scrape private feeds or logged-in watch history;
- synchronize YouTube Watch Later or cross-platform playback state;
- create an unlimited "inbox zero" obligation;
- run a continuous high-frequency crawler;
- send email, write Google Calendar events, or access Todoist at launch;
- use OpenClaw for repository implementation, validation, PR review, or ordinary queue operation;
- use a live model to classify relevance or generate summaries at launch;
- silently add people, companies, sources, aliases, or role occupants to the active roster.

Adaptive ranking, transcript-assisted extraction, automatic pre-call question generation, Calendar integration, and broader network coverage are post-launch candidates and require separate approval.

---

## 6. Product principles

1. **Queue, not feed.** The product presents a finite decision surface, not an endless timeline.
2. **Human judgment remains authoritative.** Automation proposes; the user decides.
3. **Primary before commentary.** Official IR pages, filings, direct interviews, and original uploads outrank reaction content and reposts.
4. **Directness matters.** "A video about Sam Altman" is not a Sam Altman appearance.
5. **Absence is acceptable.** "No high-signal release today" is a successful result.
6. **Explain every result.** Each item shows which rule, source, person, company, topic, or event caused it to surface.
7. **Bound the backlog.** Saved items expire or require deliberate pinning.
8. **Local-first and reversible.** Data, state, configuration, logs, and controls remain inspectable and disableable.
9. **Idempotent automation.** Re-running a scan must not duplicate records or decisions.
10. **Coverage honesty.** The product reports what it checked, what failed, and what remains unverified.
11. **No guilt mechanics.** Metrics diagnose system quality; they do not shame the user.
12. **No hidden self-modification.** The system can recommend roster or ranking changes but may not apply them without approval.

---

## 7. User experience and daily operating model

### 7.1 Primary daily schedule

| Time (America/Chicago) | Job | User-facing behavior |
|---|---|---|
| 4:30 p.m. | Full discovery scan | Poll all approved lanes, normalize, deduplicate, rank, and build the evening queue. |
| 4:40 p.m. target | Queue-ready notification | One local notification showing actionable counts; no notification storm. |
| 6:15 a.m. | Earnings/event refresh | Recheck same-day time, status, official view link, and cancellation/change signals. Silent unless a watched event changed materially. |
| ~T-60 and T-15 min before each watched live event | Targeted link check | For Watch-live commitments with an exact known start time only: verify the official webcast URL and schedule; notify once if the requested link becomes available or the event materially changed. Bounded to the watched event; does not trigger a full scan. |
| On demand | Scan now | Safe manual refresh with the same idempotent pipeline. |

The implementation may adjust internal timing to fit existing Personal OS scheduler conventions, but the user-facing service-level target remains "queue ready by 4:45 p.m. CT."

### 7.2 Evening queue layout

The default queue has these sections:

1. **Tomorrow: Earnings & Corporate Events**
2. **P0: Consequential Leader Appearances**
3. **P1: Core Podcast Releases**
4. **P2: Market Voice Appearances**
5. **Saved to Reconsider**
6. **Coverage & Source Health**

The earnings section is separate from the evening media-duration cap because it is a planning surface for future events.

### 7.3 Standard media decisions

For podcasts, interviews, panels, and clips:

- **Watch** — place in the active Tonight queue.
- **Save for later** — retain in the bounded saved queue.
- **Skip** — suppress this item and its recognized duplicates.
- **Watched** — record completion and expose the synthesis handoff.

### 7.4 Earnings/event decisions

For a scheduled call or investor event:

- **Watch live** — keep in the next-day event agenda and enable an optional local reminder.
- **Save replay** — do not require live attendance; monitor for the official replay and resurface once it becomes available.
- **Skip** — suppress this event for the current quarter/event occurrence.
- **Watched** — record completion and expose the earnings synthesis handoff.

### 7.5 Minimum viable triage

The daily triage should take less than five minutes. Each card must show enough information to decide without opening a search engine:

- title/event name;
- source/company;
- publication or scheduled time in America/Chicago;
- duration when known;
- matched person, role, company, and topic tags;
- directness and confidence;
- item type: full interview, panel, keynote, short clip, earnings call, investor day, replay, and so on;
- a concise deterministic "Why this surfaced" explanation;
- best current view link;
- source/coverage warning when relevant;
- decision controls.

### 7.6 Knowledge handoff

After an item is marked Watched, Personal OS must offer:

- **Copy synthesis packet** — metadata, links, matched theses/topics, timestamps entered by the user, and the standard ChatGPT synthesis instructions;
- **Create Obsidian draft** — only after production-vault access is separately approved; create a bounded draft or staging note, not a final thesis update;
- **No thesis impact** — close the item without creating durable knowledge;
- **Promote to session note** — create or stage the learning-session note template.

The canonical interpretation remains manual. The system must not infer that "watched" means "agreed," "important," or "thesis-changing."

---

## 8. Lane requirements

### 8.1 Lane A — Curated Podcasts

#### Launch roster

**AI**

- Dwarkesh Podcast
- Latent Space
- No Priors

**Crypto**

- Unchained
- Bankless
- Forward Guidance

**Markets**

- Odd Lots
- Macro Voices
- The Compound and Friends

#### Requirements

The podcast adapter must:

- poll approved public RSS/Atom feeds or approved official source endpoints;
- preserve stable feed and episode identifiers;
- record publication time, title, description, duration, artwork reference, and canonical link when available;
- group audio and video versions of the same episode;
- recognize corrected/reissued episodes without producing duplicates;
- support active, trial, paused, and retired sources;
- report feed failures and stale sources;
- permit a source-level cadence expectation without assuming missed publication is an error;
- expire unplayed old releases according to queue policy;
- never browse the recommendation homepage to fill an empty queue.

Core-source releases receive P1 priority unless demoted by duplication, staleness, or explicit source status.

---

### 8.2 Lane B — Market Voices

#### Launch roster

- Tom Lee
- Dan Ives
- Mohamed El-Erian
- Liz Ann Sonders
- Mike Wilson
- Gene Munster
- Mike Novogratz
- Stephanie Link

The data model must not label every person a formal "CNBC contributor." Relationship to a network is an effective-dated, nullable affiliation attribute. The durable tracking entity is the person.

#### Requirements

The system must search approved public sources for direct appearances and support:

- exact names and approved aliases;
- spelling variants such as Mohamed/Mohammed El-Erian;
- effective-dated organizations and titles;
- official network uploads and podcasts;
- direct interview, panel, remote guest, keynote, or original podcast classifications;
- source allowlists and blocklists;
- duplicate clips and repost suppression;
- a confidence score and reason for each match;
- a false-positive flag from the user;
- a rolling 90-day appearance history;
- time-on-show or segment duration when reliably available;
- topic/narrative tags without automatically creating or scoring a forecast.

A person mention in commentary is not a direct appearance and must not receive P2 priority.

---

### 8.3 Lane C — Consequential Leaders

#### Launch people and roles

**Frontier AI**

- Sam Altman
- Dario Amodei
- Demis Hassabis
- configured heads of frontier AI labs as effective-dated roles

**Compute and technology platforms**

- Jensen Huang
- Lisa Su
- Satya Nadella
- Sundar Pichai
- Mark Zuckerberg
- Andy Jassy
- Apple CEO role
- Elon Musk

**Enterprise AI, capital allocation, and crypto**

- Alex Karp
- Gavin Baker
- Brad Gerstner
- Brian Armstrong
- Vitalik Buterin

**Role-based watches**

- Federal Reserve Chair
- U.S. Treasury Secretary
- SEC Chair
- CFTC Chair
- Apple CEO
- configured frontier-lab heads
- configured AI accelerator/semiconductor platform heads

The role model must preserve historical occupants and effective dates. It must not hard-code current political or corporate officeholders in logic. Every "configured" role above must be enumerated in the Session 1-approved launch role appendix (role, initial occupant, effective date, roster cap); Packet 1A seeds roles from that appendix, not from this list alone.

#### P0 inclusion rule

A result receives P0 only when the tracked person or current role occupant is directly and substantively speaking in one of the following:

- original long-form interview;
- panel or fireside chat;
- keynote or product presentation;
- earnings-call participation;
- government testimony or formal hearing;
- substantive financial-media segment;
- original podcast guest appearance.

"Substantive" is applied deterministically. An appearance qualifies when its format class is long-form interview, panel/fireside, keynote, testimony, earnings participation, or original podcast, or when a financial-media segment has a known direct-appearance duration at or above a configured threshold (default 5 minutes; provisional in Phase 0, finalized at Session 2). Segments from approved sources with unknown duration are classified `ambiguous` and surfaced demoted with an ambiguity label rather than promoted to P0 or silently dropped.

The following are excluded or demoted:

- reaction videos;
- commentary about the person;
- synthetic voice or fan edits;
- trailers and teasers;
- short clips that duplicate a longer original;
- stale footage reposted with a new title;
- thumbnail-only matches;
- compilation videos without meaningful direct remarks.

A P0 label means "review promptly," not "interrupt life immediately." Literal interruptive alerts are opt-in and limited to explicitly watched live events.

---

### 8.4 Lane D — Earnings & Corporate Events

#### Product decision

This lane is required. Earnings calls are one of the highest-density primary-source inputs for AI demand, capital expenditure, data-center buildout, power demand, crypto business models, customer concentration, management guidance, and competitive positioning. The lane must be treated as a scheduled-event workflow rather than an ordinary content feed.

#### Launch event types

- quarterly earnings calls;
- annual-results calls;
- official investor days/capital-markets days for Tier A companies;
- material company-hosted strategy or financial-update webcasts when announced through official IR channels.

Product launches, industry conferences, government hearings, and broader live events may use the same generic event model later, but they are not required for launch unless already covered by the Consequential Leaders lane.

#### Event lifecycle

```text
Event status (content track):
discovered → tentative → confirmed → scheduled → live → ended
  → replay_pending → replay_available → archived
Any pre-event status may transition to changed or cancelled.

User decision (decision track, stored separately):
undecided → watch_live | save_replay | skip | watched

Queue visibility (queue track, stored separately):
candidate → queued | suppressed | expired | archived
```

Event status, user decision, and queue visibility are three separate state machines; `watched`, `skipped`, and `expired` never appear in the event-status track. Media items use an analogous three-track model. Packet 1A must publish the full transition tables for all three tracks for both media items and events, with invalid transitions rejected and tested.

#### T-minus workflow

**T-7 days to T-2 days**

- Detect and store the event.
- Verify company, quarter, date, expected timing, and official IR page when available.
- Display in the seven-day upcoming view but do not push it into the daily queue solely because it exists.

**T-1 evening**

- Surface every confirmed Tier A event scheduled for the next local day. Estimated-only events remain in the seven-day upcoming view with their confidence label and do not enter the T-1 section until confirmed.
- Surface Tier B events when they match an active thesis/topic, are manually pinned, or meet configured priority rules.
- Display local time, before-open/after-close context when available, confidence, and current official link status.
- Offer Watch live, Save replay, and Skip.

**T-0 morning**

- Refresh schedule, time zone, cancellation/change status, and official webcast URL.
- Notify only when a watched event changed materially or the requested live link became available.

**T-0 pre-event (watched events only)**

- Run targeted link checks at approximately T-60 and T-15 minutes before each Watch-live commitment.
- Notify once when the requested live link becomes available or the schedule materially changes.
- These checks are bounded to watched events and do not trigger a full scan.
- Targeted checks are scheduled only for events with an exact known start time; date-only or approximate events cannot receive T-minus checks and are labeled accordingly.

**T-0 post-event**

- Detect official replay, earnings release, shareholder letter, slides, and relevant filing links.
- For Save replay decisions, resurface once when the official replay becomes available.
- Do not create a second duplicate item for the replay.

**T+1 and later**

- Retain an event record and linked materials.
- Expire the queue item according to policy while preserving audit history.
- Expose the earnings synthesis handoff when marked watched.

#### Link hierarchy

The card must expose the best available link in this order:

1. official company live webcast URL;
2. official company event detail page;
3. official investor-relations events page;
4. official company replay URL;
5. official company upload on an approved platform;
6. approved secondary event page, clearly labeled as secondary.

If a live URL is not yet published, the card must show `Link pending` and the official IR events page rather than a guessed or unofficial stream. A webcast URL resolving to a domain outside the Session 1-approved IR/webcast vendor list is quarantined as `Link pending (unknown vendor)` and is not fetched or displayed as verified until the domain is separately approved.

#### Primary materials

Where available, the event record must link, not automatically ingest full copyrighted material, to:

- earnings release;
- shareholder letter;
- earnings presentation/slides;
- Form 8-K or equivalent current report;
- Form 10-Q, 10-K, 6-K, 20-F, or other relevant filing;
- official transcript;
- official replay;
- prepared-remarks document.

SEC EDGAR may be used after approval as a read-only source for U.S. filing metadata and links. SEC public data APIs provide company submissions and XBRL data without API keys, but implementation must follow SEC fair-access requirements and identify the application appropriately.

#### Schedule confidence

Every event must carry one of:

- `confirmed_official` — date/time verified from company IR or an official filing;
- `confirmed_secondary` — confirmed by a structured calendar provider but not yet found on official IR;
- `estimated` — provider estimate only;
- `unknown`.

Schedule changes and cancellations are event-status concerns, not confidence values: they are recorded in the event lifecycle state and change history, after which confidence is re-derived from the best current source. Estimated dates must never be presented as confirmed.

#### Material change taxonomy

"Materially changed" is deterministic and versioned in configuration. Launch change classes: cancellation; date change; start-time shift at or above a configured threshold (default 30 minutes); live or replay link availability gained or lost; and official status reversal (confirmed to estimated or unknown). Each class carries transition and notification-deduplication tests (§20). No notification or event behavior may depend on an unclassified notion of material change.

---

## 9. Priority company universe

The company roster is configurable, effective-dated, and capped. It is a research universe, not a portfolio recommendation.

### 9.1 Tier A — Must surface on T-1

The launch cap is **20 Tier A companies**. These calls appear in the prior-evening queue whenever scheduled, even if the user has no current saved thesis for the company.

#### AI platforms, demand, and enterprise adoption

1. Microsoft
2. Alphabet
3. Amazon
4. Meta Platforms
5. Apple
6. Oracle
7. Palantir Technologies
8. Tesla

#### Compute, accelerators, and semiconductor supply chain

9. NVIDIA
10. Advanced Micro Devices
11. Broadcom
12. Taiwan Semiconductor Manufacturing Company
13. ASML
14. CoreWeave

#### Data-center infrastructure and power

15. Vertiv
16. GE Vernova
17. Constellation Energy

#### Crypto rails, balance sheets, and stablecoins

18. Coinbase
19. Strategy
20. Circle Internet Group

### 9.2 Tier B — Tracked and conditionally surfaced

Tier B companies are tracked in the seven-day calendar and surfaced T-1 when manually pinned, linked to an active thesis, elevated by a current topic rule, or selected by a deterministic priority policy.

#### AI infrastructure, memory, networking, real estate, and power

- Micron Technology
- Arista Networks
- Eaton
- Equinix
- Digital Realty
- Vistra
- Talen Energy
- Applied Digital

#### Crypto platforms and public-market infrastructure

- Robinhood Markets
- Galaxy Digital
- Block

#### Bitcoin miners and HPC-transition companies

- MARA Holdings
- CleanSpark
- IREN
- Riot Platforms
- Hut 8

### 9.3 Required company fields

Each company record must support:

- stable internal company ID;
- legal name and display name;
- aliases and former names;
- ticker(s), exchange(s), and effective dates;
- CIK or equivalent regulatory identifier when applicable;
- priority tier;
- domain/topic tags;
- official investor-relations root URL;
- official events page URL;
- official filings page URL when useful;
- fiscal year and reporting cadence when known;
- primary reporting time zone;
- active/paused/retired state;
- manual pin state;
- linked active theses/topics;
- source-verification date;
- notes and exception rules.

The Builder must verify current tickers, identifiers, official IR URLs, mergers, renames, and listing status from official sources during the live-adapter planning phase. Names and identifiers must not be assumed to remain static.

### 9.4 Roster governance

- Tier A is capped at 20 at launch.
- Tier B is capped at 20 at launch.
- No company is promoted or removed automatically.
- Monthly review may propose changes based on watch yield, thesis relevance, information value, and false-positive/missed-event data.
- A promotion requires an explicit reason and user approval.
- A company must not be demoted solely because the user skipped one quarter.
- Corporate actions, ticker changes, mergers, and role changes must preserve historical records rather than overwrite them.

---

## 10. Source strategy and precedence

### 10.1 Approved source classes

The architecture must support adapters for:

1. public podcast RSS/Atom feeds;
2. official YouTube channels and approved public video search;
3. official network/program uploads and public feeds;
4. official company investor-relations events and results pages;
5. an approved structured earnings-calendar provider;
6. SEC EDGAR public APIs and feeds;
7. approved broad podcast-person search provider;
8. manually entered canonical links.

### 10.2 Source precedence

For claims about schedule, identity, or view location:

1. official company/network/person source;
2. regulator/exchange source;
3. approved structured provider;
4. reputable secondary source;
5. broad search result.

A lower-precedence source may discover an item, but higher-precedence confirmation should replace or enrich it when available.

### 10.3 Launch video/network allowlist

The initial approved discovery universe should include:

- CNBC Television and the selected tracked-show feeds;
- Bloomberg Television and Bloomberg Technology official uploads;
- Yahoo Finance official uploads;
- official company, investor-relations, and executive channels;
- official conference/event-organizer channels added through human-approved configuration;
- official U.S. government and central-bank channels required by the role-based watches — Federal Reserve, U.S. Treasury, SEC, CFTC, and relevant Senate/House committee channels — as candidates, each subject to the standard source verification and roster approval.

Role-based watch coverage is limited to officially published hearing and event video. Unpublished, delayed, or member-only uploads are reported as coverage gaps, not treated as misses.

Additional networks or channels require source verification and roster approval. Broad web results may discover candidates, but an unapproved channel must not silently become a trusted source.

### 10.4 Candidate technical sources

The PRD does not mandate a paid vendor. Phase 0 must compare provider cost, rate limits, licensing, reliability, coverage, and allowed use before selection.

Current viable building blocks include:

- YouTube Data API search with publication-time boundaries and official channel filtering;
- public RSS/Atom feeds for core podcasts;
- a structured earnings-calendar API such as Financial Modeling Prep — adoption requires a Session 1 provider entitlement artifact confirming the plan's display, persistence, and fixture rights for single-user local use; absent that evidence, use link-only data;
- Nasdaq's public earnings calendar as a manual reference surface only — its calendar endpoint is undocumented, so it must not be implemented as an automated adapter;
- official company investor-relations pages for confirmed event and webcast links;
- SEC EDGAR public APIs for filings and post-event primary documents.

YouTube sourcing is a mandated Phase 0 architecture decision (**D-YT**), resolved in the plan and approved at Session 1. The YouTube API Services Developer Policies prohibit API clients from using API data to create new or derived data or metrics, restrict aggregation, and require non-authorized API metadata to be refreshed or deleted on a 30-day cycle; the derived-metrics exception applies only to audited analytics developers. Because this design derives directness classes, confidence values, priority scores, and canonical groups, the Phase 0 plan must select and justify one of:

1. **RSS-first (default recommendation).** Poll allowlisted channels via YouTube's official channel RSS feeds — outside the API Services terms and quota — and restrict the Data API to person search only, minimizing stored API-sourced fields to stable identifiers.
2. **Third-party person search.** Route person/appearance search through the Session 1-approved broad-search provider under licensing that permits derived classification, removing the Data API from the classification path.
3. **Documented deviation — rejected alternative.** Retaining the Data API with derived classification as a recorded deviation was considered and rejected: documenting a known terms violation does not make the implementation compliant, and this path cannot satisfy any launch acceptance criterion. It is preserved here only as a rejected alternative for the ADR record.

The launch implementation must select option 1, option 2, or a combination of both. The D-YT ADR must demonstrate that the terms of each selected source permit the specific classifications performed on that source's data; any source whose terms do not permit them is used for display and linking only, with the coverage impact documented.

Under the selected option: provider display metadata sourced from the Data API (titles, descriptions, channel names) lives in a TTL-controlled refreshable cache with expiry, refresh, deletion, and deleted-video tests; only stable identifiers and internal or user-authored facts persist indefinitely; and the Phase 0 plan must include a worst-case quota budget covering the full roster, aliases, pagination, overlap windows, retries, manual scans, and soak traffic — preferring upload-playlist or RSS polling for allowlisted channels and requiring an approved quota extension before any design that exceeds the reserve is accepted.

The system must not depend on undocumented private endpoints when an official source is available.

### 10.5 Coverage reporting

Each scan must report health by adapter/source:

```text
Core podcast feeds: 9/9 healthy
Official video channels: 12/13 healthy
Person search: healthy; last success 16:34 CT
Earnings calendar: healthy
Official IR verification: 18/20 checked; 2 link-pending
SEC filings: healthy
Overall coverage: strong but incomplete
```

The absence of a result must never be described as proof that no appearance occurred.

---

## 11. Discovery, normalization, matching, and deduplication

### 11.1 Scan cursor behavior

- Store the last successful cursor per adapter/source.
- Use a configurable overlap window to catch delayed uploads and clock differences.
- If the Mac was off or a source failed, catch up from the last successful cursor.
- Commit a cursor only after the relevant source batch is persisted successfully.
- Re-running the same window must be idempotent.

Apple documents timed `launchd` jobs for user agents and notes that jobs missed while the machine is powered off may not run until a later scheduled occurrence. The implementation must therefore rely on persisted catch-up cursors rather than assume every wall-clock run occurred.

### 11.2 Canonicalization

Normalize:

- URL tracking parameters;
- video and episode identifiers;
- feed GUIDs;
- company, person, and role aliases;
- publication/scheduled timestamps to UTC;
- display timestamps to America/Chicago;
- source names and channel IDs;
- media duration;
- event quarter/fiscal period;
- alternate audio/video/replay links.

### 11.3 Directness classification

The deterministic classifier must produce:

- `direct_primary` — person/company is the original speaker/source;
- `direct_secondary_upload` — direct remarks reposted by an approved source;
- `panel_participant`;
- `host_or_interviewer`;
- `mentioned_only`;
- `commentary_about`;
- `ambiguous`.

Only direct_primary, direct_secondary_upload, or panel_participant may receive P0/P2 by default.

### 11.4 Deduplication

The system must group or suppress:

- audio and video versions of one podcast episode;
- full segment and clipped excerpt;
- network upload and guest-channel repost;
- original live event and official replay;
- title changes on the same underlying ID;
- delayed reposts of old footage;
- same event discovered by calendar provider, IR page, and filing.

Suppression is applied only when documented deterministic evidence satisfies a versioned rule — shared canonical ID, identical feed GUID, same channel and underlying video ID, or equivalent. Weaker signals produce a `suspected_duplicate` label: grouped visually, never silently suppressed. No acceptance criterion may claim that clip, cross-channel repost, or stale-footage detection is complete; metadata-only detection is inherently partial while media and transcript downloads remain prohibited, so residual duplicate leakage is measured (§18) rather than assumed away.

The canonical record retains alternate links and discovery occurrences. Skipping the canonical item suppresses recognized duplicates for that occurrence.

### 11.5 Ranking

Ranking must be deterministic and explainable. Allowed factors include:

- lane and priority tier;
- directness;
- source precedence/trust;
- company tier;
- active thesis/topic match (per the Phase 0-approved thesis snapshot and deterministic matching grammar);
- novelty;
- recency;
- event proximity;
- duration/time cost;
- duplicate/repost penalty;
- prior user decision for the same occurrence;
- manually pinned state.

The launch system must not use opaque machine-learning personalization.

---

## 12. Queue and backlog policy

### 12.1 Evening media caps

- Tonight cap: **3 items**.
- Tonight known-duration cap: **90 minutes**.
- Saved cap: **12 items**.
- Saved expiry: **14 days** unless pinned.
- Saved resurfacing: no more than **2 items** in one daily queue.
- A saved item is not resurfaced every day.
- Skipped, expired, or duplicate items do not silently return.
- No filler is added when fewer than three items qualify.

No item enters Tonight without an explicit Watch decision: the system proposes candidates and never commits them. The daily candidate surface is itself bounded by configurable per-lane and total candidate caps (defaults set in Phase 0); qualifying P0 items beyond the candidate caps remain visible in a collapsed "Additional consequential appearances" section rather than being lost. Pinned saved items still count toward the Saved cap.

### 12.2 Earnings caps

- All next-day Tier A calls with confirmed schedules are visible in the earnings section; estimated-only events remain in the seven-day view with a visible confidence label.
- The interface recommends no more than **2 Watch live commitments per day** but does not hide additional calls.
- Save replay items resurface once when a verified official replay appears.
- Unwatched replay items expire from the active queue after **7 days** unless pinned.
- Event metadata and primary links remain archived after queue expiry.

### 12.3 Empty state

A valid queue may state:

> No qualifying item was found among the sources successfully checked (N of M healthy). Use a saved item or complete a primary-source review.

The empty state must display failed or unverified source counts alongside the statement and must never assert that no appearance or release occurred. The system must not broaden search or lower quality thresholds merely to populate cards.

---

## 13. Data model

The implementation must use existing Personal OS persistence conventions. If no suitable module exists, use a local SQLite-backed bounded context with migrations and clear ownership.

### 13.1 Required entities

- `source`
- `source_endpoint`
- `person`
- `role`
- `role_occupancy`
- `affiliation`
- `company`
- `company_identifier`
- `topic`
- `media_item`
- `scheduled_event`
- `discovery_occurrence`
- `entity_match`
- `canonical_group`
- `user_decision`
- `decision_history`
- `queue_snapshot`
- `scan_run`
- `scan_cursor`
- `source_health`
- `coverage_report`
- `roster_change_proposal`
- `synthesis_handoff`

### 13.2 Media item minimum fields

- internal ID;
- source-specific ID;
- canonical URL and alternate URLs;
- title and description excerpt;
- source and source precedence;
- publication and discovery timestamps;
- media type and duration;
- matched people, roles, companies, and topics;
- directness class and confidence;
- deterministic priority score and explanation;
- canonical-group/duplicate relationship;
- content status;
- user decision state;
- queue visibility state (candidate, queued, suppressed, expired, archived);
- expiry and pin state;
- coverage notes;
- created/updated timestamps.

### 13.3 Scheduled event minimum fields

- internal event ID;
- company and nullable fiscal period (investor days and non-quarterly events may have none);
- event type;
- scheduled date, optional start/end timestamps, a time-precision indicator (date-only, approximate, exact), and the source time zone;
- timing label such as before open/after close when available;
- schedule confidence and source;
- official event page;
- live webcast URL;
- replay URL;
- earnings release URL;
- filing URL(s);
- slides/shareholder letter/prepared remarks URLs;
- event status and change history;
- user decision state;
- queue visibility state;
- link verification timestamps;
- priority explanation;
- created/updated timestamps.

### 13.4 Audit history

Every user decision and automated state transition must be traceable. Append-only history records internal facts, stable identifiers, decisions, and user-authored notes; it does not archive provider display metadata that is subject to refresh or deletion obligations (§10.4). The system may update current state for efficient queries but must retain an append-only history sufficient to answer:

- what was discovered;
- when and from which source;
- why it surfaced;
- how it was grouped;
- which decision was made;
- what later changed;
- why it resurfaced or expired.

---

## 14. Personal OS integration

### 14.1 Architectural rule

This is a Personal OS module. The Builder must extend existing primitives for UI, persistence, job execution, configuration, logging, secrets, feature flags, and notifications when available. It must not ship an unrelated standalone dashboard unless the architecture plan proves that no safe native integration exists.

### 14.2 Required surfaces

Personal OS must expose:

- Daily Intelligence Queue dashboard;
- seven-day upcoming events view;
- saved queue;
- watched history;
- source/person/company registry views;
- source health and last-run status;
- scan-now control;
- kill switch/pause control;
- synthesis handoff action;
- bounded monthly yield report;
- clear indication of development, shadow, or live mode.

### 14.3 Configuration

Rosters and policy thresholds must be human-readable, schema-validated, version-controlled where appropriate, and editable through the repository or approved Personal OS admin surface. Runtime secrets must never be committed.

### 14.4 Feature modes

- `disabled`
- `fixture`
- `shadow_live` — live discovery and persistence, no production notification or Obsidian write;
- `active_read_only` — live queue and notifications, no external writes beyond approved local data;
- `active_with_obsidian_handoff` — approved bounded local Obsidian draft/staging write;

Scheduler activation is an orthogonal, separately gated dimension. Any mode may be run manually; scheduled execution in `shadow_live` requires the Session 2 shadow-scheduler gate, and scheduled execution in an active mode requires the Session 3 production-activation gate.

Mode changes are explicit, logged, and protected by the appropriate human gate.

---

## 15. Mac mini scheduling and notifications

### 15.1 Scheduler

Use the existing Personal OS scheduler if one is already approved and suitable. Otherwise, the proposed macOS implementation is a per-user `launchd` LaunchAgent implementing a single **due-work dispatcher** contract: `RunAtLoad` plus a fixed dispatcher interval — bounded and justified in the Phase 0 scheduler ADR and quota budget (allowable range 1–15 minutes; default 5) — that wakes, consults a local due-work table, and makes no external request unless work is due. The 4:30 p.m. scan, 6:15 a.m. refresh, and per-event T-minus checks are all rows in that table, with every deadline computed in America/Chicago inside the application rather than inherited from the system time zone. The contract must declare and test its operating conditions: user logged in, post-reboot behavior, Keychain availability, sleep/wake, runs missed while powered off (recovered via catch-up cursors on the next dispatch), and system time-zone changes. This is not a continuously running custom daemon.

Requirements:

- idempotent job entrypoint;
- persisted catch-up cursors;
- bounded runtime and timeout;
- single-instance lock;
- deadlines computed in America/Chicago independent of the system time zone;
- structured logs;
- retry/backoff for transient failures;
- partial success by source;
- safe manual run;
- documented install, load, unload, disable, and uninstall;
- no root requirement;
- no hidden persistence mechanism;
- no scheduler activation until the applicable gate passes: Session 2 for scheduled shadow runs, Session 3 for production operation.

### 15.2 Notifications

At launch, notifications are local macOS notifications only.

- one queue-ready notification after the daily scan when actionable;
- optional watched-event reminder;
- material schedule-change notification for watched events;
- source-failure notification only after a defined repeated-failure threshold;
- no per-item notification storm;
- no email, SMS, or external messaging.

The notification must deep-link into the corresponding Personal OS queue/event when supported by the existing application architecture.

---

## 16. Security, privacy, licensing, and operational boundaries

### 16.1 Credentials

- Read-only APIs only at launch.
- Credentials must use the existing approved secrets mechanism or macOS Keychain.
- No secrets in repository files, Markdown, SQLite records, logs, command history, screenshots, or PR descriptions.
- Network adapters must redact query keys and authorization headers.
- Credential creation and installation require explicit human approval.

### 16.2 Network controls

- Maintain an allowlist of approved domains/endpoints, including the Session 1-approved IR/webcast vendor-domain list; permit only bounded redirects from official IR pages to domains on that list, and quarantine unknown destinations as `Link pending` without fetching them until separately approved.
- Use documented public APIs/feeds where possible.
- Respect provider rate limits, terms, robots directives, and SEC fair-access guidance.
- Set an identifying user agent where required.
- Use timeouts, retries, and circuit breakers.
- A single source failure must not prevent the rest of the queue from building.

### 16.3 Content storage

At launch, store metadata, short excerpts permitted by source use, links, user decisions, and user-authored notes. Do not download full videos/audio or store unlicensed full transcripts.

### 16.4 Financial boundary

The module is a research and learning system. It must not:

- generate buy/sell instructions;
- execute orders;
- connect to brokerage accounts;
- frame priority as investment recommendation;
- claim that an earnings call is material to the user's portfolio without an explicit user-authored tag.

---

## 17. Reliability and failure handling

### 17.1 Required failure cases

The implementation must handle:

- Mac powered off at scheduled time;
- Mac asleep or temporarily offline;
- API quota exhausted;
- credential revoked or expired mid-run;
- malformed feed item;
- source endpoint moved;
- source returns duplicate or old content;
- event date changed after confirmation;
- event cancelled;
- webcast link published late;
- replay never published;
- ambiguous person/company name;
- role occupant changed;
- ticker/company rename or merger;
- database locked/corrupted, including stale single-instance lock;
- notification failure or notification permission denied;
- Obsidian path unavailable;
- canonical groups merged or split after user decisions exist;
- partial scan success.

### 17.2 Degraded behavior

- Build a partial queue from healthy sources.
- Preserve prior decisions and queue state.
- Mark stale/unverified data visibly.
- Retry only within bounded policy.
- Never erase current data because a source returned an empty response.
- Never advance a failed source cursor.
- Provide a human-readable recovery action.

### 17.3 Health surface

The dashboard must show:

- last full scan start/end and outcome;
- per-adapter last success;
- number of items discovered/accepted/rejected/grouped;
- rate-limit state;
- event links awaiting verification;
- scheduler state;
- current mode;
- next scheduled run;
- latest error summary with sensitive data redacted.

---

## 18. Metrics and controlled improvement

### 18.1 Product reliability metrics

- percentage of scheduled scans completed successfully;
- queue ready by 4:45 p.m. CT;
- source-health rate;
- duplicate rate;
- person-match false-positive rate and appearance recall/miss rate against the ground-truth sample;
- tracked Tier A earnings events surfaced T-1;
- fallback-page reachability, live-link acquisition rate (among events with a published official live link), and replay acquisition/resurfacing rate (among events with a published official replay), each measured separately;
- schedule-change detection rate;
- mean recovery time after source failure.

### 18.2 Habit and usefulness metrics

- daily decision completion rate;
- median triage time;
- Watch/Save/Skip distribution;
- saved-to-watched conversion;
- saved expiry rate;
- watched-to-session-note conversion;
- source yield by hour consumed;
- person/company watch yield;
- routine sessions completed per week;
- number of surfaced items that led to a thesis update or forecast.

Metrics are diagnostic. There are no streak punishments, guilt badges, or automatic expansion of the queue.

### 18.3 Recommendations

After sufficient history, the system may produce deterministic recommendations such as:

- retire a source with repeated low yield;
- demote a person with high false-positive/skip rates;
- promote a Tier B company with repeated thesis impact;
- adjust saved-item expiry;
- add an alias or official channel;
- repair a failing source endpoint.

No recommendation is applied automatically. At most one major workflow change should be approved in a monthly review.

---

## 19. Major phases and bounded implementation packets

All phases below are launch-blocking. Packets are implementation subphases, not mandatory separate PRs. Prefer one coherent PR per major phase unless harness conventions or the repository's established architecture require a different safe boundary.

Execution follows the batched-gate model in Section 0: Session 1 closes Packets 0A–0B and authorizes Packet 0C; Phase 0 closes after Packet 0C, audit reconciliation, and the asynchronous merge acknowledgment; Packet 0C through Phase 5 then run as one autonomous stretch with asynchronous merge acknowledgments; Session 2 precedes the Phase 6 soak; Session 3 closes Phase 6.

### Phase 0 — PRD integration and repo-grounded plan

#### Packet 0A — Current-state synthesis

- Inspect canonical PRD, active amendments, architecture, harness, data model, UI, scheduler, notifications, secrets, Obsidian integration, tests, and open PRs.
- Identify conflicts, reuse opportunities, and existing gates.
- Confirm whether this amendment can be folded into the active PRD amendment branch/PR.

#### Packet 0B — Requirements and architecture plan

- Integrate this amendment into the canonical PRD.
- Produce requirements traceability.
- Decide module boundaries and ownership, naming the exact development, shadow, and production database paths or schemas.
- Propose provider evaluation criteria — cost, rate limits, licensing, data-retention obligations, reliability, coverage — and recommend the earnings-calendar provider, the broad person-search provider (or a documented deferral with coverage impact), the D-YT YouTube sourcing option (§10.4), a worst-case quota budget, and the full external-access bundle for Session 1 approval, without creating credentials.
- Name the approved local source or versioned snapshot for active thesis/topic links (the real vault is unavailable until Session 3) and define the deterministic matching grammar: field-specific tokens, aliases, negative terms, and precedence rules that operate without vault access or an LLM.
- Define the ground-truth procedure for appearance quality: sample size, sampling window, and strata by lane and source, with provisional empirical thresholds.
- Define the migration, rollout, and rollback approach.
- Produce the phase/packet/PR plan and validation matrix.

#### Packet 0C — Live probe and golden fixtures (post-Session 1)

- Using the Session 1 credentials and scope, perform a thin, bounded, read-only pull of real metadata: recent episodes from each core podcast feed; recent uploads from sample allowlisted channels; person-search results for a representative subset of tracked people; one week of earnings-calendar data; and sample SEC EDGAR submissions.
- Convert raw captures into synthetic golden fixtures — real-shaped structure with provider-policy-safe content — before committing; raw API captures are never committed to the repository and follow the §10.4 cache rules. Phases 1–3 build against these fixtures rather than invented ones.
- Record provider quirks — missing durations, title conventions, clip patterns, quota cost per call type — as inputs to threshold planning.
- No persistence into production tables, no scheduler, no notifications, no Obsidian access.

#### Phase 0 acceptance

- Canonical PRD contains the amendment or an approved exact integration diff.
- Personal OS go-live checklist marks all later phases as blocking.
- No unresolved wording implies live authorization.
- Session 1 is held after Packets 0A–0B: the plan, D-YT decision, launch role appendix, and external-access bundle are approved with explicit scope before implementation begins.
- Packet 0C is complete: synthetic golden fixtures exist and provider quirks are documented.
- Phase 0 closes only after Packet 0C, packet-audit reconciliation, and the asynchronous merge acknowledgment.

#### Audit

Codex packet audits plus Fable phase-end audit, required before merge because this amendment changes workflow, governance, scheduler, external-source, and readiness boundaries.

---

### Phase 1 — Offline foundation, domain model, and queue UX

#### Packet 1A — Registries and schemas

- Source, person, role, company, topic, policy, and alias schemas.
- Seed the launch rosters in this PRD.
- Effective-dated roles, affiliations, tickers, and identifiers, seeded from the Session 1 launch role appendix.
- Full state-transition tables for the three tracks (status, decision, queue visibility) for media items and events, with invalid transitions rejected.
- Validation and migration framework.

#### Packet 1B — Fixture-based discovery engine

- Adapter contracts with fixture/mock implementations only, built against Packet 0C golden fixtures plus synthetic edge-case fixtures.
- Scan runs/cursors, normalization, matching, canonicalization, deduplication, directness, ranking, and state transitions.
- No-network enforcement.

#### Packet 1C — Local queue and decisions

- Personal OS-native queue surfaces using fixtures.
- Watch/Save/Skip/Watched and Watch live/Save replay states.
- Caps, expiry, resurfacing, source health, audit history, and synthesis handoff staging.

#### Phase 1 acceptance

- End-to-end fixture run produces all four lanes.
- Repeated scans are idempotent.
- State transitions and caps are enforced.
- Earnings event lifecycle works from discovery through replay in fixtures.
- No live network access occurs within Phase 1 packets beyond the already-completed 0C probe; no scheduler activation or real Obsidian access occurs.
- Unit/integration/UI tests and safety invariants pass.

#### Audit

Codex packet audits plus Fable phase-end audit, required before merge because this phase establishes Personal OS workflow and future live boundaries.

---

### Phase 2 — Live read-only media discovery

#### Packet 2A — Core podcast adapters

- Approved RSS/Atom discovery.
- Feed health and stale-feed detection.
- Audio/video grouping.
- Live shadow-mode validation against manual samples.

#### Packet 2B — Official channel and person search

- Approved YouTube Data API or equivalent official adapter.
- Official channel polling via the D-YT-selected mechanism (RSS or upload-playlist polling preferred for allowlisted channels).
- Person/role searches with publication boundaries, via the Data API and/or the Session 1-approved broad person-search provider per the D-YT decision.
- Network/program source configuration.
- Directness, duplicate, and stale-repost validation.

#### Packet 2C — Coverage and shadow report

- Run in `shadow_live` mode.
- Freeze the stratified manual ground-truth sample defined in Phase 0; its contents and construction procedure are Codex-reviewed and human-acknowledged before any threshold tuning begins; compare results against it.
- Tune deterministic thresholds without opaque personalization; report precision, recall, duplicate leakage, sample size, and unavailable-source treatment by lane.
- Document known network and podcast coverage gaps.

#### Phase 2 acceptance

- All nine core podcasts are monitored successfully or have documented approved exceptions.
- Market Voice and Consequential Leader live results are measured against the frozen ground-truth sample — precision, recall, duplicate leakage, and sample size reported by lane — relative to provisional Phase 0 thresholds; final thresholds are approved at Session 2.
- No unapproved source, scraping method, or credential storage is used.
- Source failures degrade gracefully.
- Live scan can be run on demand but is not yet scheduled in production.

#### Stop gates

Credential creation/installation and first live network execution are pre-authorized by the Session 1 bundle. Any source, endpoint, credential, or scope beyond the bundle re-opens the gate and requires explicit approval.

#### Audit

Codex packet audits plus Fable phase-end audit, required before merge because this phase operates live external-source and credential boundaries.

---

### Phase 3 — Earnings and corporate-events lane

#### Packet 3A — Company registry and calendar adapter

- Verify current company identifiers and official IR roots.
- Implement an approved structured earnings-calendar adapter.
- Distinguish estimated, secondary-confirmed, and official-confirmed dates.
- Seven-day upcoming view and T-1 selection.

#### Packet 3B — Official IR and filing resolution

- Official event-page and webcast-link resolution.
- Schedule-change and cancellation handling.
- SEC EDGAR read-only filing metadata/links where applicable.
- Official replay and primary-material attachment.

#### Packet 3C — Event decision workflow

- Watch live, Save replay, Skip, Watched.
- Morning refresh; change-notification intents emitted to a fake sink (delivery is implemented and validated in Packet 4B).
- Replay resurfacing and expiry.
- Earnings synthesis handoff.

#### Phase 3 acceptance

- Every Tier A company has verified identifiers and an approved source strategy.
- Real events complete the T-1 → T-0 refresh → replay lifecycle in shadow mode.
- Estimated dates are never mislabeled as confirmed.
- Official view link or official IR fallback is supplied.
- Schedule changes do not create duplicate events.
- SEC/provider rate and usage policies are documented and tested.

#### Stop gates

The approved calendar provider and endpoints from the Session 1 bundle are pre-authorized. Any additional paid provider, credential, or endpoint re-opens the gate and requires explicit approval.

#### Audit

Codex packet audits plus Fable phase-end audit, required before merge because this phase affects financial-research workflow, live external sources, credentials, and source-of-truth rules.

---

### Phase 4 — Mac mini scheduling, notifications, and operations

#### Packet 4A — Scheduled job packaging

- Integrate with the existing Personal OS scheduler or prepare a user LaunchAgent — built and validated in staging, staged for installation, but not installed or loaded.
- Due-work dispatcher contract per §15.1: idempotent entrypoints, lock, timeout, retries, cursors, structured logs, America/Chicago deadline computation.
- Install/load/unload/disable/uninstall documentation.

#### Packet 4B — Notification behavior

- Queue-ready notification.
- Watched-event reminder.
- Material schedule-change notification.
- Notification deduplication and quiet behavior, keyed to the material-change taxonomy.
- Delivery and deep-link validation in an isolated staging user/application context.

#### Packet 4C — Recovery and kill switch

- Offline/powered-off catch-up.
- Source failure and quota degradation.
- Safe pause and manual scan.
- Health dashboard and operator runbook.

#### Phase 4 acceptance

- Scheduler package passes fixture and staging tests.
- No duplicate concurrent scans.
- Missed-run catch-up works.
- Disable/uninstall leaves no hidden process.
- Notifications are bounded and deep-link correctly where supported.
- No scheduler installation or loading has occurred; the package is staged pending the Session 2 gate.

#### Stop gates

Shadow-configuration installation/loading occurs only at Session 2. Production scheduler operation and production notifications occur only at Session 3.

#### Audit

Codex packet audits plus Fable phase-end audit, required before merge and again as a read-only activation review at Session 2 if installation details changed after merge.

---

### Phase 5 — Obsidian handoff, review metrics, and system governance

#### Packet 5A — Synthesis handoff

- Copyable ChatGPT synthesis packet, including the standard synthesis instruction template as a versioned configuration deliverable.
- Watched-item metadata and user timestamp capture.
- Obsidian-compatible draft/staging output.
- Clear separation between session note, thesis, forecast, and appearance record.

#### Packet 5B — Approved local-vault integration

- Use the existing Personal OS Obsidian boundary if one exists.
- Validate against a staging vault path during the autonomous run; first real-vault access is enabled only at Session 3.
- Write only explicitly requested draft/staging notes.
- Never update thesis confidence or final notes automatically.
- Provide path validation, collision handling, and rollback.

#### Packet 5C — Monthly yield and roster review

- Bounded source/person/company/media-type reports.
- False-positive and missed-event review.
- Human-approved roster-change proposals.
- No automatic policy mutation.

#### Phase 5 acceptance

- A watched item can move into the manual ChatGPT/Obsidian loop without re-entering metadata.
- No skipped/unwatched item pollutes the vault.
- Production vault writes are bounded, user-triggered, and recoverable.
- Metrics are accurate and do not create streak/guilt mechanics.

#### Stop gates

First real Obsidian-vault access/write is approved at Session 3. Staging-vault validation requires no session.

#### Audit

Codex packet audits plus Fable phase-end audit, required before merge because this phase defines the boundary with a production local knowledge store.

---

### Phase 6 — End-to-end hardening and launch readiness

#### Packet 6A — Pre-launch soak (post-Session 2)

Run the complete system under the shadow-activated scheduler — scheduled autonomous daily cycles, not manual runs — for at least:

- seven consecutive calendar days;
- two real tracked earnings events through the event lifecycle;
- one source outage or simulated outage recovery;
- one powered-off/missed-run catch-up test;
- a representative sample of direct and indirect person matches.

The Session 2 soak plan must name a calendar window containing at least two qualifying tracked events; the soak extends until both complete. A correctly degraded outage cycle counts as healthy when degradation, recovery action, and data preservation behave as specified; an incorrectly handled outage restarts the seven-cycle count.

#### Packet 6B — Reconciliation and remediation

- Compare surfaced items with manual checks.
- Quantify misses, false positives, duplicates, and bad links.
- Repair material defects.
- Freeze launch rosters and thresholds.

#### Packet 6C — Final readiness package

- Operator runbook.
- Security/credential review.
- Scheduler and notification status.
- Data backup/restore validation.
- Disable/uninstall validation.
- Known limitations.
- Final requirements traceability.
- Go-live checklist and rollback plan.

#### Phase 6 acceptance

Pre-activation acceptance — every item satisfied before Session 3 convenes:

- Seven consecutive healthy daily cycles.
- 100% of officially announced Tier A earnings events in the manual acceptance sample surfaced by T-1; upstream events not officially announced by T-1 are reported separately as coverage limitations.
- Link success is measured with fixed denominators and Session 2-approved thresholds across three separate metrics: fallback-page reachability for all surfaced events; live-link acquisition among events for which an official live link was published; and replay acquisition and resurfacing among events for which an official replay was published.
- Person-appearance precision, recall, and duplicate leakage meet the Session 2-approved thresholds, measured by the frozen ground-truth procedure with reported sample sizes.
- Queue generation remains bounded under earnings-season load.
- No critical or high-severity unresolved defect.
- All major-phase audits reconciled.

Activation acceptance — completed inside Session 3, in order:

- The bounded production smoke test passes and its rollback path is verified (Session 3 step 1).
- Pre-activation acceptance is reviewed and confirmed (Session 3 step 2).
- Chris explicitly approves Personal OS go-live and activation (Session 3 step 3).

#### Audit

Fable phase-end audit required for the final readiness/activation posture, reconciled with all prior packet audits.

---

## 20. Test and validation requirements

The Builder must map these to repository-standard commands and report exact counts.

### 20.1 Unit tests

At minimum:

- source and roster schema validation;
- effective-dated role/ticker resolution;
- exact alias matching;
- partial-name false-positive prevention;
- direct appearance versus commentary-about classification;
- URL/feed GUID canonicalization;
- audio/video/replay grouping;
- stale repost suppression;
- event schedule confidence;
- time-zone/DST conversion;
- valid and invalid decision transitions;
- Tonight/Saved/event caps;
- expiry and pin behavior;
- deterministic ranking and explanations;
- source health transitions;
- cursor commit semantics;
- no-secret logging.

### 20.2 Integration tests

- idempotent repeated scan;
- overlap-window catch-up;
- partial source failure;
- quota/rate-limit degradation;
- missed scheduled run;
- event date/time change;
- late webcast link;
- replay appearance after Save replay;
- company rename/ticker change;
- role succession;
- database migration and rollback;
- synthesis handoff generation;
- Obsidian staging collision handling;
- notification deduplication per material-change class;
- scheduler single-instance behavior and stale-lock recovery;
- due-work dispatcher: missed-run recovery, DST transition, system time-zone change, logged-out and post-reboot behavior;
- credential revocation or expiry mid-run;
- provider schema drift and partial pagination;
- event cancellation propagation;
- replay never published (expiry path);
- database lock/corruption recovery with cursor and transaction assertions;
- notification permission denial with user-visible degraded state;
- canonical-group merge and split preserving prior user decisions;
- provider metadata cache expiry, refresh, deletion, and deleted-video handling.

### 20.3 End-to-end tests

- full four-lane queue from fixtures;
- approved live shadow scan;
- T-1 earnings appearance and T-0 refresh;
- Watch live notification path;
- Save replay resurfacing;
- Watched → synthesis handoff;
- disable/pause → no scheduled runs;
- uninstall/rollback leaves data in documented state.

### 20.4 Safety assertions

Every major-phase final report must state whether:

- live external calls occurred and under what approval;
- credentials were created, read, installed, or stored;
- production DB paths were accessed;
- real Obsidian paths were accessed;
- scheduler/background components were installed or activated;
- notifications were enabled;
- Todoist, Gmail, Google Calendar, brokerage, or other external services were accessed;
- OpenClaw was invoked;
- live generative-model inference calls occurred (as distinct from S1-authorized source API requests);
- media/transcripts were downloaded;
- protected paths were accessed;
- readiness or activation status changed;
- a merge occurred.

---

## 21. Launch definition of done

Personal OS may go live with this amendment only when all of the following are true:

1. The canonical PRD contains this amendment.
2. All seven major phases (Phase 0 through Phase 6) are complete and accepted.
3. The queue runs autonomously on the Mac mini at the approved schedule.
4. The four lanes render in Personal OS with persistent triage decisions.
5. The podcast roster is live and healthy.
6. Market Voice and Consequential Leader discovery is live with acceptable precision and explicit coverage limits.
7. Tier A earnings calls that are officially announced by T-1 surface the prior evening and refresh the morning of the event; events not officially announced by T-1 are reported as coverage limitations, not misses.
8. Cards provide a verified official viewing link or a clearly labeled official IR fallback.
9. Save replay items resurface when the official replay appears.
10. Missed-run catch-up, deduplication, caps, expiry, and kill switch work.
11. Watched items enter the manual ChatGPT/Obsidian loop without automatic thesis changes.
12. Secrets, logs, source access, and local paths pass security review.
13. Install, disable, rollback, and recovery are documented and tested.
14. Required independent read-only audits are complete and reconciled.
15. No critical/high defect remains open.
16. Chris explicitly approves final activation and Personal OS go-live.

Approval to merge code does not, by itself, approve production activation. Approval to activate the discovery queue does not authorize trading, external messaging, autonomous model interpretation, Calendar writes, OpenClaw, or automatic thesis updates.

---

## 22. Post-launch candidates — explicitly excluded from launch gate

These may be evaluated only after the launch system has stable usage data:

- transcript-assisted claim extraction;
- automated pre-call question packets tied to active theses;
- semantic relevance classification using a live model;
- broader podcast-person indexing;
- more television networks and international sources;
- product-launch and regulatory-hearing event types;
- Google Calendar or Todoist integration;
- mobile companion interface;
- adaptive ranking;
- automatic source/roster recommendations beyond deterministic reports;
- contributor forecast extraction and calibration automation;
- automatic monthly thesis-review drafts.

None of these may be pulled into a launch phase merely because the underlying generic event or adapter model can support them.

---

## 23. Open decisions for Phase 0 planning

The Builder should resolve these through repo inspection and present a recommendation, not block on a question unless the choice is safety- or architecture-critical:

1. Which existing Personal OS module owns the queue UI and data?
2. Does the harness orchestrator already provide safe scheduled-job semantics?
3. Which approved secrets mechanism is already used?
4. Which structured earnings-calendar provider best fits cost, licensing, and coverage?
5. Which official channels/network sources form the initial allowlist?
6. What precision/recall thresholds are achievable in the current architecture?
7. What is the approved Obsidian staging/final path boundary?
8. What local notification mechanism is already present?
9. Can all launch requirements fit one module, or are bounded adapters separate packages?
10. What is the exact pre-launch soak environment and dataset?
11. Which D-YT YouTube sourcing option (§10.4) is selected, and what do the selected providers' terms require of storage, cache TTL, and fixture design?

Defaults in this PRD apply when the repository provides no contrary approved convention.

---

## 24. Required major-phase final report format

For every major phase, the Builder must maintain a running implementation log and produce a final report with:

- scope completed;
- packets/subphases completed;
- files changed;
- migrations/configuration added;
- validation commands and results;
- exact test counts;
- coverage/precision findings when applicable;
- safety assertions;
- deviations from the PRD;
- unresolved risks and open questions;
- next human decision required;
- branch;
- commit;
- PR URL;
- human-review excerpt;
- Codex packet-audit status and Fable phase-end audit status, with reconciliation notes.

The human-review excerpt must state:

- what changed;
- what files changed;
- what safety boundaries remain true;
- what approving/merging would mean;
- what approving/merging would not mean;
- what Chris should double-check.

The Builder may not merge without explicit human approval; an asynchronous acknowledgment per the Section 0 execution model satisfies this requirement.

---

## 25. External reference notes for implementation planning

These references are planning inputs, not automatic authorization to use a provider:

- Apple, “Scheduling Timed Jobs” and “Creating Launch Daemons and Agents”: timed per-user work through `launchd`, including missed-run behavior considerations.  
  https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html  
  https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html

- YouTube Data API `search.list`: supports publication-time boundaries and query/channel filtering.  
  https://developers.google.com/youtube/v3/docs/search/list

- SEC EDGAR public APIs: company submissions and XBRL data are available in JSON without API keys; implementation must follow SEC access policies.  
  https://www.sec.gov/search-filings/edgar-application-programming-interfaces

- Financial Modeling Prep earnings-calendar documentation: candidate structured calendar source requiring provider, pricing, licensing, and credential review.  
  https://site.financialmodelingprep.com/developer/docs/stable/earnings-calendar

- Nasdaq earnings calendar: manual reference surface only (undocumented endpoint; must not be implemented as an automated adapter).  
  https://www.nasdaq.com/market-activity/earnings

---

## 26. Revision change log

### 26.1 Revision 1.1 — 2026-07-14 first audit dispositions

| # | Finding | Disposition |
|---|---|---|
| A1 | Phase 6 soak required scheduled autonomous cycles, but no gate authorized a scheduled shadow run | Added the Session 2 shadow-scheduler activation gate; the soak runs under the shadow scheduler with no manual runs (§0, §14.4, §15.1, §19 Phases 4 and 6) |
| A2 | No scan between 6:15 a.m. and 4:30 p.m. could detect day-of live links for after-close Watch-live events | Added targeted T-60/T-15 link checks bounded to watched events (§7.1, §8.4) |
| A3 | Independent Claude Code audit mandate conflicted with the §24 recommendation field and existing harness conventions | Audits now follow harness conventions — Codex per packet, Fable at phase end, reconciled before merge; §24 field replaced (§0, §19, §24) |
| B1 | Nasdaq calendar endpoint is undocumented, violating §10.4's own source rule | Demoted to manual reference only (§10.4, §25) |
| B2 | `changed`/`cancelled` overloaded the schedule-confidence enum with event-status concerns | Removed from the enum; tracked in event status and change history (§8.4) |
| B3 | "Substantive" in the P0 rule was non-deterministic | Operationalized via format class or duration threshold, default 5 minutes, finalized in Phase 0 (§8.3) |
| B4 | §21.7 lacked the officially-announced-by-T-1 qualifier used in Phase 6 acceptance | Aligned (§21) |
| B5 | Role-based watches (Fed Chair, Treasury, SEC, CFTC) were not coverable by the launch allowlist | Added official government/central-bank channel candidates and a coverage-limit statement (§10.3) |
| B6 | The ChatGPT synthesis instruction template was referenced but never defined | Made an explicit, versioned Packet 5A deliverable (§19) |
| B7 | YouTube API data-retention rules may constrain the 90-day appearance history | Added a compliance requirement and Phase 0 evaluation item (§10.4, §23) |
| — | Execution model | Human gates batched into three sessions plus asynchronous merge acknowledgments; Packet 0C live probe and golden fixtures added so the engine builds against real-shaped data (§0, §19) |

---

### 26.2 Revision 1.2 — 2026-07-14 second independent audit dispositions

All 24 findings accepted; R2-14, R2-17, and R2-24 accepted with modification.

| Ref | Finding | Disposition |
|---|---|---|
| R2-01 | Session 1 "closed Phase 0" while Packet 0C remained a post-Session-1 Phase 0 packet | Session 1 closes 0A–0B and authorizes 0C; Phase 0 closes after 0C, audit reconciliation, and merge ack (§0, §19) |
| R2-02 | "Live model/API calls" gate overlapped S1-authorized source API requests | Gate reworded to live generative-model inference calls; safety assertions aligned (§0, §20.4) |
| R2-03 | Production-database gate had no session designation | Phase 0 names dev/shadow/production paths; S1 authorizes shadow only; production at S3 (§0, §19 0B) |
| R2-04 | Threshold authority contradictory across Phase 0, Phase 2, and Session 2 | Policy thresholds fixed in Phase 0; empirical thresholds provisional until Session 2 approval (§0, §8.3, §19) |
| R2-05 | "All six major phases" vs. seven defined phases | Corrected to seven (§21) |
| R2-06 | Event lifecycle mixed decision and queue states into event status | Three separate state machines with published transition tables (§8.4, §19 1A) |
| R2-07 | Tonight-placement ambiguity; unbounded candidate surface | Explicit Watch required for Tonight; per-lane and total candidate caps; pinned items count toward Saved cap (§12.1) |
| R2-08 | Estimated events vs. T-1 visibility; schema over-required start/end and fiscal period | Confirmed-only T-1; time-precision indicator, optional start/end, nullable fiscal period; T-minus checks require exact start time (§7.1, §8.4, §12.2, §13.3) |
| R2-09 | "Materially changed" undefined | Versioned material-change taxonomy with per-class tests (§8.4, §20) |
| R2-10 | Broad person-search provider and "configured" roles unowned | Added to S1 bundle and Packet 2B; launch role appendix mandated (§0, §8.3, §19) |
| R2-11 | Precision without recall; no ground-truth procedure | Frozen stratified ground-truth sample; precision, recall, leakage, sample size reported by lane; Session 2 approves thresholds (§18, §19) |
| R2-12 | Empty state asserted absence contrary to coverage honesty | Coverage-qualified wording with failed-source counts (§12.3) |
| R2-13 | Absolute dedup claims undeliverable from metadata alone | Suppression only on documented deterministic evidence; suspected_duplicate class; completeness claims removed; leakage measured (§11.4) |
| R2-14 | YouTube API derived-data prohibition conflicts with classification design | Modified: converted to mandated Phase 0 decision D-YT with three options (RSS-first default, third-party search, documented deviation), approved at Session 1 — no compliance-acceptance process exists for unaudited single-user clients (§10.4) |
| R2-15 | Golden fixtures conflicted with 30-day metadata refresh obligations | Synthetic fixtures; TTL-controlled metadata cache with lifecycle tests; audit history excludes provider display metadata (§10.4, §13.4, §19 0C, §20.2) |
| R2-16 | No worst-case quota budget | Phase 0 quota budget covering roster, aliases, pagination, overlap, retries, manual scans, soak; RSS/playlist polling preferred; quota-extension gate (§10.4, §19 0B) |
| R2-17 | S1 approved licensing posture, not entitlement evidence | Modified: provider entitlement artifacts required at Session 1; FMP link-only absent evidence — noting display restrictions chiefly target third-party redistribution (§0, §10.4) |
| R2-18 | LaunchAgent semantics incompatible with fixed times and per-event checks | Due-work dispatcher contract: RunAtLoad plus fixed interval, local due-work table, America/Chicago deadlines, declared and tested operating conditions (§15.1, §19 4A, §20.2) |
| R2-19 | Notification sequencing inverted; no production smoke test | Phase 3 emits intents to a fake sink; Phase 4 validates in a staging context; Session 3 split into smoke test then activation (§0, §19) |
| R2-20 | Named-endpoints scope broke on unknown webcast vendor domains | Approved vendor-domain list and bounded redirect rules in the S1 bundle; unknown destinations quarantined as Link pending (§0, §8.4, §16.2) |
| R2-21 | Active-thesis source and matching grammar unspecified before Session 3 | Phase 0 names the local thesis snapshot and deterministic matching grammar (§11.5, §19 0B) |
| R2-22 | Fallback pages counted as link success; no live/replay threshold | Three separate metrics with fixed denominators and Session 2-approved thresholds (§18.1, §19 Phase 6) |
| R2-23 | Soak window not guaranteed to contain two events; healthy-cycle undefined under outage | Session 2 soak plan names a qualifying window and extends until both events complete; degraded-cycle counting defined (§19 6A) |
| R2-24 | Test matrix gaps | Modified scope: cancellation, replay-never-published, and DB corruption already existed in §17.1 but were unmapped to tests; added those mappings plus credential revocation, schema drift/pagination, stale-lock recovery, permission denial, group merge/split decision preservation, and cache lifecycle tests (§17.1, §20.2) |

---

### 26.3 Revision 1.3 — 2026-07-14 follow-up audit dispositions

All five findings accepted.

| Ref | Finding | Disposition |
|---|---|---|
| R3-01 | D-YT "documented deviation" left a knowingly non-compliant implementation authorized by the PRD | Reclassified as a rejected alternative that cannot satisfy launch acceptance; launch restricted to options 1–2, with the ADR demonstrating per-source classification rights and display-only fallback (§10.4) |
| R3-02 | Phase 6 acceptance depended on a smoke test occurring inside the session that closes Phase 6 | Session 3 defined as three ordered steps; Phase 6 acceptance split into pre-activation acceptance (before Session 3) and activation acceptance (inside Session 3) (§0, §19) |
| R3-03 | Media and event schemas lacked the queue-visibility field required by the three-track model | Added queue visibility state to §13.2 and §13.3 |
| R3-04 | Frozen ground-truth sample could be flawed with no review before tuning | Sample and construction procedure Codex-reviewed and human-acknowledged before threshold tuning (§19 2C) |
| R3-05 | Dispatcher interval unbounded | Bounded range 1–15 minutes (default 5), justified in the Phase 0 scheduler ADR and quota budget (§15.1) |

---

*End of amendment. Revision 1.3.*
