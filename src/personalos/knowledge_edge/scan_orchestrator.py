"""Knowledge Edge scan orchestrator (P-KE-1B).

Composes ``adapters/`` (fixture-only in this packet -- live rails are Phase 2/3),
``engine/`` (pure classification/dedup/ranking logic), and ``state/`` (persistence)
into one idempotent scan-run entrypoint, analogous to ``cli/today.py``'s role for
the morning cycle (AD-1). This is the one module in the package that does I/O and
reads a caller-supplied "now" -- it never calls ``datetime.now()`` itself, so a scan
run's outcome is fully determined by (database state, adapter data, ``now``,
``queue_date``, thesis snapshot).

## Known state-layer (P-KE-1A) API gaps this orchestrator works around or defers

Flagged here (and repeated in the Packet 1B handoff) rather than fixed by editing
``state/`` directly, per this packet's scope boundary:

1. **No update-fields function for already-created media items or scheduled
   events beyond the three state-transition updaters.** ``create_media_item`` and
   ``create_scheduled_event`` accept their classification/ranking/link fields only
   at creation time. This orchestrator therefore computes directness, ranking, and
   (for events) any same-run filing enrichment *before* the row is ever inserted,
   so nothing needs to be corrected afterward -- but it also means: (a) a
   podcast episode's title/description correction on a later scan cannot be
   applied to the existing row (only a new ``discovery_occurrence`` records the
   corrected raw payload for audit purposes); (b) an event discovered before its
   webcast link/confirmed schedule exists cannot later have that link/confidence
   attached once created. (b) is a real Lane D gap for the amendment's own T-0
   refresh requirement (§8.4) -- it is deferred to whichever of P-KE-3B/3C adds
   this update path, since that is where live schedule/link refresh first becomes
   load-bearing.
2. **No query-by-natural-key helper for cross-scan-run dedup evidence.** Only
   ``get_media_item_by_dedupe_key`` exists; there is no persisted ``feed_guid``/
   ``underlying_id`` column on ``ke_media_items`` and no "list all recent
   occurrences" helper. Deterministic dedup evidence (§11.4) is therefore only
   evaluated *within* a single scan run's freshly-fetched batch here, not across
   separate runs (e.g. a stale repost surfacing two weeks after the original would
   not be caught by this packet). This is a real limitation, not an oversight;
   flagged for a follow-up packet to consider adding those columns + lookups.
3. **Filings only enrich an event created in the same scan run.** Since events
   cannot be updated after creation (gap 1), a filing discovered in a later run
   than its event cannot be attached at all in this packet. Both adapters run in
   the same scan for this reason and filings are matched to events before either
   is persisted.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import personalos.knowledge_edge.state as ke
from personalos.idempotency import stable_side_effect_id
from personalos.knowledge_edge.adapters.contracts import (
    AdapterFetchResult,
    ChannelVideoAdapter,
    DiscoveredEvent,
    DiscoveredFiling,
    DiscoveredMediaItem,
    EarningsEventAdapter,
    FilingsAdapter,
    PodcastFeedAdapter,
)
from personalos.knowledge_edge.engine import canonicalize, dedup, directness, matching, ranking

# Source types this packet's four contracts cover, and which fetch method handles
# each. ir_page/person_search_provider/manual_link sources exist in the schema's
# SOURCE_TYPES but have no fixture contract in Packet 1B and are skipped (not
# failed) here -- they are Phase 2/3 territory (person_search deferred per
# PHASE0_PROVIDERS_AND_ACCESS.md §3; ir_page/manual_link are enrichment sources
# with no adapter contract named for this packet).
_MEDIA_SOURCE_TYPES = frozenset({"podcast_feed", "youtube_channel", "network_program"})
_EVENT_SOURCE_TYPES = frozenset({"calendar_provider"})
_FILING_SOURCE_TYPES = frozenset({"sec_edgar"})

_QUEUEABLE_EVENT_STATUSES = frozenset(
    {"confirmed", "scheduled", "live", "ended", "replay_pending", "replay_available"}
)


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat()


def _sid(prefix: str, *parts: str) -> str:
    return stable_side_effect_id(prefix, ":".join(parts))


@dataclass(frozen=True)
class ScanSummary:
    scan_run_id: str
    status: str
    media_items_created: int
    media_items_reprocessed: int
    events_created: int
    events_reprocessed: int
    sources_healthy: int
    sources_failed: int
    queue_snapshot_rows_created: int


def run_scan(
    connection,
    *,
    scan_run_id: str,
    run_type: str,
    triggered_by: str,
    now: datetime,
    queue_date: str,
    podcast_adapter: PodcastFeedAdapter,
    channel_adapter: ChannelVideoAdapter,
    earnings_adapter: EarningsEventAdapter,
    filings_adapter: FilingsAdapter,
    theses: Sequence[Mapping] = (),
) -> ScanSummary:
    """Run one full, idempotent Knowledge Edge scan against fixture adapters.

    Re-running this with the same database state, adapter data, and ``now``
    produces no new media/event rows (only, at most, new audit-trail
    ``discovery_occurrence`` rows) and no duplicate ``queue_snapshot`` rows --
    the Phase 1 idempotency requirement (§11.1).
    """
    ke.create_scan_run(connection, scan_run_id=scan_run_id, run_type=run_type, triggered_by=triggered_by, started_at=_iso(now))

    media_created = 0
    media_reprocessed = 0
    events_created = 0
    events_reprocessed = 0
    sources_healthy = 0
    sources_failed = 0

    sources = ke.list_sources(connection, status="active")
    event_records: list[tuple[Mapping, DiscoveredEvent]] = []
    filing_records: list[DiscoveredFiling] = []

    for source in sources:
        source_type = source["source_type"]
        source_id = source["source_id"]
        cursor = ke.get_scan_cursor(connection, source_id=source_id)
        cursor_value = cursor["last_successful_cursor_value"] if cursor else None

        if source_type in _MEDIA_SOURCE_TYPES:
            fetch = podcast_adapter.fetch_episodes if source_type == "podcast_feed" else channel_adapter.fetch_uploads
            result = fetch(source_id=source_id, cursor=cursor_value, now=now)
            healthy = _record_source_health(connection, source=source, result=result, scan_run_id=scan_run_id, now=now)
            if not healthy:
                sources_failed += 1
                continue
            sources_healthy += 1
            created, reprocessed = _persist_media_batch(
                connection,
                source=source,
                items=result.items,
                scan_run_id=scan_run_id,
                now=now,
                theses=theses,
            )
            media_created += created
            media_reprocessed += reprocessed
            _advance_cursor(connection, source_id=source_id, result=result, now=now)

        elif source_type in _EVENT_SOURCE_TYPES:
            result = earnings_adapter.fetch_events(source_id=source_id, cursor=cursor_value, now=now)
            healthy = _record_source_health(connection, source=source, result=result, scan_run_id=scan_run_id, now=now)
            if not healthy:
                sources_failed += 1
                continue
            sources_healthy += 1
            event_records.extend((source, item) for item in result.items)
            _advance_cursor(connection, source_id=source_id, result=result, now=now)

        elif source_type in _FILING_SOURCE_TYPES:
            result = filings_adapter.fetch_filings(source_id=source_id, cursor=cursor_value, now=now)
            healthy = _record_source_health(connection, source=source, result=result, scan_run_id=scan_run_id, now=now)
            if not healthy:
                sources_failed += 1
                continue
            sources_healthy += 1
            filing_records.extend(result.items)
            _advance_cursor(connection, source_id=source_id, result=result, now=now)
        # else: source_type not modeled by this packet's adapter contracts; skipped.

    events_created, events_reprocessed = _persist_events(
        connection, event_records=event_records, filing_records=filing_records, scan_run_id=scan_run_id, now=now
    )

    _advance_event_lifecycles(connection, now=now)

    queue_rows = _build_and_record_queue(connection, queue_date=queue_date, now=now, theses=theses)

    _record_coverage_report(connection, scan_run_id=scan_run_id, queue_date=queue_date, sources=sources)

    ke.complete_scan_run(
        connection,
        scan_run_id=scan_run_id,
        status="completed" if sources_failed == 0 else "partially_completed",
        completed_at=_iso(now),
        summary={
            "media_items_created": media_created,
            "media_items_reprocessed": media_reprocessed,
            "events_created": events_created,
            "events_reprocessed": events_reprocessed,
            "sources_healthy": sources_healthy,
            "sources_failed": sources_failed,
        },
    )

    return ScanSummary(
        scan_run_id=scan_run_id,
        status="completed" if sources_failed == 0 else "partially_completed",
        media_items_created=media_created,
        media_items_reprocessed=media_reprocessed,
        events_created=events_created,
        events_reprocessed=events_reprocessed,
        sources_healthy=sources_healthy,
        sources_failed=sources_failed,
        queue_snapshot_rows_created=queue_rows,
    )


def _record_source_health(
    connection, *, source: Mapping, result: AdapterFetchResult, scan_run_id: str, now: datetime
) -> bool:
    source_id = source["source_id"]
    health_id = _sid("health", source_id)
    existing = ke.get_source_health(connection, source_id=source_id)
    if result.healthy:
        ke.upsert_source_health(
            connection,
            health_id=health_id,
            source_id=source_id,
            status="healthy",
            scan_run_id=scan_run_id,
            last_success_at=_iso(now),
            consecutive_failure_count=0,
        )
        return True
    prior_failures = existing["consecutive_failure_count"] if existing else 0
    ke.upsert_source_health(
        connection,
        health_id=health_id,
        source_id=source_id,
        status="failed",
        scan_run_id=scan_run_id,
        last_failure_at=_iso(now),
        consecutive_failure_count=prior_failures + 1,
        last_error_summary=result.error_summary or "",
    )
    return False


def _advance_cursor(connection, *, source_id: str, result: AdapterFetchResult, now: datetime) -> None:
    if result.next_cursor_value is None:
        return
    ke.advance_scan_cursor(
        connection,
        cursor_id=_sid("cursor", source_id),
        source_id=source_id,
        last_successful_cursor_value=result.next_cursor_value,
        last_successful_at=_iso(now),
    )


def _candidate_dict_for_dedup(dedupe_key: str, item: DiscoveredMediaItem) -> dict:
    return {
        "media_item_id": dedupe_key,  # surrogate identifier; see engine.dedup docstring.
        "dedupe_key": dedupe_key,
        "feed_guid": item.feed_guid,
        "underlying_id": item.underlying_id,
        "is_replay_of_underlying_id": item.is_replay_of_underlying_id,
        "title": item.title,
        "matched_person_id": item.matched_person_id,
        "published_at": item.published_at,
    }


def _persist_media_batch(
    connection,
    *,
    source: Mapping,
    items: Sequence[DiscoveredMediaItem],
    scan_run_id: str,
    now: datetime,
    theses: Sequence[Mapping],
) -> tuple[int, int]:
    source_id = source["source_id"]
    lane = source["lane"]

    new_items: list[tuple[str, DiscoveredMediaItem]] = []
    reprocessed = 0
    for item in items:
        dedupe_key = canonicalize.build_dedupe_key(source_id=item.source_id, stable_id=item.source_specific_id)
        existing = ke.get_media_item_by_dedupe_key(connection, dedupe_key)
        if existing is not None:
            ke.create_discovery_occurrence(
                connection,
                occurrence_id=_sid("occ", existing["media_item_id"], scan_run_id, item.source_specific_id),
                media_item_id=existing["media_item_id"],
                source_id=source_id,
                scan_run_id=scan_run_id,
                discovered_at=_iso(now),
                raw_payload_summary=dict(item.raw_payload_summary),
            )
            reprocessed += 1
            continue
        new_items.append((dedupe_key, item))

    new_items.sort(key=lambda pair: pair[0])
    groups, group_of, rule_of = _group_duplicates(new_items)

    created = 0
    for index, (dedupe_key, item) in enumerate(new_items):
        group = groups[group_of[index]]
        canonical_group_id = None
        is_canonical = True
        if len(group) > 1:
            group_dedupe_keys = sorted(new_items[member][0] for member in group)
            canonical_group_id = _sid("cgrp", *group_dedupe_keys)
            if not ke.list_canonical_group_members(connection, canonical_group_id=canonical_group_id):
                ke.create_canonical_group(
                    connection,
                    canonical_group_id=canonical_group_id,
                    dedupe_rule=rule_of.get(index, "manual"),
                )
            is_canonical = index == group[0]

        suspected_reason = None
        if canonical_group_id is None:
            candidates_before = [_candidate_dict_for_dedup(dk, other) for dk, other in new_items[:index]]
            suspected_reason = dedup.find_suspected_duplicate(
                new_item=_candidate_dict_for_dedup(dedupe_key, item), existing_items=candidates_before
            )

        directness_class = directness.classify_directness(
            format_hint=item.format_hint, duration_seconds=item.duration_seconds
        )
        is_substantive, substantive_reason = directness.classify_substantive_appearance(
            format_hint=item.format_hint,
            directness_class=directness_class,
            duration_seconds=item.duration_seconds,
        )
        person_ids = [item.matched_person_id] if item.matched_person_id else []
        topic_matches = matching.match_topics(
            company_id=item.matched_company_id,
            person_ids=person_ids,
            title=item.title,
            description=item.description_excerpt,
            theses=theses,
        )
        company = ke.get_company(connection, item.matched_company_id) if item.matched_company_id else None
        ranking_result = ranking.compute_priority_score(
            directness_class=directness_class,
            source_precedence=item.source_precedence,
            company_roster_group=company["roster_group"] if company else None,
            topic_matches=topic_matches,
            published_at=item.published_at,
            now=now,
            duration_seconds=item.duration_seconds,
            is_suspected_duplicate=suspected_reason is not None,
            pinned=False,
            prior_decision_state=None,
        )
        explanation = ranking_result.explanation
        if not is_substantive:
            explanation = f"{explanation}; not substantive ({substantive_reason})"

        media_item_id = _sid("media", dedupe_key)
        confidences = [1.0 for value in (item.matched_person_id, item.matched_role_id, item.matched_company_id) if value]
        media_item = ke.create_media_item(
            connection,
            media_item_id=media_item_id,
            source_id=source_id,
            source_specific_id=item.source_specific_id,
            canonical_url=canonicalize.normalize_url(item.canonical_url),
            alternate_urls=[canonicalize.normalize_url(url) for url in item.alternate_urls],
            title=item.title,
            description_excerpt=item.description_excerpt,
            source_precedence=item.source_precedence,
            media_type=item.media_type,
            dedupe_key=dedupe_key,
            published_at=item.published_at,
            discovered_at=_iso(now),
            duration_seconds=canonicalize.normalize_duration_seconds(item.duration_seconds),
            directness_class=directness_class,
            match_confidence=max(confidences) if confidences else None,
            priority_score=ranking_result.score,
            priority_explanation=explanation,
            canonical_group_id=canonical_group_id,
            is_canonical=is_canonical,
            coverage_notes=suspected_reason or "",
        )
        created += 1

        for entity_type, entity_id in (
            ("person", item.matched_person_id),
            ("role", item.matched_role_id),
            ("company", item.matched_company_id),
        ):
            if entity_id is None:
                continue
            ke.create_entity_match(
                connection,
                entity_match_id=_sid("match", media_item_id, entity_type, entity_id),
                target_type="media_item",
                target_id=media_item_id,
                matched_entity_type=entity_type,
                matched_entity_id=entity_id,
                match_method="exact_alias",
                confidence=1.0,
                reason=f"adapter-declared {entity_type} match",
            )

        ke.create_discovery_occurrence(
            connection,
            occurrence_id=_sid("occ", media_item_id, scan_run_id, item.source_specific_id),
            media_item_id=media_item_id,
            source_id=source_id,
            scan_run_id=scan_run_id,
            discovered_at=_iso(now),
            raw_payload_summary=dict(item.raw_payload_summary),
        )

        ke.update_media_content_status(connection, media_item_id=media_item_id, content_status="normalized")
        ke.update_media_content_status(connection, media_item_id=media_item_id, content_status="ranked")

        # §8.3: "ambiguous" (unknown-duration financial-media segment) must never be
        # silently dropped -- it stays a visible, demoted candidate (its low
        # directness weight already ranks it below qualifying appearances). Only
        # genuinely non-eligible directness classes (commentary_about,
        # mentioned_only, host_or_interviewer) and explicitly excluded formats are
        # suppressed from the Market Voices / Consequential Leaders lanes.
        if canonical_group_id is not None and not is_canonical:
            ke.update_media_queue_visibility(connection, media_item_id=media_item_id, queue_visibility_state="suppressed")
        elif (
            not is_substantive
            and directness_class != "ambiguous"
            and lane in ("market_voices", "consequential_leaders")
        ):
            ke.update_media_queue_visibility(connection, media_item_id=media_item_id, queue_visibility_state="suppressed")

    return created, reprocessed


def _group_duplicates(
    new_items: Sequence[tuple[str, DiscoveredMediaItem]],
) -> tuple[list[list[int]], dict[int, int], dict[int, str]]:
    """Group same-batch new items into deterministic-evidence duplicate clusters.

    Returns ``(groups, group_of_index, dedupe_rule_of_index)``. ``groups[i]`` is a
    list of indices into ``new_items``, in first-seen order; ``group_of_index[i]``
    maps an item's index to which group it landed in.
    """
    groups: list[list[int]] = []
    group_of: dict[int, int] = {}
    rule_of: dict[int, str] = {}
    candidates_so_far: list[dict] = []

    for index, (dedupe_key, item) in enumerate(new_items):
        candidate = _candidate_dict_for_dedup(dedupe_key, item)
        evidence = dedup.find_duplicate_evidence(new_item=candidate, existing_items=candidates_so_far)
        if evidence is not None:
            existing_index = next(
                i for i, (dk, _) in enumerate(new_items[:index]) if dk == evidence.existing_media_item_id
            )
            group_id = group_of[existing_index]
            group_of[index] = group_id
            groups[group_id].append(index)
            rule_of[group_id] = evidence.rule
        else:
            group_id = len(groups)
            groups.append([index])
            group_of[index] = group_id
        candidates_so_far.append(candidate)

    return groups, group_of, rule_of


def _persist_events(
    connection,
    *,
    event_records: Sequence[tuple[Mapping, DiscoveredEvent]],
    filing_records: Sequence[DiscoveredFiling],
    scan_run_id: str,
    now: datetime,
) -> tuple[int, int]:
    created = 0
    reprocessed = 0
    for source, item in event_records:
        event_id = f"event-{item.company_id}-{item.event_id_hint}"
        existing = ke.get_scheduled_event(connection, event_id)
        if existing is not None:
            reprocessed += 1
            continue

        merged_filing_urls = list(item.filing_urls)
        for filing in filing_records:
            if filing.company_id != item.company_id:
                continue
            if filing.fiscal_period is not None and item.fiscal_period is not None:
                if filing.fiscal_period != item.fiscal_period:
                    continue
            if filing.filing_url not in merged_filing_urls:
                merged_filing_urls.append(filing.filing_url)

        ke.create_scheduled_event(
            connection,
            event_id=event_id,
            company_id=item.company_id,
            event_type=item.event_type,
            scheduled_date=item.scheduled_date,
            fiscal_period=item.fiscal_period,
            start_time_utc=item.start_time_utc,
            end_time_utc=item.end_time_utc,
            time_precision=item.time_precision,
            source_timezone=item.source_timezone,
            timing_label=item.timing_label,
            schedule_confidence=item.schedule_confidence,
            schedule_source=item.schedule_source,
            official_event_page_url=item.official_event_page_url,
            live_webcast_url=item.live_webcast_url,
            replay_url=item.replay_url,
            earnings_release_url=item.earnings_release_url,
            filing_urls=merged_filing_urls,
            slides_url=item.slides_url,
            shareholder_letter_url=item.shareholder_letter_url,
            prepared_remarks_url=item.prepared_remarks_url,
        )
        created += 1

    return created, reprocessed


def _advance_event_lifecycles(connection, *, now: datetime) -> None:
    """Deterministically progress each open event's status track based on ``now``
    vs. its own scheduled/start/end times (amendment §8.4's T-1/T-0/T+1 lifecycle).
    Never reads the wall clock; ``now`` is the only time input.
    """
    for event in ke.list_scheduled_events(connection):
        status = event["event_status"]
        if status in ("cancelled", "archived"):
            continue
        target = _next_event_status(event, now=now)
        if target is not None and target != status:
            ke.update_event_status(connection, event_id=event["event_id"], event_status=target)


def _next_event_status(event: Mapping, *, now: datetime) -> str | None:
    status = event["event_status"]
    scheduled_date = datetime.fromisoformat(event["scheduled_date"]).date()
    today = now.date()

    if status in ("discovered", "tentative") and event["schedule_confidence"] in (
        "confirmed_official",
        "confirmed_secondary",
    ):
        return "confirmed"
    if status == "confirmed" and scheduled_date <= today:
        return "scheduled"
    if status == "scheduled":
        start = event["start_time_utc"]
        if start is not None and now >= datetime.fromisoformat(start):
            return "live"
        if start is None and scheduled_date < today:
            return "live"
    if status == "live":
        end = event["end_time_utc"]
        if end is not None and now >= datetime.fromisoformat(end):
            return "ended"
        if end is None:
            return "ended"
    if status == "ended":
        return "replay_pending"
    if status == "replay_pending" and event["replay_url"]:
        return "replay_available"
    return None


def _build_and_record_queue(
    connection, *, queue_date: str, now: datetime, theses: Sequence[Mapping]
) -> int:
    rows_created = 0

    known_lanes = {"curated_podcasts", "market_voices", "consequential_leaders"}
    media_by_section: dict[str, list[dict]] = {
        "p1_core_podcasts": [],
        "p2_market_voices": [],
        "p0_consequential_leaders": [],
    }
    for state in ("candidate", "queued"):
        for item in ke.list_media_items(connection, queue_visibility_state=state):
            source = ke.get_source(connection, item["source_id"])
            if source is None or source["lane"] not in known_lanes:
                continue
            decision = ke.get_user_decision(connection, entity_type="media_item", entity_id=item["media_item_id"])
            decision_state = decision["decision_state"] if decision else "undecided"
            section = ranking.assign_queue_section(lane=source["lane"], decision_state=decision_state)
            # save_for_later items are gathered separately below (they need
            # resurfacing/expiry policy, not per-lane candidate-cap ranking); skip
            # them here rather than build an unused bucket.
            if section not in media_by_section:
                continue
            media_by_section[section].append(
                {"entity_id": item["media_item_id"], "priority_score": item["priority_score"] or 0.0, "row": item}
            )

    section_caps = {
        "p0_consequential_leaders": None,
        "p1_core_podcasts": ranking.PROVISIONAL_PER_LANE_CANDIDATE_CAP,
        "p2_market_voices": ranking.PROVISIONAL_PER_LANE_CANDIDATE_CAP,
    }
    for section in ("p0_consequential_leaders", "p1_core_podcasts", "p2_market_voices"):
        candidates = media_by_section.get(section, [])
        ordered = ranking.order_candidates(candidates)
        promoted, _overflow = ranking.select_promoted(ordered, cap=section_caps[section])
        rows_created += _record_section(
            connection, queue_date=queue_date, section=section, entity_type="media_item", ordered_entity_ids=promoted, items_by_id={c["entity_id"]: c["row"] for c in candidates}
        )

    saved_media = [
        {"entity_id": item["media_item_id"], "priority_score": item["priority_score"] or 0.0, "row": item}
        for item in ke.list_media_items(connection, decision_state="save_for_later")
        if item["queue_visibility_state"] not in ("expired", "archived", "suppressed")
    ]
    resurfaced_ids = ranking.select_resurfaced_saved_items(saved_media)
    rows_created += _record_section(
        connection,
        queue_date=queue_date,
        section="saved_to_reconsider",
        entity_type="media_item",
        ordered_entity_ids=resurfaced_ids,
        items_by_id={c["entity_id"]: c["row"] for c in saved_media},
    )

    earnings_candidates = [
        {
            "entity_id": event["event_id"],
            "priority_score": _event_priority_score(connection, event, theses=theses, now=now),
            "row": event,
        }
        for event in ke.list_scheduled_events(connection)
        if event["event_status"] in _QUEUEABLE_EVENT_STATUSES
        and _event_decision_state(connection, event) not in ("skip", "watched")
    ]
    ordered_events = ranking.order_candidates(earnings_candidates)
    rows_created += _record_section(
        connection,
        queue_date=queue_date,
        section="tomorrow_earnings_events",
        entity_type="scheduled_event",
        ordered_entity_ids=[item["entity_id"] for item in ordered_events],
        items_by_id={c["entity_id"]: c["row"] for c in earnings_candidates},
    )

    return rows_created


def _event_decision_state(connection, event: Mapping) -> str:
    decision = ke.get_user_decision(connection, entity_type="scheduled_event", entity_id=event["event_id"])
    return decision["decision_state"] if decision else "undecided"


def _event_priority_score(connection, event: Mapping, *, theses: Sequence[Mapping], now: datetime) -> float:
    """Lightweight Lane D scoring: company tier + thesis (entity-only, events have
    no title/description text) + schedule confidence + proximity to ``now``.
    Duration/directness/dedup do not apply to scheduled events, so this does not
    reuse :func:`ranking.compute_priority_score` (a media-item-shaped formula).
    """
    company = ke.get_company(connection, event["company_id"])
    company_weight = 0.0
    if company is not None:
        company_weight = ranking.COMPANY_ROSTER_GROUP_WEIGHTS.get(company["roster_group"], 0.0)

    topic_matches = matching.match_topics(
        company_id=event["company_id"], person_ids=(), title="", description="", theses=theses
    )
    topic_bonus = ranking.THESIS_ENTITY_MATCH_BONUS if topic_matches else 0.0

    confidence_weight = {
        "confirmed_official": 50.0,
        "confirmed_secondary": 35.0,
        "estimated": 15.0,
        "unknown": 0.0,
    }.get(event["schedule_confidence"], 0.0)

    scheduled_date = datetime.fromisoformat(event["scheduled_date"]).date()
    days_until = (scheduled_date - now.date()).days
    proximity_bonus = 30.0 if -7 <= days_until <= 1 else max(0.0, 10.0 - abs(days_until))

    return company_weight + topic_bonus + confidence_weight + proximity_bonus


def _record_section(
    connection,
    *,
    queue_date: str,
    section: str,
    entity_type: str,
    ordered_entity_ids: Sequence[str],
    items_by_id: Mapping[str, Mapping],
) -> int:
    existing_rows = ke.list_queue_snapshot(connection, queue_date=queue_date, section=section)
    existing_entity_ids = {row["entity_id"] for row in existing_rows}
    created = 0
    for position, entity_id in enumerate(ordered_entity_ids, start=1):
        if entity_id in existing_entity_ids:
            continue
        row = items_by_id.get(entity_id, {})
        explanation = row.get("priority_explanation", "")
        ke.record_queue_snapshot(
            connection,
            snapshot_id=_sid("qsnap", queue_date, section, entity_type, entity_id),
            queue_date=queue_date,
            section=section,
            entity_type=entity_type,
            entity_id=entity_id,
            rank_position=position,
            explanation=explanation,
        )
        if entity_type == "media_item":
            current_state = row.get("queue_visibility_state")
            if current_state == "candidate":
                ke.update_media_queue_visibility(connection, media_item_id=entity_id, queue_visibility_state="queued")
        created += 1
    return created


def _record_coverage_report(connection, *, scan_run_id: str, queue_date: str, sources: Sequence[Mapping]) -> None:
    healthy = 0
    failed = 0
    for source in sources:
        health = ke.get_source_health(connection, source_id=source["source_id"])
        if health is None:
            continue
        if health["status"] == "healthy":
            healthy += 1
        else:
            failed += 1
    total = healthy + failed
    ke.create_coverage_report(
        connection,
        coverage_report_id=_sid("coverage", scan_run_id, queue_date),
        scan_run_id=scan_run_id,
        report_date=queue_date,
        report={"sources_healthy": healthy, "sources_failed": failed, "sources_total": total},
        overall_summary=(
            f"{healthy}/{total} sources healthy" if total else "no sources configured"
        ),
    )
