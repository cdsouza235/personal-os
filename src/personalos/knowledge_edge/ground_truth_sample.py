"""P-KE-2C: frozen ground-truth sample construction (`PHASE0_THESIS_MATCHING.md`
Part 3, R3-04, amendment §19 Packet 2C).

This module builds the PRECISION side of the sample deterministically from
already-persisted shadow-scan data: which surfaced candidates a human reviews and
confirms/rejects. It cannot construct the RECALL side (§Part 3's "independently-
identified known appearances") -- that requires a human to already know of
appearances the system may have missed, which is not derivable from this repo's own
state. The recall sections this module emits are therefore always empty lists with
their required minimum size recorded alongside them; the Conductor fills them in by
hand as part of acknowledging the sample (R3-04), before this same file is frozen.

No LLM call, no fuzzy matching, no vault access -- matches
`PHASE0_THESIS_MATCHING.md`'s own "operate without vault access or an LLM"
constraint, restated here for the sampling procedure rather than the matching
grammar.

Determinism: given the same DB state, window, and `generated_at`, two calls to
`build_ground_truth_sample` produce byte-identical `to_canonical_dict()` output.
Selection within an over-full stratum uses a stable hash of each candidate's own
entity id (`sha256`, never `hash()` or `random`) as the sort key, so the choice of
*which* candidates land in the sample is reproducible without introducing a lexical
or discovery-order bias.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import personalos.knowledge_edge.state as ke

SAMPLE_SCHEMA_VERSION = 1

# Provisional minimum/target sample sizes, PHASE0_THESIS_MATCHING.md Part 3.
LANE_A_PRECISION_SAMPLE_SIZE = 10
LANE_B_PRECISION_SAMPLE_SIZE = 30
LANE_B_RECALL_MINIMUM = 15
LANE_C_PRECISION_SAMPLE_SIZE = 20
LANE_C_RECALL_MINIMUM = 10
MINIMUM_WINDOW_DAYS = 14

LANE_LABELS: dict[str, str] = {
    "curated_podcasts": "Lane A -- Curated Podcasts",
    "market_voices": "Lane B -- Market Voices",
    "consequential_leaders": "Lane C -- Consequential Leaders",
    "earnings_events": "Lane D -- Earnings & Corporate Events",
}


class GroundTruthSampleError(ValueError):
    """Raised when the sampling window or inputs do not satisfy Part 3's design."""


def _stable_rank(entity_id: str) -> str:
    """Deterministic pseudo-random ordering key: sha256 of the entity's own stable
    id. Never Python's builtin ``hash()`` (salted per-process, not reproducible
    across runs) and never ``random`` (not reproducible without a seed this module
    would then have to also freeze)."""
    return hashlib.sha256(entity_id.encode("utf-8")).hexdigest()


def _validate_window(window_start: str, window_end: str) -> None:
    try:
        start = date.fromisoformat(window_start)
        end = date.fromisoformat(window_end)
    except ValueError as error:
        raise GroundTruthSampleError(
            f"window_start/window_end must be ISO dates (YYYY-MM-DD): {error}"
        ) from error
    if end < start:
        raise GroundTruthSampleError("window_end must not be before window_start")
    span_days = (end - start).days + 1
    if span_days < MINIMUM_WINDOW_DAYS:
        raise GroundTruthSampleError(
            f"sampling window must span at least {MINIMUM_WINDOW_DAYS} consecutive "
            f"calendar days (Part 3); got {span_days} day(s) "
            f"({window_start}..{window_end})"
        )


def _in_window(value: str | None, *, window_start: str, window_end: str) -> bool:
    if not value:
        return False
    day = value[:10]
    return window_start <= day <= window_end


def _media_precision_candidate(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "media_item_id": item["media_item_id"],
        "source_id": item["source_id"],
        "title": item["title"],
        "canonical_url": item["canonical_url"],
        "published_at": item["published_at"],
        "directness_class": item["directness_class"],
        "canonical_group_id": item["canonical_group_id"],
        "is_canonical": item["is_canonical"],
        "queue_visibility_state": item["queue_visibility_state"],
    }


def _select_deterministic_sample(
    candidates: list[dict[str, Any]], *, size: int, id_field: str
) -> list[dict[str, Any]]:
    ordered = sorted(candidates, key=lambda row: _stable_rank(str(row[id_field])))
    return ordered[:size]


@dataclass(frozen=True)
class GroundTruthSample:
    schema_version: int
    generated_at: str
    window_start: str
    window_end: str
    lane_d_window_end: str
    lane_a_precision_check: tuple[dict[str, Any], ...]
    lane_b_precision_check: tuple[dict[str, Any], ...]
    lane_b_recall_check_minimum: int
    lane_b_recall_check: tuple[dict[str, Any], ...]
    lane_c_precision_check: tuple[dict[str, Any], ...]
    lane_c_recall_check_minimum: int
    lane_c_recall_check: tuple[dict[str, Any], ...]
    lane_d_events: tuple[dict[str, Any], ...]
    coverage_gaps: tuple[str, ...]

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "lane_d_window_end": self.lane_d_window_end,
            "lane_a_precision_check": list(self.lane_a_precision_check),
            "lane_b_precision_check": list(self.lane_b_precision_check),
            "lane_b_recall_check_minimum": self.lane_b_recall_check_minimum,
            "lane_b_recall_check": list(self.lane_b_recall_check),
            "lane_c_precision_check": list(self.lane_c_precision_check),
            "lane_c_recall_check_minimum": self.lane_c_recall_check_minimum,
            "lane_c_recall_check": list(self.lane_c_recall_check),
            "lane_d_events": list(self.lane_d_events),
            "coverage_gaps": list(self.coverage_gaps),
        }

    def canonical_json(self) -> str:
        return json.dumps(self.to_canonical_dict(), sort_keys=True, separators=(",", ":"))

    def checksum_sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def build_ground_truth_sample(
    connection: Any,
    *,
    window_start: str,
    window_end: str,
    generated_at: str,
    lane_d_window_end: str | None = None,
    coverage_gaps: Sequence[str] = (),
) -> GroundTruthSample:
    """Construct the precision-side sample deterministically from whatever is
    already persisted in ``connection`` (a post-scan shadow DB). ``lane_d_window_end``
    may extend past ``window_end`` (Part 3: "if the chosen 14-day window happens to
    contain zero Tier A earnings events, extend the Lane D stratum's window (only)
    until at least one Tier A event has completed") -- it must never be earlier.
    """
    _validate_window(window_start, window_end)
    effective_lane_d_window_end = lane_d_window_end or window_end
    if effective_lane_d_window_end < window_end:
        raise GroundTruthSampleError("lane_d_window_end must not be before window_end")

    sources_by_id = {source["source_id"]: source for source in ke.list_sources(connection)}
    media_by_lane: dict[str, list[dict[str, Any]]] = {}
    for item in ke.list_media_items(connection):
        source = sources_by_id.get(item["source_id"])
        if source is None:
            continue
        if not _in_window(item["published_at"], window_start=window_start, window_end=window_end):
            continue
        media_by_lane.setdefault(source["lane"], []).append(item)

    # Lane A: every discovered item regardless of queue_visibility_state -- the
    # spot-check is about grouping/dedup correctness (Part 3), which requires
    # seeing suppressed canonical-group duplicates too, not just what survived to
    # be surfaced.
    lane_a_pool = [
        _media_precision_candidate(item) for item in media_by_lane.get("curated_podcasts", [])
    ]
    lane_a = _select_deterministic_sample(
        lane_a_pool, size=LANE_A_PRECISION_SAMPLE_SIZE, id_field="media_item_id"
    )

    # Lane B/C: only what was actually SURFACED (candidate/queued) -- a suppressed
    # item was never shown to Chris, so it cannot be part of a "surfaced candidate
    # appearances" precision check.
    def _surfaced(lane: str) -> list[dict[str, Any]]:
        return [
            _media_precision_candidate(item)
            for item in media_by_lane.get(lane, [])
            if item["queue_visibility_state"] in ("candidate", "queued")
        ]

    lane_b = _select_deterministic_sample(
        _surfaced("market_voices"), size=LANE_B_PRECISION_SAMPLE_SIZE, id_field="media_item_id"
    )
    lane_c = _select_deterministic_sample(
        _surfaced("consequential_leaders"),
        size=LANE_C_PRECISION_SAMPLE_SIZE,
        id_field="media_item_id",
    )

    companies_by_id = {company["company_id"]: company for company in ke.list_companies(connection)}
    lane_d_events = []
    for event in ke.list_scheduled_events(connection):
        if not _in_window(
            event["scheduled_date"], window_start=window_start, window_end=effective_lane_d_window_end
        ):
            continue
        company = companies_by_id.get(event["company_id"])
        if company is None or company["priority_tier"] != "tier_a":
            continue
        lane_d_events.append(
            {
                "event_id": event["event_id"],
                "company_id": event["company_id"],
                "company_display_name": company["display_name"],
                "event_type": event["event_type"],
                "scheduled_date": event["scheduled_date"],
                "schedule_confidence": event["schedule_confidence"],
                "event_status": event["event_status"],
            }
        )
    lane_d_events.sort(key=lambda row: (row["scheduled_date"], row["event_id"]))

    return GroundTruthSample(
        schema_version=SAMPLE_SCHEMA_VERSION,
        generated_at=generated_at,
        window_start=window_start,
        window_end=window_end,
        lane_d_window_end=effective_lane_d_window_end,
        lane_a_precision_check=tuple(lane_a),
        lane_b_precision_check=tuple(lane_b),
        lane_b_recall_check_minimum=LANE_B_RECALL_MINIMUM,
        lane_b_recall_check=(),
        lane_c_precision_check=tuple(lane_c),
        lane_c_recall_check_minimum=LANE_C_RECALL_MINIMUM,
        lane_c_recall_check=(),
        lane_d_events=tuple(lane_d_events),
        coverage_gaps=tuple(coverage_gaps),
    )


# ------------------------------------------------------------------- freeze artifact

ACK_STATUS_PENDING = "PENDING CONDUCTOR ACKNOWLEDGMENT (R3-04)"
ACK_STATUS_ACKNOWLEDGED = "ACKNOWLEDGED"


@dataclass(frozen=True)
class FrozenSampleFiles:
    markdown_path: str
    markdown_text: str
    frozen_json_path: str
    frozen_json_text: str
    checksum_sha256: str


def render_frozen_sample_files(
    sample: GroundTruthSample,
    *,
    sample_date: str,
    frozen_json_relative_path: str,
    markdown_relative_path: str,
) -> FrozenSampleFiles:
    """Pure rendering: builds the markdown doc + canonical JSON text without
    touching the filesystem, so tests can assert on content/determinism without a
    temp-dir round trip, and the CLI layer owns the one filesystem write.
    """
    frozen_json_text = sample.canonical_json()
    checksum = sample.checksum_sha256()

    header = (
        "---\n"
        f'status: "{ACK_STATUS_PENDING}"\n'
        f'sample_date: "{sample_date}"\n'
        f'frozen_file: "{frozen_json_relative_path}"\n'
        f'checksum_sha256: "{checksum}"\n'
        'acknowledged_by: ""\n'
        'acknowledged_at: ""\n'
        "---\n"
    )

    lines: list[str] = [
        header,
        "",
        f"# Knowledge Edge -- Frozen Ground-Truth Sample ({sample_date})",
        "",
        "Per R3-04 (`PHASE0_THESIS_MATCHING.md` Part 3): this sample's contents and "
        "construction procedure must be Codex-reviewed and Chris-acknowledged "
        "**before any threshold tuning begins against it**. The Conductor "
        "acknowledges by editing the fenced header above -- `status:` to "
        f'`"{ACK_STATUS_ACKNOWLEDGED}"`, plus `acknowledged_by`/`acknowledged_at` -- '
        "and committing that edit. `personalos knowledge-edge shadow report` refuses "
        "to run against an unacknowledged sample.",
        "",
        f"Window: `{sample.window_start}` .. `{sample.window_end}` "
        f"({(date.fromisoformat(sample.window_end) - date.fromisoformat(sample.window_start)).days + 1} days). "
        f"Lane D window: `{sample.window_start}` .. `{sample.lane_d_window_end}`.",
        "",
        f"Frozen machine-readable file: `{frozen_json_relative_path}` "
        f"(sha256 `{checksum}`).",
        "",
    ]

    if sample.coverage_gaps:
        lines.append("## Named coverage gaps")
        lines.append("")
        for gap in sample.coverage_gaps:
            lines.append(f"- {gap}")
        lines.append("")

    lines.append("## Lane A -- Curated Podcasts (precision/grouping spot-check)")
    lines.append("")
    lines.append(f"{len(sample.lane_a_precision_check)} item(s) sampled.")
    lines.append("")
    lines.append("| media_item_id | source_id | title | is_canonical | directness_class |")
    lines.append("|---|---|---|---|---|")
    for item in sample.lane_a_precision_check:
        lines.append(
            f"| {item['media_item_id']} | {item['source_id']} | {item['title']} | "
            f"{item['is_canonical']} | {item['directness_class']} |"
        )
    lines.append("")

    for lane_key, precision_items, recall_minimum in (
        ("market_voices", sample.lane_b_precision_check, sample.lane_b_recall_check_minimum),
        (
            "consequential_leaders",
            sample.lane_c_precision_check,
            sample.lane_c_recall_check_minimum,
        ),
    ):
        lines.append(f"## {LANE_LABELS[lane_key]}")
        lines.append("")
        lines.append(f"### Precision check -- {len(precision_items)} surfaced candidate(s)")
        lines.append("")
        lines.append("| media_item_id | source_id | title | directness_class |")
        lines.append("|---|---|---|---|")
        for item in precision_items:
            lines.append(
                f"| {item['media_item_id']} | {item['source_id']} | {item['title']} | "
                f"{item['directness_class']} |"
            )
        lines.append("")
        lines.append(
            f"### Recall check -- PENDING, minimum {recall_minimum} independently-identified "
            "known appearance(s)"
        )
        lines.append("")
        lines.append(
            "This section cannot be constructed from repo state: it requires the reviewer "
            "to independently know of appearances during the window (e.g. by manually "
            "checking 2-3 known sources per Part 3), not just grade what the system already "
            "surfaced. The Conductor fills this in as part of the acknowledgment above."
        )
        lines.append("")

    lines.append("## Lane D -- Earnings & Corporate Events (100% of window, not sampled)")
    lines.append("")
    lines.append(f"{len(sample.lane_d_events)} Tier A event(s) in window.")
    lines.append("")
    lines.append("| event_id | company | type | scheduled_date | confidence | status |")
    lines.append("|---|---|---|---|---|---|")
    for event in sample.lane_d_events:
        lines.append(
            f"| {event['event_id']} | {event['company_display_name']} | {event['event_type']} | "
            f"{event['scheduled_date']} | {event['schedule_confidence']} | {event['event_status']} |"
        )
    lines.append("")

    markdown_text = "\n".join(lines)

    return FrozenSampleFiles(
        markdown_path=markdown_relative_path,
        markdown_text=markdown_text,
        frozen_json_path=frozen_json_relative_path,
        frozen_json_text=frozen_json_text,
        checksum_sha256=checksum,
    )


class SampleAcknowledgmentError(ValueError):
    """Raised when a sample's fenced header cannot be parsed, or the sample is not
    yet Conductor-acknowledged (R3-04)."""


def parse_sample_header(markdown_text: str) -> dict[str, str]:
    """Parse the fenced ``---``-delimited header block at the top of a frozen
    sample markdown file into a flat ``{key: value}`` dict. Deliberately not a
    general YAML parser (this repo has zero third-party dependencies) -- it only
    understands the narrow ``key: "value"`` shape this module itself writes.
    """
    lines = markdown_text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SampleAcknowledgmentError("sample file is missing its fenced header (no leading ---)")
    fields: dict[str, str] = {}
    closed = False
    for line in lines[1:]:
        if line.strip() == "---":
            closed = True
            break
        if ":" not in line:
            continue
        key, _, raw_value = line.partition(":")
        value = raw_value.strip()
        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1]
        fields[key.strip()] = value
    if not closed:
        raise SampleAcknowledgmentError("sample file's fenced header is never closed with ---")
    return fields


def require_acknowledged_sample(markdown_text: str, *, frozen_json_text: str) -> dict[str, str]:
    """Parse the header, require `status: "ACKNOWLEDGED"`, and require the header's
    recorded checksum to match the actual frozen JSON content byte-for-byte
    (integrity: catches a frozen file edited after the checksum was recorded, or a
    header copy-pasted onto the wrong JSON file).
    """
    fields = parse_sample_header(markdown_text)
    status = fields.get("status", "")
    if status != ACK_STATUS_ACKNOWLEDGED:
        raise SampleAcknowledgmentError(
            f"sample is not yet Conductor-acknowledged (R3-04): status is {status!r}, "
            f'expected "{ACK_STATUS_ACKNOWLEDGED}"'
        )
    recorded_checksum = fields.get("checksum_sha256", "")
    actual_checksum = hashlib.sha256(frozen_json_text.encode("utf-8")).hexdigest()
    if recorded_checksum != actual_checksum:
        raise SampleAcknowledgmentError(
            f"sample checksum mismatch: header records {recorded_checksum!r}, frozen file "
            f"actually hashes to {actual_checksum!r} -- the frozen file was modified after "
            "acknowledgment, or the header/file pairing is wrong"
        )
    if not fields.get("acknowledged_by", "").strip():
        raise SampleAcknowledgmentError("sample is ACKNOWLEDGED but acknowledged_by is empty")
    if not fields.get("acknowledged_at", "").strip():
        raise SampleAcknowledgmentError("sample is ACKNOWLEDGED but acknowledged_at is empty")
    return fields


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
