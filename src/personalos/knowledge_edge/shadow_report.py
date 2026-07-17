"""P-KE-2C: shadow-report generator (amendment §18/§19 Phase 2 acceptance, R2-11,
R2-16, R2-22).

Computes per-lane precision/recall/duplicate-leakage from a Conductor-acknowledged,
hand-graded ground-truth sample (`ground_truth_sample.py`), plus a coverage report
(9/9 Lane A podcast feeds; the §10.3 YouTube-channel-allowlist gap NAMED, never
silently absorbed; person-search quota usage vs the §5 per-scan budget). Emits
`docs/knowledge_edge/SHADOW_REPORT_<date>.md` via a CLI subcommand.

## Grading protocol

A frozen sample (`ground_truth_sample.py`) is never edited after freeze -- grading
instead happens entirely in a separate, paired grades file (`sample_grades.py`),
created strictly after R3-04 acknowledgment (see
`docs/knowledge_edge/PACKET_2C_FIRST_SHADOW_RUN.md`):

- The grades file's `precision_verdicts` maps each frozen precision-check item's
  `media_item_id` to one of:
    - `"confirmed"`      -- a genuine, correctly-surfaced appearance;
    - `"rejected"`       -- not a genuine direct appearance (false positive);
    - `"duplicate_leak"` -- a duplicate/repost that should have been suppressed or
      grouped but was not (this feeds precision AND leakage: a leaked duplicate is
      never a "confirmed" correct surfacing);
    - `null`             -- still ungraded -- excluded from every metric, but
      counted and reported as `ungraded`, honestly. Grading never invents a
      verdict for an item nobody reviewed. `sample_grades.require_paired_grades`
      requires every frozen item id to be present as a key (even if `null`) and
      refuses any id that does not belong to the frozen sample.
- Each recall-check entry in the grades file's `lane_b_recall_check`/
  `lane_c_recall_check` gets a `"found_by_system"` boolean (hand-authored
  independently of what the system surfaced, per `PHASE0_THESIS_MATCHING.md` Part 3
  -- these entries exist only in the grades file, never in the frozen sample).

This module never grades anything itself -- it only reads whatever verdicts are
already present and reports honestly on what is and is not graded yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import personalos.knowledge_edge.state as ke
from personalos.knowledge_edge.shadow_bootstrap import LANE_A_SHADOW_VERIFICATION_FLIPS

VERDICT_CONFIRMED = "confirmed"
VERDICT_REJECTED = "rejected"
VERDICT_DUPLICATE_LEAK = "duplicate_leak"
PRECISION_VERDICTS = (VERDICT_CONFIRMED, VERDICT_REJECTED, VERDICT_DUPLICATE_LEAK)

# Provisional Phase 0 thresholds, PHASE0_THESIS_MATCHING.md Part 3 -- Session 2
# approves final values; this module only compares against these starting points.
PROVISIONAL_PRECISION_THRESHOLD_BC = 0.85
PROVISIONAL_RECALL_THRESHOLD_BC = 0.70
PROVISIONAL_DUPLICATE_LEAKAGE_THRESHOLD = 0.10

# §5's worst-case per-scan person-search call budget (see
# rails/knowledge_edge/youtube.py MAX_SEARCH_CALLS_PER_SCAN's own derivation).
PERSON_SEARCH_PER_SCAN_BUDGET = 174

LANE_A_SOURCE_IDS: tuple[str, ...] = tuple(
    flip.source_id for flip in LANE_A_SHADOW_VERIFICATION_FLIPS
)

NAMED_COVERAGE_GAP_SEC10_3 = (
    "No §10.3-approved YouTube channel has been seeded yet in this repo (migration "
    "history seeds zero `youtube_channel` source rows) -- Lane B/C official-channel "
    "coverage is a named, documented gap this report carries forward, not a silent "
    "absence. `search.list` person-search remains the only live Lane B/C mechanism "
    "until a future packet's own Conductor-verified channel allowlist lands."
)


@dataclass(frozen=True)
class LaneGradingMetrics:
    lane: str
    precision_confirmed: int
    precision_rejected: int
    precision_duplicate_leak: int
    precision_ungraded: int
    precision_sample_size: int
    precision: float | None
    duplicate_leakage: float | None
    recall_found: int
    recall_missed: int
    recall_ungraded: int
    recall_sample_size: int
    recall: float | None


def _grade_precision(items: list[dict[str, Any]]) -> tuple[int, int, int, int]:
    confirmed = rejected = duplicate_leak = ungraded = 0
    for item in items:
        verdict = item.get("verdict")
        if verdict == VERDICT_CONFIRMED:
            confirmed += 1
        elif verdict == VERDICT_REJECTED:
            rejected += 1
        elif verdict == VERDICT_DUPLICATE_LEAK:
            duplicate_leak += 1
        else:
            ungraded += 1
    return confirmed, rejected, duplicate_leak, ungraded


def _grade_recall(items: list[dict[str, Any]]) -> tuple[int, int, int]:
    found = missed = ungraded = 0
    for item in items:
        verdict = item.get("found_by_system")
        if verdict is True:
            found += 1
        elif verdict is False:
            missed += 1
        else:
            ungraded += 1
    return found, missed, ungraded


def merge_precision_verdicts(
    precision_items: list[dict[str, Any]], precision_verdicts: dict[str, Any]
) -> list[dict[str, Any]]:
    """Combines a frozen sample's precision-check items (immutable, no `verdict`
    key) with a paired grades file's `precision_verdicts` (`media_item_id ->
    verdict`) into the shape `compute_lane_metrics` expects. Never mutates
    `precision_items` -- returns new dicts, since the caller's frozen-sample data
    must stay untouched.
    """
    return [
        {**item, "verdict": precision_verdicts.get(item["media_item_id"])}
        for item in precision_items
    ]


def compute_lane_metrics(
    *,
    lane: str,
    precision_items: list[dict[str, Any]],
    recall_items: list[dict[str, Any]],
) -> LaneGradingMetrics:
    confirmed, rejected, duplicate_leak, precision_ungraded = _grade_precision(precision_items)
    precision_graded = confirmed + rejected + duplicate_leak
    precision = confirmed / precision_graded if precision_graded else None
    duplicate_leakage = duplicate_leak / precision_graded if precision_graded else None

    found, missed, recall_ungraded = _grade_recall(recall_items)
    recall_graded = found + missed
    recall = found / recall_graded if recall_graded else None

    return LaneGradingMetrics(
        lane=lane,
        precision_confirmed=confirmed,
        precision_rejected=rejected,
        precision_duplicate_leak=duplicate_leak,
        precision_ungraded=precision_ungraded,
        precision_sample_size=len(precision_items),
        precision=precision,
        duplicate_leakage=duplicate_leakage,
        recall_found=found,
        recall_missed=missed,
        recall_ungraded=recall_ungraded,
        recall_sample_size=len(recall_items),
        recall=recall,
    )


@dataclass(frozen=True)
class LaneACoverageRow:
    source_id: str
    name: str
    status: str
    health_status: str | None
    monitored: bool
    exception_reason: str | None


@dataclass(frozen=True)
class LaneACoverage:
    rows: tuple[LaneACoverageRow, ...]

    @property
    def monitored_count(self) -> int:
        return sum(1 for row in self.rows if row.monitored)

    @property
    def total_count(self) -> int:
        return len(self.rows)


def build_lane_a_coverage(connection: Any) -> LaneACoverage:
    """9/9 (or documented-exception) Lane A coverage table, keyed off the same nine
    source_ids `shadow_bootstrap.py` flips -- the canonical launch roster -- rather
    than whatever happens to be in the DB, so a source that is missing entirely
    still shows up as a named exception instead of silently shrinking the
    denominator.
    """
    sources_by_id = {source["source_id"]: source for source in ke.list_sources(connection)}
    health_by_id = {health["source_id"]: health for health in ke.list_source_health(connection)}

    rows: list[LaneACoverageRow] = []
    for source_id in LANE_A_SOURCE_IDS:
        source = sources_by_id.get(source_id)
        health = health_by_id.get(source_id)
        health_status = health["status"] if health is not None else None
        if source is None:
            rows.append(
                LaneACoverageRow(
                    source_id=source_id,
                    name=source_id,
                    status="missing",
                    health_status=None,
                    monitored=False,
                    exception_reason="source row not present in this database",
                )
            )
            continue
        monitored = source["status"] == "active" and health_status == "healthy"
        exception_reason = None
        if not monitored:
            exception_reason = (
                f"status={source['status']!r}, last health={health_status!r} "
                "(not yet verified/scanned successfully in this database)"
            )
        rows.append(
            LaneACoverageRow(
                source_id=source_id,
                name=source["name"],
                status=source["status"],
                health_status=health_status,
                monitored=monitored,
                exception_reason=exception_reason,
            )
        )
    return LaneACoverage(rows=tuple(rows))


def _format_percent(value: float | None) -> str:
    return "N/A (no graded items)" if value is None else f"{value * 100:.1f}%"


def _format_vs_threshold(value: float | None, *, threshold: float, higher_is_better: bool) -> str:
    if value is None:
        return ""
    meets = value >= threshold if higher_is_better else value <= threshold
    comparator = ">=" if higher_is_better else "<="
    return f" (provisional threshold {comparator} {threshold * 100:.0f}%: {'meets' if meets else 'BELOW'})"


def render_shadow_report(
    *,
    report_date: str,
    lane_a_coverage: LaneACoverage,
    lane_a_metrics: LaneGradingMetrics,
    lane_b_metrics: LaneGradingMetrics,
    lane_c_metrics: LaneGradingMetrics,
    lane_d_event_count: int,
    lane_d_window_start: str,
    lane_d_window_end: str,
    person_search_calls_made: int | None,
    person_search_budget: int = PERSON_SEARCH_PER_SCAN_BUDGET,
    named_coverage_gaps: tuple[str, ...] = (NAMED_COVERAGE_GAP_SEC10_3,),
    sample_markdown_path: str = "",
    sample_checksum: str = "",
) -> str:
    lines: list[str] = [
        f"# Knowledge Edge -- Shadow Report ({report_date})",
        "",
        "Amendment §19 Phase 2 acceptance: per-lane precision/recall/duplicate-leakage "
        "measured against the frozen, Conductor-acknowledged ground-truth sample "
        f"(`{sample_markdown_path}`, sha256 `{sample_checksum}`); relative to provisional "
        "Phase 0 thresholds -- final thresholds are approved at Session 2, not by this "
        "report.",
        "",
        "## Coverage: Lane A curated podcasts",
        "",
        f"{lane_a_coverage.monitored_count}/{lane_a_coverage.total_count} monitored "
        "(active + healthy in this database) or documented exception.",
        "",
        "| source_id | name | status | last health | monitored | exception |",
        "|---|---|---|---|---|---|",
    ]
    for row in lane_a_coverage.rows:
        lines.append(
            f"| {row.source_id} | {row.name} | {row.status} | {row.health_status or 'never scanned'} "
            f"| {'yes' if row.monitored else 'no'} | {row.exception_reason or '-'} |"
        )
    lines.append("")

    lines.append("## Named coverage gaps")
    lines.append("")
    for gap in named_coverage_gaps:
        lines.append(f"- {gap}")
    lines.append("")

    lines.append("## Coverage: person-search quota usage vs §5 per-scan budget")
    lines.append("")
    if person_search_calls_made is None:
        lines.append(
            "Not yet run this scan -- person-search is a separate, Conductor-run bounded "
            "step per `docs/knowledge_edge/PACKET_2C_FIRST_SHADOW_RUN.md`; usage is "
            "reported once that step's call count is supplied to this generator."
        )
    else:
        used_percent = (person_search_calls_made / person_search_budget) * 100 if person_search_budget else 0.0
        lines.append(
            f"{person_search_calls_made}/{person_search_budget} calls used "
            f"({used_percent:.1f}% of the §5 worst-case per-scan budget)."
        )
    lines.append("")

    lines.append("## Precision / recall / duplicate leakage by lane")
    lines.append("")

    lines.append("### Lane A -- Curated Podcasts (grouping/dedup spot-check)")
    lines.append("")
    lines.append(
        f"Sample size: {lane_a_metrics.precision_sample_size} "
        f"(graded: {lane_a_metrics.precision_confirmed + lane_a_metrics.precision_rejected + lane_a_metrics.precision_duplicate_leak}, "
        f"ungraded: {lane_a_metrics.precision_ungraded})."
    )
    lines.append(
        f"- Correct grouping/dedup rate: {_format_percent(lane_a_metrics.precision)}"
    )
    lines.append(
        "- Duplicate leakage: "
        f"{_format_percent(lane_a_metrics.duplicate_leakage)}"
        f"{_format_vs_threshold(lane_a_metrics.duplicate_leakage, threshold=PROVISIONAL_DUPLICATE_LEAKAGE_THRESHOLD, higher_is_better=False)}"
    )
    lines.append("- No recall stratum for Lane A (Part 3: mechanics spot-check, not appearance recall).")
    lines.append("")

    for label, metrics in (("Lane B -- Market Voices", lane_b_metrics), ("Lane C -- Consequential Leaders", lane_c_metrics)):
        lines.append(f"### {label}")
        lines.append("")
        precision_graded = metrics.precision_confirmed + metrics.precision_rejected + metrics.precision_duplicate_leak
        lines.append(
            f"Precision sample size: {metrics.precision_sample_size} "
            f"(graded: {precision_graded}, ungraded: {metrics.precision_ungraded})."
        )
        lines.append(
            f"Recall sample size: {metrics.recall_sample_size} "
            f"(graded: {metrics.recall_found + metrics.recall_missed}, ungraded: {metrics.recall_ungraded})."
        )
        lines.append(
            f"- Precision: {_format_percent(metrics.precision)}"
            f"{_format_vs_threshold(metrics.precision, threshold=PROVISIONAL_PRECISION_THRESHOLD_BC, higher_is_better=True)}"
        )
        lines.append(
            f"- Recall: {_format_percent(metrics.recall)}"
            f"{_format_vs_threshold(metrics.recall, threshold=PROVISIONAL_RECALL_THRESHOLD_BC, higher_is_better=True)}"
        )
        lines.append(
            f"- Duplicate leakage: {_format_percent(metrics.duplicate_leakage)}"
            f"{_format_vs_threshold(metrics.duplicate_leakage, threshold=PROVISIONAL_DUPLICATE_LEAKAGE_THRESHOLD, higher_is_better=False)}"
        )
        lines.append("")

    lines.append("### Lane D -- Earnings & Corporate Events")
    lines.append("")
    lines.append(
        f"{lane_d_event_count} Tier A event(s) in window `{lane_d_window_start}`..`{lane_d_window_end}` "
        "-- 100% of the window is checked (Part 3: bounded, enumerable universe, not a sample)."
    )
    lines.append("")

    lines.append(
        "This report proves only what this packet's frozen sample and coverage data "
        "show; it does not itself constitute Session 2 threshold ratification, and it "
        "carries forward every ungraded item honestly rather than excluding it silently."
    )

    return "\n".join(lines) + "\n"
