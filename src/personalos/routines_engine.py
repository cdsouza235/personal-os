"""Pure due-today / owed computation engine (D-PO-010, P-CORE-02).

This module contains no I/O and takes no ``sqlite3.Connection``. It consumes plain
routine dicts (the shape ``state.list_routines``/``state.get_routine`` return) and
plain completion dicts (the shape ``state.list_routine_completions`` returns) and
computes, for a single as-of date, which routines are due today and what "owed"
make-up debt exists. Same inputs always produce the same output.

## Conventions this module relies on (all decisions made here, documented for the
## auditor rather than left implicit)

- ``as_of_date``: an ISO date string (``YYYY-MM-DD``) or a ``datetime.date``. Only the
  calendar date matters; there is no timezone handling in this module (the caller is
  responsible for resolving "today" in whatever timezone matters before calling in).
- ``occurrence_overrides``: a mapping keyed by ``(routine_id, due_date)`` where
  ``due_date`` is the ISO date string of the *missed* occurrence being overridden (not
  today's date). The value is a ``missed_behavior`` string from
  ``state.ROUTINE_MISSED_BEHAVIOR_TYPES``. It overrides ``missed_behavior_default`` for
  that one occurrence only.
- Only routines with ``status == "active"`` and ``enabled is True`` are due-eligible.
  Everything else (paused, archived, disabled, and routines whose ``cadence_type`` is
  ``None`` or ``"manual_only"``) is simply absent from the due-today set and never
  produces owed entries -- not an error.
- Fixed ISO week for all weekly accounting: Monday-Sunday, identified by
  ``date.isocalendar()[:2]`` (ISO year, ISO week number) so accounting resets exactly
  at the Monday boundary and correctly handles year boundaries.

### Cadence-specific conventions

- ``every_n_days``: ``cadence_config = {"n": <int>}``. The schedule anchor is the most
  recent completion's ``completed_for_date`` if the routine has ever been completed,
  else the routine's ``created_at_utc`` date. The next due date is anchor + N days.
- ``specific_days`` / ``rotating_weekday_pool``: ``cadence_config = {"days": [...]}``
  where each entry is one of the lowercase three-letter weekday abbreviations
  ``"mon", "tue", "wed", "thu", "fri", "sat", "sun"``.
- ``x_times_per_week``, ``weekly_target_count``, and the baseline PRD ``"weekly"``
  cadence type are all implemented identically (N completions anywhere in the current
  ISO week, order-independent): N comes from ``routine["weekly_target"]`` (preferred,
  first-class column), falling back to ``cadence_config["target"]`` if
  ``weekly_target`` is ``None``. ``"weekly"`` additionally defaults N to 1 if neither is
  set, since D-PO-010/PRD do not otherwise define its parameters and the most natural
  reading of a bare "weekly" cadence is "once a week." This default-to-1 behavior for
  ``"weekly"`` is a documented gap-fill, not a decision extracted from D-PO-010 (which
  does not describe ``"weekly"``'s parameters at all) -- flagged in the handoff.
- ``weekly_target_reps``: same weekly-window shape as above, but the quantity summed
  is reps, not completion count. Each completion's contribution is
  ``completion["metadata"].get("reps", 0)``. The weekly target N again comes from
  ``routine["weekly_target"]`` (preferred) falling back to ``cadence_config["target"]``.
- ``rotating_sequence`` / ``rotating_weekday_pool``: pool membership = all *active,
  enabled* routines sharing the same ``rotation_group`` value. Pool order is
  ``sorted(members, key=lambda r: r["routine_id"])`` -- deterministic without adding any
  new schema. ``rotating_sequence``'s pool has an occurrence every calendar day;
  ``rotating_weekday_pool``'s pool has an occurrence only on the weekdays named in the
  *first* pool member's ``cadence_config["days"]`` (all members of one rotation_group
  are assumed to share the same cadence_type/cadence_config; mixing is undefined). The
  pool advances one member per *resolved* occurrence (a real completion by any pool
  member on that date, or a missed occurrence resolved by ``skip_and_continue``,
  ``bump_schedule_by_one_day``, ``carry_forward_within_week``, or
  ``escalate_to_review``). ``combine_with_next`` freezes the pool: the same member stays
  "next" until the occurrence is actually completed.
- Weekly-target cadence types (``x_times_per_week``, ``weekly_target_count``,
  ``weekly_target_reps``, ``"weekly"``) do NOT use ``missed_behavior_default`` /
  ``occurrence_overrides`` at all. Their only "owed" concept is the current week's
  shortfall (see below); D-PO-010 does not define a per-day missed-occurrence semantic
  for a cadence whose due-ness is defined week-wide, so this scope boundary is a
  documented decision, not an oversight.

## Missed-behavior conventions (apply to daily/weekdays/specific_days/every_n_days/
## rotating_sequence/rotating_weekday_pool only -- see above)

A past due date (before ``as_of_date``) with no completion recorded for that exact
date is "missed." ``missed_behavior_default`` (or ``occurrence_overrides`` for that one
occurrence) decides what happens:

- ``combine_with_next``: no owed entry. For calendar-fixed cadences (daily/weekdays/
  specific_days) this is a pure no-op (those are due on their calendar day regardless of
  history). For schedule-pointer cadences (``every_n_days``, rotation pools) the
  schedule does not advance past the miss -- the obligation folds into whatever the
  next occurrence is (rolls the routine to due-every-day-until-completed for
  ``every_n_days``; freezes the current pool member for rotation cadences).
- ``bump_schedule_by_one_day``: no owed entry. For ``every_n_days``, the schedule
  pointer resolves at the missed date + 1 day instead of the missed date itself,
  shifting every subsequent due date one day later. For calendar-fixed cadences this
  has no observable effect (they have no schedule pointer to shift). For rotation
  pools it resolves the occurrence (pool advances) same as ``skip_and_continue`` --
  documented simplification, see handoff.
- ``carry_forward_within_week``: no schedule change (resolves/advances the same as
  ``skip_and_continue``), but appends an ``OwedEntry(kind="missed_occurrence")`` IF the
  missed date's ISO week matches ``as_of_date``'s ISO week. Once ``as_of_date`` moves to
  a new ISO week the entry stops appearing (bounded to the week it was missed in, not
  carried further) -- this is a live recomputation, not a stored decay.
- ``skip_and_continue``: no owed entry, schedule/pool advances past the miss as if it
  had resolved on time.
- ``escalate_to_review``: no schedule change (resolves/advances), but appends an
  ``OwedEntry(kind="missed_occurrence", missed_behavior="escalate_to_review")``
  unconditionally (not bounded to a week) for as long as that exact due date remains
  uncompleted. This is the escalation signal: an owed entry whose ``missed_behavior``
  field equals ``"escalate_to_review"``. It clears itself the moment a completion with
  ``completed_for_date`` equal to that exact missed date is recorded (even if recorded
  late), since "missed" is always evaluated as "no completion for this exact date."

## Return shape

``compute_due_and_owed`` returns a ``DueAndOwed``:

- ``due_today``: sorted ``list[str]`` of due routine_ids for ``as_of_date``.
- ``owed``: ``list[OwedEntry]``, sorted deterministically. Two disjoint kinds:
  - ``kind="missed_occurrence"``: a specific missed past due date that its
    missed-behavior handling decided to surface (``carry_forward_within_week``,
    bounded to the week, or ``escalate_to_review``, unbounded). Fields used:
    ``routine_id``, ``due_date`` (ISO date of the missed occurrence),
    ``missed_behavior``.
  - ``kind="weekly_shortfall"``: a weekly-target routine that has not yet met its
    target for the ISO week containing ``as_of_date``. Fields used: ``routine_id``,
    ``week_start`` (ISO date of that week's Monday), ``amount`` (shortfall quantity),
    ``unit`` (``"count"`` for x_times_per_week/weekly_target_count/weekly,
    ``"reps"`` for weekly_target_reps).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

_WEEKDAY_ABBREVIATIONS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_WEEKLY_TARGET_COUNT_CADENCE_TYPES = ("x_times_per_week", "weekly_target_count", "weekly")
_ROTATION_CADENCE_TYPES = ("rotating_sequence", "rotating_weekday_pool")
_CALENDAR_FIXED_CADENCE_TYPES = ("daily", "weekdays", "specific_days")
_SCHEDULE_RESOLVING_BEHAVIORS = (
    "skip_and_continue",
    "bump_schedule_by_one_day",
    "carry_forward_within_week",
    "escalate_to_review",
)


@dataclass(frozen=True)
class OwedEntry:
    """One unit of "owed" make-up debt. See module docstring for field usage per kind."""

    routine_id: str
    kind: str
    due_date: str | None = None
    missed_behavior: str | None = None
    week_start: str | None = None
    amount: int | None = None
    unit: str | None = None


@dataclass(frozen=True)
class DueAndOwed:
    due_today: list[str]
    owed: list[OwedEntry]


def compute_due_and_owed(
    routines: Sequence[Mapping[str, Any]],
    completions: Sequence[Mapping[str, Any]],
    *,
    as_of_date: str | date,
    occurrence_overrides: Mapping[tuple[str, str], str] | None = None,
) -> DueAndOwed:
    as_of = _to_date(as_of_date)
    overrides: dict[tuple[str, str], str] = dict(occurrence_overrides or {})

    completions_by_routine: dict[str, list[Mapping[str, Any]]] = {}
    for completion in completions:
        completions_by_routine.setdefault(completion["routine_id"], []).append(completion)

    active_routines = [
        routine
        for routine in routines
        if routine["status"] == "active" and routine["enabled"] is True
    ]

    due_today: set[str] = set()
    owed: list[OwedEntry] = []

    rotation_groups: dict[str, list[Mapping[str, Any]]] = {}
    for routine in active_routines:
        if routine["cadence_type"] in _ROTATION_CADENCE_TYPES and routine.get("rotation_group"):
            rotation_groups.setdefault(routine["rotation_group"], []).append(routine)

    rotation_member_ids = {
        routine["routine_id"] for members in rotation_groups.values() for routine in members
    }

    for members in rotation_groups.values():
        pool_due, pool_owed = _rotation_due_and_owed(
            members, completions_by_routine, as_of, overrides
        )
        due_today |= pool_due
        owed.extend(pool_owed)

    for routine in active_routines:
        routine_id = routine["routine_id"]
        if routine_id in rotation_member_ids:
            continue
        cadence_type = routine["cadence_type"]
        if cadence_type is None or cadence_type == "manual_only":
            continue

        routine_completions = completions_by_routine.get(routine_id, [])
        completed_dates = {_to_date(c["completed_for_date"]) for c in routine_completions}

        if cadence_type in _CALENDAR_FIXED_CADENCE_TYPES:
            is_due, entries = _calendar_due_and_owed(routine, completed_dates, as_of, overrides)
            if is_due:
                due_today.add(routine_id)
            owed.extend(entries)
        elif cadence_type == "every_n_days":
            is_due, entries = _every_n_days_due_and_owed(
                routine, completed_dates, as_of, overrides
            )
            if is_due:
                due_today.add(routine_id)
            owed.extend(entries)
        elif cadence_type in _WEEKLY_TARGET_COUNT_CADENCE_TYPES:
            is_due, entry = _weekly_target_count_due_and_owed(routine, routine_completions, as_of)
            if is_due:
                due_today.add(routine_id)
            if entry is not None:
                owed.append(entry)
        elif cadence_type == "weekly_target_reps":
            is_due, entry = _weekly_target_reps_due_and_owed(
                routine, routine_completions, as_of
            )
            if is_due:
                due_today.add(routine_id)
            if entry is not None:
                owed.append(entry)
        else:
            raise ValueError(f"unsupported cadence_type: {cadence_type!r}")

    owed.sort(key=lambda entry: (entry.routine_id, entry.kind, entry.due_date or "", entry.week_start or ""))
    return DueAndOwed(due_today=sorted(due_today), owed=owed)


def _to_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _creation_date(routine: Mapping[str, Any]) -> date:
    return datetime.fromisoformat(routine["created_at_utc"]).date()


def _iso_week_key(value: date) -> tuple[int, int]:
    iso_year, iso_week, _ = value.isocalendar()
    return (iso_year, iso_week)


def _week_bounds(value: date) -> tuple[date, date]:
    monday = value - timedelta(days=value.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _weekday_abbrev(value: date) -> str:
    return _WEEKDAY_ABBREVIATIONS[value.weekday()]


def _is_calendar_due(routine: Mapping[str, Any], value: date) -> bool:
    cadence_type = routine["cadence_type"]
    if cadence_type == "daily":
        return True
    if cadence_type == "weekdays":
        return value.weekday() < 5
    if cadence_type == "specific_days":
        days = set((routine.get("cadence_config") or {}).get("days", []))
        return _weekday_abbrev(value) in days
    raise ValueError(f"not a calendar-fixed cadence_type: {cadence_type!r}")


def _owed_entry_for_missed(
    routine_id: str, due_date: date, behavior: str | None, as_of: date
) -> OwedEntry | None:
    if behavior == "carry_forward_within_week":
        if _iso_week_key(due_date) == _iso_week_key(as_of):
            return OwedEntry(
                routine_id=routine_id,
                kind="missed_occurrence",
                due_date=due_date.isoformat(),
                missed_behavior=behavior,
            )
        return None
    if behavior == "escalate_to_review":
        return OwedEntry(
            routine_id=routine_id,
            kind="missed_occurrence",
            due_date=due_date.isoformat(),
            missed_behavior=behavior,
        )
    return None


def _calendar_due_and_owed(
    routine: Mapping[str, Any],
    completed_dates: set[date],
    as_of: date,
    overrides: Mapping[tuple[str, str], str],
) -> tuple[bool, list[OwedEntry]]:
    routine_id = routine["routine_id"]
    is_due_today = _is_calendar_due(routine, as_of) and as_of not in completed_dates

    owed: list[OwedEntry] = []
    cursor = _creation_date(routine)
    while cursor < as_of:
        if _is_calendar_due(routine, cursor) and cursor not in completed_dates:
            behavior = overrides.get(
                (routine_id, cursor.isoformat()), routine.get("missed_behavior_default")
            )
            entry = _owed_entry_for_missed(routine_id, cursor, behavior, as_of)
            if entry is not None:
                owed.append(entry)
        cursor += timedelta(days=1)
    return is_due_today, owed


def _every_n_days_due_and_owed(
    routine: Mapping[str, Any],
    completed_dates: set[date],
    as_of: date,
    overrides: Mapping[tuple[str, str], str],
) -> tuple[bool, list[OwedEntry]]:
    routine_id = routine["routine_id"]
    n = int((routine.get("cadence_config") or {})["n"])
    pointer = max(completed_dates) if completed_dates else _creation_date(routine)

    owed: list[OwedEntry] = []
    while True:
        candidate = pointer + timedelta(days=n)
        if candidate > as_of:
            return False, owed
        if candidate in completed_dates:
            pointer = candidate
            continue
        if candidate == as_of:
            return True, owed

        behavior = overrides.get(
            (routine_id, candidate.isoformat()), routine.get("missed_behavior_default")
        )
        if behavior == "skip_and_continue":
            pointer = candidate
        elif behavior == "bump_schedule_by_one_day":
            pointer = candidate + timedelta(days=1)
        elif behavior == "carry_forward_within_week":
            pointer = candidate
            entry = _owed_entry_for_missed(routine_id, candidate, behavior, as_of)
            if entry is not None:
                owed.append(entry)
        elif behavior == "escalate_to_review":
            pointer = candidate
            entry = _owed_entry_for_missed(routine_id, candidate, behavior, as_of)
            if entry is not None:
                owed.append(entry)
        else:
            # combine_with_next (or no behavior configured): pileup, due every day
            # from here until an actual completion resolves it.
            return True, owed


def _weekly_target_count_due_and_owed(
    routine: Mapping[str, Any],
    routine_completions: Sequence[Mapping[str, Any]],
    as_of: date,
) -> tuple[bool, OwedEntry | None]:
    monday, sunday = _week_bounds(as_of)
    target = routine.get("weekly_target")
    if target is None:
        target = (routine.get("cadence_config") or {}).get("target")
    if target is None and routine["cadence_type"] == "weekly":
        target = 1
    if target is None:
        raise ValueError(
            f"routine {routine['routine_id']!r} has no weekly_target for cadence "
            f"{routine['cadence_type']!r}"
        )

    completed_this_week = sum(
        1
        for completion in routine_completions
        if monday <= _to_date(completion["completed_for_date"]) <= sunday
    )
    shortfall = target - completed_this_week
    if shortfall <= 0:
        return False, None
    return True, OwedEntry(
        routine_id=routine["routine_id"],
        kind="weekly_shortfall",
        week_start=monday.isoformat(),
        amount=shortfall,
        unit="count",
    )


def _weekly_target_reps_due_and_owed(
    routine: Mapping[str, Any],
    routine_completions: Sequence[Mapping[str, Any]],
    as_of: date,
) -> tuple[bool, OwedEntry | None]:
    monday, sunday = _week_bounds(as_of)
    target = routine.get("weekly_target")
    if target is None:
        target = (routine.get("cadence_config") or {}).get("target")
    if target is None:
        raise ValueError(
            f"routine {routine['routine_id']!r} has no weekly_target for weekly_target_reps"
        )

    reps_this_week = 0
    for completion in routine_completions:
        completed_for = _to_date(completion["completed_for_date"])
        if monday <= completed_for <= sunday:
            reps_this_week += int((completion.get("metadata") or {}).get("reps", 0))

    shortfall = target - reps_this_week
    if shortfall <= 0:
        return False, None
    return True, OwedEntry(
        routine_id=routine["routine_id"],
        kind="weekly_shortfall",
        week_start=monday.isoformat(),
        amount=shortfall,
        unit="reps",
    )


def _pool_calendar_due(representative: Mapping[str, Any], value: date) -> bool:
    cadence_type = representative["cadence_type"]
    if cadence_type == "rotating_sequence":
        return True
    if cadence_type == "rotating_weekday_pool":
        days = set((representative.get("cadence_config") or {}).get("days", []))
        return _weekday_abbrev(value) in days
    raise ValueError(f"not a rotation cadence_type: {cadence_type!r}")


def _rotation_due_and_owed(
    members: Sequence[Mapping[str, Any]],
    completions_by_routine: Mapping[str, Sequence[Mapping[str, Any]]],
    as_of: date,
    overrides: Mapping[tuple[str, str], str],
) -> tuple[set[str], list[OwedEntry]]:
    members_sorted = sorted(members, key=lambda routine: routine["routine_id"])
    size = len(members_sorted)
    representative = members_sorted[0]

    pool_completed_dates: set[date] = set()
    for member in members_sorted:
        for completion in completions_by_routine.get(member["routine_id"], []):
            pool_completed_dates.add(_to_date(completion["completed_for_date"]))

    cursor = min(_creation_date(member) for member in members_sorted)
    resolved_count = 0
    owed: list[OwedEntry] = []

    while cursor < as_of:
        if _pool_calendar_due(representative, cursor):
            member = members_sorted[resolved_count % size]
            if cursor in pool_completed_dates:
                resolved_count += 1
            else:
                behavior = overrides.get(
                    (member["routine_id"], cursor.isoformat()),
                    member.get("missed_behavior_default"),
                )
                if behavior in _SCHEDULE_RESOLVING_BEHAVIORS:
                    resolved_count += 1
                    entry = _owed_entry_for_missed(
                        member["routine_id"], cursor, behavior, as_of
                    )
                    if entry is not None:
                        owed.append(entry)
                # combine_with_next (or unset): pool frozen, same member stays next.
        cursor += timedelta(days=1)

    due: set[str] = set()
    if _pool_calendar_due(representative, as_of) and as_of not in pool_completed_dates:
        due.add(members_sorted[resolved_count % size]["routine_id"])
    return due, owed
