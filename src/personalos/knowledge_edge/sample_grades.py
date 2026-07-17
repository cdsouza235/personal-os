"""P-KE-2C: the ground-truth sample's paired GRADES file (R3-04, iteration-2 redesign).

`ground_truth_sample.py` freezes an immutable sample; this module is the *separate*
artifact that carries the human judgment against it -- precision verdicts and
independently-identified recall entries -- without ever touching the frozen file's
own bytes. The split exists to fix a real design bug (audited): a checksum computed
over ungraded content can never match itself again once grading edits the *same*
file. Two artifacts, two lifecycles:

    - the FROZEN sample (`ground_truth_sample.py`): checksummed once at freeze,
      never edited again, Conductor-acknowledged via its own markdown header before
      grading begins;
    - the GRADES file (this module): created strictly after acknowledgment,
      references the frozen checksum, holds `precision_verdicts` (one entry per
      frozen precision-check item id, no missing or extra -- `render_blank_grades_file`
      pre-populates exactly this key set so a grader cannot typo an id into
      existence) plus the lane B/C recall entries (freeform -- Part 3's recall check
      requires independently-known appearances that do not exist in the frozen
      sample at all).

`shadow_report.py` is the only consumer: it requires an ACKNOWLEDGED frozen sample
(`ground_truth_sample.require_acknowledged_sample`) *and* a grades file that passes
`require_paired_grades` here before computing any metric.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from personalos.knowledge_edge.ground_truth_sample import precision_item_ids

GRADES_SCHEMA_VERSION = 1


class SampleGradingError(ValueError):
    """Raised when a grades file is malformed, or is not paired with the frozen
    sample it claims to grade (wrong/stale checksum, missing or extra item ids)."""


def _frozen_checksum(frozen_json_text: str) -> str:
    return hashlib.sha256(frozen_json_text.encode("utf-8")).hexdigest()


def render_blank_grades_file(frozen_json_text: str) -> str:
    """Pure rendering: builds a blank grades skeleton for exactly the frozen
    sample's own precision item ids (every value `null` -- ungraded) plus empty
    recall arrays, referencing the frozen file's checksum. Deterministic given the
    same `frozen_json_text`. Never writes to disk -- the CLI layer owns that, same
    convention as `ground_truth_sample.render_frozen_sample_files`.
    """
    try:
        sample_dict = json.loads(frozen_json_text)
    except json.JSONDecodeError as error:
        raise SampleGradingError(f"frozen sample file is not valid JSON: {error}") from error

    grades: dict[str, Any] = {
        "schema_version": GRADES_SCHEMA_VERSION,
        "frozen_checksum_sha256": _frozen_checksum(frozen_json_text),
        "graded_by": "",
        "graded_at": "",
        "precision_verdicts": {item_id: None for item_id in sorted(precision_item_ids(sample_dict))},
        "lane_b_recall_check_minimum": sample_dict["lane_b_recall_check_minimum"],
        "lane_b_recall_check": [],
        "lane_c_recall_check_minimum": sample_dict["lane_c_recall_check_minimum"],
        "lane_c_recall_check": [],
    }
    return json.dumps(grades, sort_keys=True, indent=2) + "\n"


def parse_grades_file(grades_json_text: str) -> dict[str, Any]:
    try:
        grades = json.loads(grades_json_text)
    except json.JSONDecodeError as error:
        raise SampleGradingError(f"grades file is not valid JSON: {error}") from error
    if not isinstance(grades, dict):
        raise SampleGradingError("grades file must contain a JSON object")
    return grades


@dataclass(frozen=True)
class PairedGrades:
    grades: dict[str, Any]
    precision_verdicts: dict[str, Any]
    lane_b_recall_check: list[dict[str, Any]]
    lane_c_recall_check: list[dict[str, Any]]


def require_paired_grades(
    *, frozen_json_text: str, acknowledged_checksum: str, grades_json_text: str
) -> PairedGrades:
    """Validates a grades file is the one Chris graded against exactly this
    acknowledged frozen sample:

        (a) the frozen file's own checksum still matches the acknowledged header's
            recorded checksum -- this is the caller's job
            (`ground_truth_sample.require_acknowledged_sample`), asserted here as a
            precondition via `acknowledged_checksum` rather than re-derived, so this
            function has exactly one reason to exist: validating the *grades* file;
        (b) the grades file's own `frozen_checksum_sha256` matches that same
            acknowledged checksum -- catches a grades file authored against a
            different (e.g. earlier, re-frozen) sample;
        (c) `precision_verdicts` covers exactly the frozen sample's precision item
            ids -- no missing id (silently excluded from the report without saying
            so) and no extra id (graded content that does not correspond to
            anything in the acknowledged sample).

    Raises `SampleGradingError` naming exactly which arm failed.
    """
    grades = parse_grades_file(grades_json_text)

    recorded = grades.get("frozen_checksum_sha256", "")
    if recorded != acknowledged_checksum:
        raise SampleGradingError(
            f"grades file references frozen checksum {recorded!r}, but the acknowledged "
            f"sample's checksum is {acknowledged_checksum!r} -- this grades file was not "
            "produced for this acknowledged sample (wrong file, or the sample was re-frozen "
            "since grading started)"
        )

    verdicts = grades.get("precision_verdicts")
    if not isinstance(verdicts, dict):
        raise SampleGradingError("grades file is missing a `precision_verdicts` object")

    sample_dict = json.loads(frozen_json_text)
    expected_ids = precision_item_ids(sample_dict)
    actual_ids = set(verdicts.keys())
    missing = expected_ids - actual_ids
    extra = actual_ids - expected_ids
    if missing or extra:
        raise SampleGradingError(
            "grades file's precision_verdicts does not cover exactly the frozen sample's "
            f"item ids -- missing: {sorted(missing)}, extra: {sorted(extra)}"
        )

    lane_b_recall_check = grades.get("lane_b_recall_check", [])
    lane_c_recall_check = grades.get("lane_c_recall_check", [])
    if not isinstance(lane_b_recall_check, list) or not isinstance(lane_c_recall_check, list):
        raise SampleGradingError(
            "grades file's lane_b_recall_check/lane_c_recall_check must be arrays"
        )

    return PairedGrades(
        grades=grades,
        precision_verdicts=verdicts,
        lane_b_recall_check=lane_b_recall_check,
        lane_c_recall_check=lane_c_recall_check,
    )
