"""Deterministic thesis/topic matching grammar per
``docs/knowledge_edge/PHASE0_THESIS_MATCHING.md`` Part 2.

Pure functions only: no I/O, no clock reads, no vault access, no LLM call of any
kind. Callers supply the already-loaded thesis snapshot (a plain sequence of dicts
shaped like the ``active_theses.yaml`` schema's ``theses`` list, version 1) --
loading that file is not this module's concern (see
``docs/knowledge_edge/PHASE0_THESIS_MATCHING.md`` Part 1: the file may not exist yet
at all, which is an acceptable, non-error state -- an empty ``theses`` sequence
simply matches nothing).
"""

from __future__ import annotations

import re
import string
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

_PUNCTUATION_TABLE = str.maketrans({char: " " for char in string.punctuation})


def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation to single spaces, collapse repeated whitespace."""
    lowered = (text or "").lower().translate(_PUNCTUATION_TABLE)
    return " ".join(lowered.split())


def _token_present(token: str, normalized_text: str) -> bool:
    normalized_token = normalize_text(token)
    if not normalized_token:
        return False
    if " " in normalized_token:
        return normalized_token in normalized_text
    return re.search(rf"\b{re.escape(normalized_token)}\b", normalized_text) is not None


def _alias_expanded_tokens(tokens: Sequence[str], aliases: Mapping[str, Sequence[str]]) -> list[str]:
    expanded = list(tokens)
    for token in tokens:
        expanded.extend(aliases.get(token, ()))
    return expanded


@dataclass(frozen=True)
class TopicMatch:
    topic_id: str
    strength: str  # "entity" | "keyword"
    reason: str


def match_topics(
    *,
    company_id: str | None,
    person_ids: Sequence[str],
    title: str,
    description: str,
    theses: Sequence[Mapping],
) -> tuple[TopicMatch, ...]:
    """Evaluate one media_item/scheduled_event against the active thesis snapshot.

    Implements evaluation order rules 1-4 from
    ``PHASE0_THESIS_MATCHING.md`` Part 2 exactly: entity-company, entity-person,
    keyword, then negative-term suppression of keyword-strength hits only.
    """
    normalized_text = normalize_text(f"{title} {description}")
    matches: list[TopicMatch] = []
    for thesis in theses:
        if thesis.get("status") != "active":
            continue
        topic_id = thesis["topic_id"]
        tokens = thesis.get("tokens", {})
        aliases = thesis.get("aliases", {})
        companies = tokens.get("companies", [])
        people = tokens.get("people", [])
        keywords = tokens.get("keywords", [])
        negative_terms = thesis.get("negative_terms", [])

        entity_hit = False
        if company_id is not None and company_id in _alias_expanded_tokens(companies, aliases):
            matches.append(
                TopicMatch(topic_id=topic_id, strength="entity", reason=f"company:{company_id}")
            )
            entity_hit = True
        for person_id in person_ids:
            if person_id in _alias_expanded_tokens(people, aliases):
                matches.append(
                    TopicMatch(topic_id=topic_id, strength="entity", reason=f"person:{person_id}")
                )
                entity_hit = True

        if entity_hit:
            continue  # rule 3 is redundant once an entity hit exists for this topic

        expanded_keywords = _alias_expanded_tokens(keywords, aliases)
        hit_keyword = next(
            (keyword for keyword in expanded_keywords if _token_present(keyword, normalized_text)),
            None,
        )
        if hit_keyword is None:
            continue

        negative_hit = any(
            _token_present(negative_term, normalized_text) for negative_term in negative_terms
        )
        if negative_hit:
            continue  # rule 4: discard keyword-strength hit only

        matches.append(TopicMatch(topic_id=topic_id, strength="keyword", reason=f"keyword:{hit_keyword}"))

    return tuple(matches)


def leading_topic(
    matches: Sequence[TopicMatch], *, theses_by_id: Mapping[str, Mapping]
) -> str | None:
    """Rule 5: cosmetic tie-break for the single "why this surfaced" topic label.

    Highest ``precedence`` wins; ties break by ``topic_id`` ascending. Never
    discards a match -- purely a display-ordering choice among survivors.
    """
    surviving_topic_ids = {match.topic_id for match in matches}
    if not surviving_topic_ids:
        return None
    return min(
        surviving_topic_ids,
        key=lambda topic_id: (-int(theses_by_id[topic_id].get("precedence", 0)), topic_id),
    )
