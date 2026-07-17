"""Knowledge Edge dashboard data + HTML rendering (P-KE-1C).

Composes ``scan_orchestrator.build_queue_snapshot_view`` plus ``state/`` reads into
the amendment's own evening-queue presentation (PRD_AMENDMENT_KNOWLEDGE_EDGE.md
Sec 7.2, Sec 8.4 link hierarchy, Sec 10.5 coverage reporting, Sec 12.3 empty state).
Read-only: this module never writes to ``ke_*`` tables. Wired as an additive,
feature-mode-gated section into the existing ``src/personalos/dashboard.py`` shell
(AD-1), not a standalone app (amendment Sec 14.1).

No network-capable import appears anywhere in this module. Feature modes supported
as of P-KE-2C are ``disabled``/``fixture``/``shadow_live`` (amendment Sec 14.4) --
``active_read_only``/``active_with_obsidian_handoff`` remain later-phase,
Session-3-gated modes this packet must not enable. ``shadow_live`` admission here is
display-only: this module never writes, so composing a queue summary for
``shadow_live`` carries no write-surface risk in itself. The actual §14.4 fence --
shadow DB path, no notifications/Obsidian/scheduler/production writes -- is enforced
by ``personalos.knowledge_edge.shadow_mode``, which every write-capable ``shadow_live``
entrypoint (bootstrap, shadow scan, sample freeze, report generation) calls before
doing anything else.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from html import escape
from typing import Any

import personalos.knowledge_edge.state as ke
from personalos.knowledge_edge.scan_orchestrator import build_queue_snapshot_view

KNOWLEDGE_EDGE_FEATURE_MODES = ("disabled", "fixture", "shadow_live")
DEFAULT_KNOWLEDGE_EDGE_FEATURE_MODE = "disabled"

# Empty until Packet 3A's vendor-domain-list approval gate clears (Phase0 Architecture
# Decisions AD-1/amendment Sec8.4): with no domain approved yet, every live_webcast_url
# is correctly quarantined as "Link pending (unknown vendor)" rather than displayed as
# verified. Callers may pass their own set (e.g. tests) once a domain is approved.
DEFAULT_APPROVED_WEBCAST_VENDOR_DOMAINS: frozenset[str] = frozenset()

_MEDIA_QUEUE_SECTIONS = (
    "p0_consequential_leaders",
    "p1_core_podcasts",
    "p2_market_voices",
    "saved_to_reconsider",
)
_SECTION_TITLES: dict[str, str] = {
    "tomorrow_earnings_events": "Tomorrow: Earnings & Corporate Events",
    "p0_consequential_leaders": "P0: Consequential Leader Appearances",
    "p1_core_podcasts": "P1: Core Podcast Releases",
    "p2_market_voices": "P2: Market Voice Appearances",
    "saved_to_reconsider": "Saved to Reconsider",
}


def validate_knowledge_edge_feature_mode(value: str) -> str:
    if value not in KNOWLEDGE_EDGE_FEATURE_MODES:
        allowed = ", ".join(KNOWLEDGE_EDGE_FEATURE_MODES)
        raise ValueError(
            f"knowledge_edge feature mode must be one of: {allowed} "
            "(active_* are later-phase, Session-3-gated modes)"
        )
    return value


def build_knowledge_edge_queue_summary(
    connection: sqlite3.Connection,
    *,
    queue_date: str,
    feature_mode: str = DEFAULT_KNOWLEDGE_EDGE_FEATURE_MODE,
    approved_webcast_vendor_domains: frozenset[str] = DEFAULT_APPROVED_WEBCAST_VENDOR_DOMAINS,
) -> dict[str, Any]:
    """Compose the full Daily Intelligence Queue view for ``queue_date``.

    Returns ``{"feature_mode": "disabled", "available": False, ...}`` without
    reading any Knowledge Edge table when disabled -- the dashboard integration
    hook relies on this short-circuit to stay byte-identical to pre-Knowledge-Edge
    output.
    """
    feature_mode = validate_knowledge_edge_feature_mode(feature_mode)
    if feature_mode == "disabled":
        return {"feature_mode": "disabled", "available": False, "queue_date": queue_date}

    snapshot = build_queue_snapshot_view(connection, queue_date=queue_date)

    sections: dict[str, list[dict[str, Any]]] = {}
    for section in ("tomorrow_earnings_events", *_MEDIA_QUEUE_SECTIONS):
        cards = []
        for row in snapshot[section]:
            if row["entity_type"] == "scheduled_event":
                card = _hydrate_event_card(
                    connection,
                    row["entity_id"],
                    approved_webcast_vendor_domains=approved_webcast_vendor_domains,
                )
            else:
                card = _hydrate_media_card(connection, row["entity_id"])
            card["rank_position"] = row["rank_position"]
            card["why_surfaced"] = row["explanation"] or card.get("priority_explanation", "")
            cards.append(card)
        sections[section] = cards

    demoted_ambiguous = [
        {**_hydrate_media_card(connection, row["entity_id"]), "why_surfaced": row["explanation"]}
        for row in snapshot["demoted_ambiguous"]
    ]

    coverage = _build_coverage_summary(connection, queue_date=queue_date)
    empty_state = _build_empty_state(sections, coverage)

    return {
        "feature_mode": feature_mode,
        "available": True,
        "queue_date": queue_date,
        "sections": sections,
        "demoted_ambiguous": demoted_ambiguous,
        "coverage": coverage,
        "empty_state": empty_state,
    }


def _hydrate_media_card(connection: sqlite3.Connection, media_item_id: str) -> dict[str, Any]:
    item = ke.get_media_item(connection, media_item_id)
    if item is None:
        return {"entity_type": "media_item", "media_item_id": media_item_id, "missing": True}

    matches = ke.list_entity_matches(connection, target_type="media_item", target_id=media_item_id)
    matched_people: list[str] = []
    matched_companies: list[str] = []
    false_positive_flagged = False
    for match in matches:
        if match["is_false_positive"]:
            false_positive_flagged = True
        if match["matched_entity_type"] == "person":
            person = ke.get_person(connection, match["matched_entity_id"])
            if person is not None:
                matched_people.append(person["display_name"])
        elif match["matched_entity_type"] == "company":
            company = ke.get_company(connection, match["matched_entity_id"])
            if company is not None:
                matched_companies.append(company["display_name"])

    decision = ke.get_user_decision(connection, entity_type="media_item", entity_id=media_item_id)
    source = ke.get_source(connection, item["source_id"])

    return {
        "entity_type": "media_item",
        "media_item_id": media_item_id,
        "title": item["title"],
        "source_name": source["name"] if source is not None else item["source_id"],
        "published_at": item["published_at"],
        "duration_seconds": item["duration_seconds"],
        "media_type": item["media_type"],
        "directness_class": item["directness_class"],
        "match_confidence": item["match_confidence"],
        "priority_explanation": item["priority_explanation"],
        "canonical_url": item["canonical_url"],
        "coverage_notes": item["coverage_notes"],
        "decision_state": decision["decision_state"] if decision is not None else "undecided",
        "matched_people": matched_people,
        "matched_companies": matched_companies,
        "false_positive_flagged": false_positive_flagged,
        "entity_match_ids": [match["entity_match_id"] for match in matches],
    }


def _hydrate_event_card(
    connection: sqlite3.Connection,
    event_id: str,
    *,
    approved_webcast_vendor_domains: frozenset[str],
) -> dict[str, Any]:
    event = ke.get_scheduled_event(connection, event_id)
    if event is None:
        return {"entity_type": "scheduled_event", "event_id": event_id, "missing": True}

    company = ke.get_company(connection, event["company_id"])
    decision = ke.get_user_decision(connection, entity_type="scheduled_event", entity_id=event_id)
    link = _resolve_event_best_link(
        event, approved_webcast_vendor_domains=approved_webcast_vendor_domains
    )

    return {
        "entity_type": "scheduled_event",
        "event_id": event_id,
        "company_display_name": company["display_name"] if company is not None else event["company_id"],
        "event_type": event["event_type"],
        "fiscal_period": event["fiscal_period"],
        "scheduled_date": event["scheduled_date"],
        "time_precision": event["time_precision"],
        "timing_label": event["timing_label"],
        "schedule_confidence": event["schedule_confidence"],
        "event_status": event["event_status"],
        "decision_state": decision["decision_state"] if decision is not None else "undecided",
        "priority_explanation": "",
        "link": link,
    }


def _url_host(url: str) -> str:
    """Extract a lowercased host from ``url`` using plain string ops -- no
    ``urllib.parse`` import here (that carve-out is scoped to
    ``engine/canonicalize.py`` only, per this packet's own constraints)."""
    remainder = url.split("://", 1)[-1]
    host = remainder.split("/", 1)[0]
    return host.lower()


def _resolve_event_best_link(
    event: Mapping[str, Any], *, approved_webcast_vendor_domains: frozenset[str]
) -> dict[str, Any]:
    """Amendment Sec8.4 link hierarchy, applied to the fields the 1A schema actually
    persists (``official_event_page_url`` doubles as both "official company event
    detail page" and "official investor-relations events page" -- 1A has no
    separate IR-events-page column)."""
    live_webcast_url = event.get("live_webcast_url")
    if live_webcast_url:
        if _url_host(live_webcast_url) in approved_webcast_vendor_domains:
            return {
                "label": "official company live webcast URL",
                "url": live_webcast_url,
                "quarantined": False,
            }
        return {
            "label": "Link pending (unknown vendor)",
            "url": None,
            "official_event_page_url": event.get("official_event_page_url"),
            "quarantined": True,
        }
    if event.get("official_event_page_url"):
        return {
            "label": "official company event detail page",
            "url": event["official_event_page_url"],
            "quarantined": False,
        }
    if event.get("replay_url"):
        return {
            "label": "official company replay URL",
            "url": event["replay_url"],
            "quarantined": False,
        }
    return {
        "label": "Link pending",
        "url": None,
        "official_event_page_url": event.get("official_event_page_url"),
        "quarantined": False,
    }


def _build_coverage_summary(connection: sqlite3.Connection, *, queue_date: str) -> dict[str, Any]:
    reports = ke.list_coverage_reports(connection, report_date=queue_date)
    latest = max(reports, key=lambda report: report["created_at"]) if reports else None

    sources_by_id = {source["source_id"]: source for source in ke.list_sources(connection)}
    per_adapter_lines = []
    for health in ke.list_source_health(connection):
        source = sources_by_id.get(health["source_id"])
        name = source["name"] if source is not None else health["source_id"]
        line = f"{name}: {health['status']}"
        if health["last_success_at"]:
            line += f"; last success {health['last_success_at']}"
        per_adapter_lines.append(line)

    return {
        "overall_summary": latest["overall_summary"] if latest is not None else "no coverage report for this queue date",
        "report": latest["report"] if latest is not None else {},
        "per_adapter_lines": sorted(per_adapter_lines),
        # amendment Sec10.5: "the absence of a result must never be described as
        # proof that no appearance occurred" -- fixed caption, not derived data.
        "honesty_note": (
            "Coverage reflects only sources successfully checked this scan; absence "
            "of a result is never proof that no appearance occurred."
        ),
    }


def _build_empty_state(
    sections: Mapping[str, Sequence[Mapping[str, Any]]], coverage: Mapping[str, Any]
) -> str | None:
    total_cards = sum(
        len(sections[section])
        for section in ("tomorrow_earnings_events", *_MEDIA_QUEUE_SECTIONS)
    )
    if total_cards > 0:
        return None
    report = coverage.get("report", {})
    healthy = report.get("sources_healthy", 0)
    total = report.get("sources_total", 0)
    return (
        f"No qualifying item was found among the sources successfully checked "
        f"({healthy} of {total} healthy). Use a saved item or complete a primary-source review."
    )


# --------------------------------------------------------------------------- rendering


def render_knowledge_edge_queue_html(summary: Mapping[str, Any]) -> str:
    """Render the composed queue summary as an HTML section, or "" when the
    feature mode is disabled -- callers rely on this empty-string short-circuit to
    keep the surrounding dashboard byte-identical when Knowledge Edge is off."""
    if not summary.get("available"):
        return ""

    mode_indicators = {
        "fixture": "fixture data only -- no live network, no scheduler activation",
        "shadow_live": (
            "shadow database, live discovery data -- no production notification, no "
            "Obsidian write, no scheduler activation (amendment Sec14.4)"
        ),
    }
    body = _definition_list(
        (
            ("Queue date", summary["queue_date"]),
            ("Feature mode", summary["feature_mode"]),
            (
                "Mode indicator",
                mode_indicators.get(summary["feature_mode"], "unrecognized mode"),
            ),
        )
    )
    if summary.get("empty_state"):
        body += f'<p class="ke-empty-state">{_e(summary["empty_state"])}</p>'

    body += _render_earnings_section(summary["sections"]["tomorrow_earnings_events"])
    for section in _MEDIA_QUEUE_SECTIONS:
        body += _render_media_section(_SECTION_TITLES[section], summary["sections"][section])
    body += _render_demoted_ambiguous_section(summary["demoted_ambiguous"])
    body += _render_coverage_section(summary["coverage"])

    return _section(
        "knowledge-edge-queue", "Knowledge Edge: Daily Intelligence Queue", body
    )


def _render_earnings_section(cards: Sequence[Mapping[str, Any]]) -> str:
    rows = [
        (
            card["company_display_name"],
            card["event_type"],
            f'{card["scheduled_date"]} ({card["time_precision"]})',
            card["schedule_confidence"],
            card["event_status"],
            card["decision_state"],
            _format_event_link(card["link"]),
        )
        for card in cards
    ]
    return (
        f'<h3>{_e(_SECTION_TITLES["tomorrow_earnings_events"])}</h3>'
        + _table(
            ("Company", "Type", "Scheduled", "Confidence", "Status", "Decision", "Link"),
            rows,
        )
    )


def _format_event_link(link: Mapping[str, Any]) -> str:
    if link["quarantined"]:
        return f'{link["label"]} (see {link.get("official_event_page_url") or "IR page"})'
    if link["url"]:
        return f'{link["label"]}: {link["url"]}'
    return f'{link["label"]} (see {link.get("official_event_page_url") or "IR page"})'


def _render_media_section(title: str, cards: Sequence[Mapping[str, Any]]) -> str:
    rows = [
        (
            card["title"],
            card["source_name"],
            card["published_at"] or "",
            _format_duration(card["duration_seconds"]),
            f'{card["directness_class"]} ({_format_confidence(card["match_confidence"])})',
            ", ".join(card["matched_people"] + card["matched_companies"]) or "-",
            card["decision_state"],
            card["why_surfaced"],
            "flagged" if card["false_positive_flagged"] else "",
        )
        for card in cards
    ]
    return f"<h3>{_e(title)}</h3>" + _table(
        (
            "Title",
            "Source",
            "Published",
            "Duration",
            "Directness (confidence)",
            "Matched",
            "Decision",
            "Why this surfaced",
            "False-positive flag",
        ),
        rows,
    )


def _render_demoted_ambiguous_section(cards: Sequence[Mapping[str, Any]]) -> str:
    rows = [
        (
            card["title"],
            card["source_name"],
            card["directness_class"],
            card["why_surfaced"],
        )
        for card in cards
    ]
    return (
        '<h3>Demoted / Ambiguous</h3>'
        '<p>Approved-source items whose directness could not be confirmed. Never '
        "promoted to P0/P2, never silently dropped (amendment &sect;8.3).</p>"
        + _table(("Title", "Source", "Directness", "Ambiguity label / reason"), rows)
    )


def _render_coverage_section(coverage: Mapping[str, Any]) -> str:
    body = _definition_list((("Overall", coverage["overall_summary"]),))
    body += _render_list(coverage["per_adapter_lines"])
    body += f'<p class="ke-coverage-honesty">{_e(coverage["honesty_note"])}</p>'
    return f"<h3>{_e('Coverage & Source Health')}</h3>" + body


def _format_duration(duration_seconds: int | None) -> str:
    if duration_seconds is None:
        return "unknown"
    minutes, seconds = divmod(int(duration_seconds), 60)
    return f"{minutes}m{seconds:02d}s"


def _format_confidence(match_confidence: float | None) -> str:
    return "unknown" if match_confidence is None else f"{match_confidence:.2f}"


def _section(section_id: str, title: str, body: str) -> str:
    return f'<section id="{_e(section_id)}"><h2>{_e(title)}</h2>{body}</section>'


def _definition_list(items: Sequence[tuple[str, object]]) -> str:
    parts = ["<dl>"]
    for key, value in items:
        parts.append(f"<dt>{_e(key)}</dt><dd>{_e(value)}</dd>")
    parts.append("</dl>")
    return "".join(parts)


def _render_list(items: Sequence[object]) -> str:
    if not items:
        return "<ul></ul>"
    return "<ul>" + "".join(f"<li>{_e(item)}</li>" for item in items) + "</ul>"


def _table(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> str:
    if not rows:
        return "<p>No rows.</p>"
    header_html = "".join(f"<th>{_e(header)}</th>" for header in headers)
    row_html = "".join(
        "<tr>" + "".join(f"<td>{_e(cell)}</td>" for cell in row) + "</tr>" for row in rows
    )
    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{row_html}</tbody></table>"


def _e(value: object) -> str:
    return escape(str(value), quote=True)
