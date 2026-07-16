"""Directness classification (amendment §11.3) and the Lane C P0 inclusion rule /
Lane B P2 eligibility gate (§8.3, §8.2).

Pure functions only: no I/O, no clock reads. Every duration/threshold comparison
takes its threshold as an explicit argument (the 5-minute default is provisional
per Phase 0 and finalized at Session 2 -- callers own the actual value in force).

``format_hint`` is the deterministic signal an adapter (or, in a live rail, a
future classifier upstream of this module) reports about *what kind of appearance*
a discovered item is. This module never invents or guesses a format_hint from free
text; it only maps an already-declared format_hint (+ duration, when relevant) to
one of the amendment's seven directness classes and, separately, to a substantive/
P0-P2-eligibility verdict.
"""

from __future__ import annotations

from personalos.knowledge_edge.state.media import DIRECTNESS_CLASSES

# The seven "substantive" format classes per §8.3's P0 inclusion rule. All but
# financial_media_segment qualify regardless of duration; financial_media_segment
# additionally requires a known duration >= the configured threshold.
FINANCIAL_MEDIA_SEGMENT = "financial_media_segment"

SUBSTANTIVE_FORMATS_NO_DURATION_CHECK = frozenset(
    {
        "original_long_form_interview",
        "panel_fireside",
        "keynote_or_product_presentation",
        "earnings_call_participation",
        "government_testimony",
        "original_podcast_guest",
    }
)

SUBSTANTIVE_FORMATS = SUBSTANTIVE_FORMATS_NO_DURATION_CHECK | {FINANCIAL_MEDIA_SEGMENT}

# The §8.3 exclusion list, given explicit format_hint names so the classifier never
# has to infer exclusion from free text.
EXCLUDED_FORMATS = frozenset(
    {
        "reaction_video",
        "commentary_about_person",
        "synthetic_or_fan_edit",
        "trailer_or_teaser",
        "short_clip_of_longer_original",
        "stale_footage_repost",
        "thumbnail_only_match",
        "compilation_video",
    }
)

# Two additional non-substantive-but-not-excluded shapes the amendment names
# elsewhere (§11.3's own directness class list): a host/interviewer's own show, and
# a bare mention with no appearance at all.
OTHER_FORMATS = frozenset({"host_or_interviewer_appearance", "mentioned_only_appearance"})

ALL_FORMAT_HINTS = SUBSTANTIVE_FORMATS | EXCLUDED_FORMATS | OTHER_FORMATS

_FORMAT_HINT_TO_DIRECTNESS_CLASS = {
    "original_long_form_interview": "direct_primary",
    "panel_fireside": "panel_participant",
    "keynote_or_product_presentation": "direct_primary",
    "earnings_call_participation": "direct_primary",
    "government_testimony": "direct_primary",
    "original_podcast_guest": "direct_primary",
    # financial_media_segment is handled specially in classify_directness (depends
    # on duration).
    "host_or_interviewer_appearance": "host_or_interviewer",
    "mentioned_only_appearance": "mentioned_only",
    "reaction_video": "commentary_about",
    "commentary_about_person": "commentary_about",
    "synthetic_or_fan_edit": "commentary_about",
    "compilation_video": "commentary_about",
    # These two are excluded from P0/P2 by format_hint (see EXCLUDED_FORMATS) but are
    # still, as a factual matter, reposts/clips of genuinely direct content, so their
    # directness class is direct_secondary_upload -- dedup.py is what actually
    # suppresses them when deterministic duplicate evidence exists (§11.4).
    "short_clip_of_longer_original": "direct_secondary_upload",
    "stale_footage_repost": "direct_secondary_upload",
    "thumbnail_only_match": "mentioned_only",
    "trailer_or_teaser": "mentioned_only",
}

# Only these directness classes may receive P0/P2 by default (§11.3).
P0_P2_ELIGIBLE_DIRECTNESS_CLASSES = frozenset(
    {"direct_primary", "direct_secondary_upload", "panel_participant"}
)

DEFAULT_SUBSTANTIVE_DURATION_THRESHOLD_SECONDS = 300  # 5 minutes; provisional, Session 2 finalizes.


def validate_format_hint(value: str) -> str:
    if value not in ALL_FORMAT_HINTS:
        raise ValueError(f"format_hint must be one of {sorted(ALL_FORMAT_HINTS)!r}, got {value!r}")
    return value


def classify_directness(*, format_hint: str, duration_seconds: int | None) -> str:
    """Return one of ``DIRECTNESS_CLASSES`` for a discovered item.

    ``financial_media_segment`` with an unknown duration is classified
    ``ambiguous`` per §8.3 rather than promoted to P0 or silently dropped; a known
    duration (met or not) is always ``direct_primary`` -- duration only ever gates
    *promotion*, handled separately by :func:`classify_substantive_appearance`.
    """
    validate_format_hint(format_hint)
    if format_hint == FINANCIAL_MEDIA_SEGMENT:
        result = "ambiguous" if duration_seconds is None else "direct_primary"
    else:
        result = _FORMAT_HINT_TO_DIRECTNESS_CLASS[format_hint]
    assert result in DIRECTNESS_CLASSES
    return result


def classify_substantive_appearance(
    *,
    format_hint: str,
    directness_class: str,
    duration_seconds: int | None,
    duration_threshold_seconds: int = DEFAULT_SUBSTANTIVE_DURATION_THRESHOLD_SECONDS,
) -> tuple[bool, str]:
    """Return ``(is_substantive, reason)`` -- the shared P0 (Lane C) / P2 (Lane B)
    eligibility gate (§8.3's inclusion rule, applied identically to Lane B per
    §8.2's "must not receive P2 priority" language for non-direct mentions).

    Deterministic; never depends on wall-clock time.
    """
    validate_format_hint(format_hint)
    if directness_class == "ambiguous":
        return False, "ambiguous_unknown_duration_demoted"
    if directness_class not in P0_P2_ELIGIBLE_DIRECTNESS_CLASSES:
        return False, f"directness_class_{directness_class}_not_eligible"
    if format_hint in EXCLUDED_FORMATS:
        return False, f"format_{format_hint}_excluded"
    if format_hint in SUBSTANTIVE_FORMATS_NO_DURATION_CHECK:
        return True, f"substantive_format_{format_hint}"
    if format_hint == FINANCIAL_MEDIA_SEGMENT:
        if duration_seconds is not None and duration_seconds >= duration_threshold_seconds:
            return True, "financial_media_segment_duration_threshold_met"
        return False, "financial_media_segment_duration_below_threshold"
    return False, f"format_{format_hint}_not_substantive"
