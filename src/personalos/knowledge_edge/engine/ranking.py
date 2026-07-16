"""Deterministic ranking (amendment §11.5) and queue-section/cap assignment
(amendment §12.1/§12.2, as far as Packet 1B's scan-time scope reaches).

Pure functions only: no I/O, no clock reads -- every function that cares about
"now" takes it as an explicit ``datetime`` argument (never ``datetime.now()``), so
identical inputs always produce identical scores, explanations, and queue-section
assignments (the Phase 1 determinism requirement).

## Scope note: caps split between this packet (1B) and the decision/CLI surface (1C/1D)

Per ``PHASE0_PLAN.md``'s packet table, §12.1's *Tonight cap* (3 items / 90 known-
duration minutes: ``TONIGHT_ITEM_CAP``/``TONIGHT_KNOWN_DURATION_CAP_SECONDS`` below)
and *Saved cap* (``SAVED_CAP``) are triggered by explicit user Watch/Save decisions
and are enforced at decision-acceptance time -- ``cli/knowledge_edge.py``'s
``decide watch``/``decide save`` handlers (P-KE-1D; P-KE-1C had shipped no
decision-acceptance surface at all, so these two caps had zero enforcement anywhere
driveable until P-KE-1D closed that as phase-end-checkpoint condition C1). What
Packet 1B computes here, once per scan run independent of any UI, is:

- the per-lane **and total** candidate caps (§12.1: "bounded by configurable
  per-lane and total candidate caps") that bound how many ranked candidates are
  promoted into today's ``queue_snapshot`` for the P1/P2 sections -- the per-lane
  cap is applied first within each lane, then the combined P1+P2 survivors are
  trimmed again to the total cap by priority_score across both lanes (so a strong
  P2 item can out-rank a weak P1 item for a shared slot) -- with P0 always fully
  promoted (never dropped, only visually collapsed beyond the cap -- §12.1's own
  "qualifying P0 items beyond the candidate caps remain visible in a collapsed
  ... section rather than being lost");
- the Saved-to-Reconsider **resurfacing** cap (at most 2 saved items included in a
  given day's snapshot);
- the pure ``is_saved_item_expired``/``is_replay_item_expired`` predicates (14-day/
  7-day, pinned items exempt) -- ``scan_orchestrator.run_scan``'s
  ``_sweep_expired_decisions`` is these predicates' production caller (P-KE-1D;
  previously unit-tested only, per checkpoint condition C1).

`PHASE0_PLAN.md`/the amendment both state the per-lane/total candidate cap has "a
default set in Phase 0," but no Phase 0 document actually records that numeric
default anywhere this packet could find (grepped every ``docs/knowledge_edge/*.md``
file). The ``PROVISIONAL_*_CANDIDATE_CAP`` constants below are this packet's own
placeholder, clearly not a Session 1/2-approved value -- flagged in the Packet 1B
handoff as a planning gap for a human/Phase-0-addendum decision, not silently
treated as authoritative.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from personalos.knowledge_edge.engine.matching import TopicMatch

DIRECTNESS_WEIGHTS: Mapping[str, float] = {
    "direct_primary": 100.0,
    "panel_participant": 85.0,
    "direct_secondary_upload": 70.0,
    "ambiguous": 20.0,
    "host_or_interviewer": 40.0,
    "mentioned_only": 10.0,
    "commentary_about": 5.0,
}

SOURCE_PRECEDENCE_WEIGHTS: Mapping[str, float] = {
    "official": 50.0,
    "regulator_exchange": 45.0,
    "approved_structured_provider": 35.0,
    "reputable_secondary": 20.0,
    "broad_search": 5.0,
}

# Company "tier" per the current seeded roster taxonomy (D-PO-019): confirmed
# nasdaq100/crypto-native groups outrank the unresolved wgmi candidate pool.
COMPANY_ROSTER_GROUP_WEIGHTS: Mapping[str, float] = {
    "nasdaq100_top10": 30.0,
    "crypto_native_top3": 30.0,
    "wgmi_candidate_pool": 10.0,
}

THESIS_ENTITY_MATCH_BONUS = 40.0
THESIS_KEYWORD_MATCH_BONUS = 15.0
THESIS_EXTRA_TOPIC_BONUS = 5.0
THESIS_EXTRA_TOPIC_BONUS_CAP = 15.0

RECENCY_TIERS_HOURS: tuple[tuple[float, float], ...] = (
    (24.0, 30.0),
    (72.0, 15.0),
    (336.0, 5.0),  # 14 days
)

DURATION_PENALTY_FREE_MINUTES = 20.0
DURATION_PENALTY_PER_10_MINUTES = 1.0
DURATION_PENALTY_CAP = 20.0

SUSPECTED_DUPLICATE_PENALTY = 25.0
PRIOR_SKIP_PENALTY = 1000.0
PINNED_BONUS = 1000.0

# Phase-0-planning-gap placeholders -- see module docstring.
PROVISIONAL_PER_LANE_CANDIDATE_CAP = 5
PROVISIONAL_TOTAL_P1_P2_CANDIDATE_CAP = 12

SAVED_CAP = 12
SAVED_EXPIRY_DAYS = 14
SAVED_RESURFACE_MAX_PER_DAY = 2
EARNINGS_REPLAY_EXPIRY_DAYS = 7
RECOMMENDED_WATCH_LIVE_PER_DAY = 2  # advisory only, per §12.2 -- never hides additional calls.

# §12.1 Tonight caps, enforced at decision-acceptance time (C1, phase-end checkpoint
# 2026-07-16 -- see cli/knowledge_edge.py's ``decide watch`` handler, the first
# production caller). TONIGHT_ITEM_CAP is a hard count of active (decision_state
# == "watch") media items; TONIGHT_KNOWN_DURATION_CAP_SECONDS bounds only the
# known-duration subset (an unknown-duration item never contributes to the minutes
# sum, since there is nothing to sum) -- both are refused, not silently trimmed.
TONIGHT_ITEM_CAP = 3
TONIGHT_KNOWN_DURATION_CAP_SECONDS = 90 * 60


@dataclass(frozen=True)
class RankingResult:
    score: float
    explanation: str


def _topic_bonus(topic_matches: Sequence[TopicMatch]) -> tuple[float, str]:
    if not topic_matches:
        return 0.0, ""
    strongest_by_topic: dict[str, str] = {}
    for match in topic_matches:
        current = strongest_by_topic.get(match.topic_id)
        if current is None or (current != "entity" and match.strength == "entity"):
            strongest_by_topic[match.topic_id] = match.strength
    base = max(
        THESIS_ENTITY_MATCH_BONUS if strength == "entity" else THESIS_KEYWORD_MATCH_BONUS
        for strength in strongest_by_topic.values()
    )
    extra_topics = len(strongest_by_topic) - 1
    extra_bonus = min(THESIS_EXTRA_TOPIC_BONUS_CAP, extra_topics * THESIS_EXTRA_TOPIC_BONUS)
    leading_topic_id = min(
        strongest_by_topic, key=lambda topic_id: (strongest_by_topic[topic_id] != "entity", topic_id)
    )
    return base + extra_bonus, f"topic={leading_topic_id} ({strongest_by_topic[leading_topic_id]})"


def _recency_bonus(*, published_at: str | None, now: datetime) -> tuple[float, str]:
    if published_at is None:
        return 0.0, "recency unknown"
    published = datetime.fromisoformat(published_at)
    hours_since = max(0.0, (now - published).total_seconds() / 3600.0)
    for threshold_hours, bonus in RECENCY_TIERS_HOURS:
        if hours_since <= threshold_hours:
            return bonus, f"published {hours_since:.1f}h ago"
    return 0.0, f"published {hours_since:.1f}h ago (stale)"


def _duration_penalty(duration_seconds: int | None) -> tuple[float, str]:
    if duration_seconds is None:
        return 0.0, ""
    minutes = duration_seconds / 60.0
    if minutes <= DURATION_PENALTY_FREE_MINUTES:
        return 0.0, f"duration {minutes:.0f}m"
    over_minutes = minutes - DURATION_PENALTY_FREE_MINUTES
    penalty = min(DURATION_PENALTY_CAP, (over_minutes / 10.0) * DURATION_PENALTY_PER_10_MINUTES)
    return -penalty, f"duration {minutes:.0f}m (time-cost penalty)"


def compute_priority_score(
    *,
    directness_class: str,
    source_precedence: str,
    company_roster_group: str | None,
    topic_matches: Sequence[TopicMatch],
    published_at: str | None,
    now: datetime,
    duration_seconds: int | None,
    is_suspected_duplicate: bool,
    pinned: bool,
    prior_decision_state: str | None,
) -> RankingResult:
    """Compute a deterministic priority score and its human-readable explanation.

    Higher is more prioritized. Pinned items and prior-skip items short-circuit to
    fixed extremes (never re-derived from the rest of the formula) so their
    ordering behavior is trivially auditable.
    """
    if prior_decision_state == "skip":
        return RankingResult(score=-PRIOR_SKIP_PENALTY, explanation="prior decision: skip")
    if pinned:
        return RankingResult(score=PINNED_BONUS, explanation="pinned")

    parts: list[str] = []
    score = 0.0

    directness_weight = DIRECTNESS_WEIGHTS.get(directness_class, 0.0)
    score += directness_weight
    parts.append(f"directness={directness_class} (+{directness_weight:.0f})")

    precedence_weight = SOURCE_PRECEDENCE_WEIGHTS.get(source_precedence, 0.0)
    score += precedence_weight
    parts.append(f"source={source_precedence} (+{precedence_weight:.0f})")

    if company_roster_group is not None:
        company_weight = COMPANY_ROSTER_GROUP_WEIGHTS.get(company_roster_group, 0.0)
        if company_weight:
            score += company_weight
            parts.append(f"company_tier={company_roster_group} (+{company_weight:.0f})")

    topic_bonus, topic_note = _topic_bonus(topic_matches)
    if topic_bonus:
        score += topic_bonus
        parts.append(f"{topic_note} (+{topic_bonus:.0f})")

    recency_bonus, recency_note = _recency_bonus(published_at=published_at, now=now)
    if recency_bonus:
        score += recency_bonus
    parts.append(f"{recency_note} (+{recency_bonus:.0f})" if recency_note else recency_note)

    duration_delta, duration_note = _duration_penalty(duration_seconds)
    if duration_delta:
        score += duration_delta
    if duration_note:
        parts.append(f"{duration_note} ({duration_delta:+.0f})" if duration_delta else duration_note)

    if is_suspected_duplicate:
        score -= SUSPECTED_DUPLICATE_PENALTY
        parts.append(f"suspected duplicate (-{SUSPECTED_DUPLICATE_PENALTY:.0f})")

    explanation = "; ".join(part for part in parts if part)
    return RankingResult(score=score, explanation=explanation)


def order_candidates(candidates: Sequence[Mapping]) -> list[Mapping]:
    """Deterministic descending-score order; ties break by ``entity_id`` ascending.

    ``entity_id`` (rather than a timestamp) is the tiebreaker so ordering never
    depends on wall-clock-adjacent fields that could collide.
    """
    return sorted(candidates, key=lambda item: (-item["priority_score"], item["entity_id"]))


def select_promoted(ordered: Sequence[Mapping], *, cap: int | None) -> tuple[list[str], list[str]]:
    """Split an already-ordered candidate list into (promoted, overflow) entity IDs.

    ``cap=None`` promotes everything (used for the P0 section, which is never
    truncated -- only visually collapsed by the 1C dashboard beyond this same cap
    value, which this function reports via the caller-visible overflow list even
    when it does not act on it).
    """
    entity_ids = [item["entity_id"] for item in ordered]
    if cap is None or len(entity_ids) <= cap:
        return entity_ids, []
    return entity_ids[:cap], entity_ids[cap:]


def assign_queue_section(
    *, lane: str, decision_state: str, is_earnings_event: bool = False
) -> str | None:
    """Map an item to one of ``state.decisions.QUEUE_SECTIONS``, or ``None`` if it
    is not a queueable candidate at all (e.g. a suppressed/excluded appearance, or
    an item the user has already decided ``skip``/``watched`` on -- those never
    resurface, §7.3).
    """
    if decision_state in ("skip", "watched"):
        return None
    if decision_state in ("save_for_later", "save_replay"):
        return "saved_to_reconsider"
    if is_earnings_event:
        return "tomorrow_earnings_events"
    return {
        "curated_podcasts": "p1_core_podcasts",
        "consequential_leaders": "p0_consequential_leaders",
        "market_voices": "p2_market_voices",
    }.get(lane)


def is_saved_item_expired(*, decided_at: str, now: datetime, pinned: bool) -> bool:
    if pinned:
        return False
    decided = datetime.fromisoformat(decided_at)
    return (now - decided) > timedelta(days=SAVED_EXPIRY_DAYS)


def is_replay_item_expired(*, ended_at: str, now: datetime, pinned: bool) -> bool:
    if pinned:
        return False
    ended = datetime.fromisoformat(ended_at)
    return (now - ended) > timedelta(days=EARNINGS_REPLAY_EXPIRY_DAYS)


def select_resurfaced_saved_items(
    candidates: Sequence[Mapping], *, max_per_day: int = SAVED_RESURFACE_MAX_PER_DAY
) -> list[str]:
    """Choose which saved items resurface in today's queue (§12.1: "no more than 2
    items in one daily queue" and "not resurfaced every day"). Deterministic
    ordering: highest priority_score first, tiebreak by ``entity_id``.
    """
    ordered = order_candidates(candidates)
    return [item["entity_id"] for item in ordered[:max_per_day]]
