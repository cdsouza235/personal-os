"""Exhaustive table-driven tests for the pure cadence engine (P-CORE-02, D-PO-010).

These tests build plain routine/completion dicts directly (matching the shapes
``state.list_routines``/``state.list_routine_completions`` return) rather than going
through a database, since ``routines_engine`` is a pure function with no I/O.
"""

from __future__ import annotations

import copy
import unittest
from datetime import date, timedelta

from personalos.routines_engine import OwedEntry, compute_due_and_owed


def make_routine(
    routine_id,
    *,
    cadence_type,
    name=None,
    status="active",
    enabled=True,
    cadence_config=None,
    missed_behavior_default="combine_with_next",
    rotation_group=None,
    weekly_target=None,
    created_at_utc="2026-01-01T00:00:00+00:00",
):
    return {
        "routine_id": routine_id,
        "name": name or routine_id,
        "status": status,
        "enabled": enabled,
        "settings": {},
        "notes": "",
        "created_at_utc": created_at_utc,
        "updated_at_utc": created_at_utc,
        "cadence_type": cadence_type,
        "cadence_config": cadence_config or {},
        "missed_behavior_default": missed_behavior_default,
        "rotation_group": rotation_group,
        "weekly_target": weekly_target,
    }


def make_completion(routine_id, completed_for_date, *, metadata=None, completion_id=None):
    return {
        "completion_id": completion_id or f"{routine_id}-{completed_for_date}",
        "routine_id": routine_id,
        "completed_for_date": completed_for_date,
        "completed_at_utc": f"{completed_for_date}T12:00:00+00:00",
        "source": "test",
        "metadata": metadata or {},
        "created_at_utc": f"{completed_for_date}T12:00:00+00:00",
    }


def date_range(start: str, end: str, *, skip: frozenset[str] = frozenset()) -> list[str]:
    cursor = date.fromisoformat(start)
    stop = date.fromisoformat(end)
    out = []
    while cursor <= stop:
        iso = cursor.isoformat()
        if iso not in skip:
            out.append(iso)
        cursor += timedelta(days=1)
    return out


# Week 28 of 2026: Mon 2026-07-06 .. Sun 2026-07-12. Week 27: Mon 2026-06-29 .. Sun 2026-07-05.
# Week 29: Mon 2026-07-13 .. Sun 2026-07-19.
MON_W28 = "2026-07-06"
TUE_W28 = "2026-07-07"
WED_W28 = "2026-07-08"
THU_W28 = "2026-07-09"
FRI_W28 = "2026-07-10"
SAT_W28 = "2026-07-11"
SUN_W28 = "2026-07-12"
MON_W29 = "2026-07-13"
MON_W27 = "2026-06-29"


class StatusFilteringMatrixMixin:
    """Mixin providing a reusable "disabled/paused/archived never due" check."""

    def assert_never_due_for_inactive_states(self, routine_kwargs, *, as_of):
        for status, enabled in (("active", False), ("paused", True), ("archived", True)):
            with self.subTest(status=status, enabled=enabled):
                routine = make_routine(
                    "r-inactive", status=status, enabled=enabled, **routine_kwargs
                )
                result = compute_due_and_owed([routine], [], as_of_date=as_of)
                self.assertEqual(result.due_today, [])


class DailyCadenceTests(unittest.TestCase, StatusFilteringMatrixMixin):
    def test_due_when_eligible(self):
        routine = make_routine("daily-1", cadence_type="daily")
        result = compute_due_and_owed([routine], [], as_of_date=THU_W28)
        self.assertEqual(result.due_today, ["daily-1"])

    def test_not_due_when_already_completed_today(self):
        routine = make_routine("daily-1", cadence_type="daily")
        completion = make_completion("daily-1", THU_W28)
        result = compute_due_and_owed([routine], [completion], as_of_date=THU_W28)
        self.assertEqual(result.due_today, [])

    def test_not_due_when_inactive(self):
        self.assert_never_due_for_inactive_states({"cadence_type": "daily"}, as_of=THU_W28)


class WeekdaysCadenceTests(unittest.TestCase, StatusFilteringMatrixMixin):
    def test_due_on_weekday(self):
        routine = make_routine("weekdays-1", cadence_type="weekdays")
        result = compute_due_and_owed([routine], [], as_of_date=THU_W28)
        self.assertEqual(result.due_today, ["weekdays-1"])

    def test_not_due_on_weekend(self):
        routine = make_routine("weekdays-1", cadence_type="weekdays")
        result = compute_due_and_owed([routine], [], as_of_date=SAT_W28)
        self.assertEqual(result.due_today, [])

    def test_not_due_when_already_completed_today(self):
        routine = make_routine("weekdays-1", cadence_type="weekdays")
        completion = make_completion("weekdays-1", THU_W28)
        result = compute_due_and_owed([routine], [completion], as_of_date=THU_W28)
        self.assertEqual(result.due_today, [])

    def test_not_due_when_inactive(self):
        self.assert_never_due_for_inactive_states({"cadence_type": "weekdays"}, as_of=THU_W28)


class SpecificDaysCadenceTests(unittest.TestCase, StatusFilteringMatrixMixin):
    def test_due_on_configured_day(self):
        routine = make_routine(
            "specific-1", cadence_type="specific_days", cadence_config={"days": ["mon", "thu"]}
        )
        result = compute_due_and_owed([routine], [], as_of_date=THU_W28)
        self.assertEqual(result.due_today, ["specific-1"])

    def test_not_due_on_unconfigured_day(self):
        routine = make_routine(
            "specific-1", cadence_type="specific_days", cadence_config={"days": ["mon", "thu"]}
        )
        result = compute_due_and_owed([routine], [], as_of_date=FRI_W28)
        self.assertEqual(result.due_today, [])

    def test_not_due_when_already_completed_today(self):
        routine = make_routine(
            "specific-1", cadence_type="specific_days", cadence_config={"days": ["mon", "thu"]}
        )
        completion = make_completion("specific-1", THU_W28)
        result = compute_due_and_owed([routine], [completion], as_of_date=THU_W28)
        self.assertEqual(result.due_today, [])

    def test_not_due_when_inactive(self):
        self.assert_never_due_for_inactive_states(
            {"cadence_type": "specific_days", "cadence_config": {"days": ["mon", "thu"]}},
            as_of=THU_W28,
        )


class EveryNDaysCadenceTests(unittest.TestCase, StatusFilteringMatrixMixin):
    def test_due_on_schedule_from_creation_anchor(self):
        routine = make_routine(
            "n3-1",
            cadence_type="every_n_days",
            cadence_config={"n": 3},
            created_at_utc="2026-06-01T00:00:00+00:00",
        )
        result = compute_due_and_owed([routine], [], as_of_date="2026-06-04")
        self.assertEqual(result.due_today, ["n3-1"])

    def test_not_due_before_schedule(self):
        routine = make_routine(
            "n3-1",
            cadence_type="every_n_days",
            cadence_config={"n": 3},
            created_at_utc="2026-06-01T00:00:00+00:00",
        )
        result = compute_due_and_owed([routine], [], as_of_date="2026-06-03")
        self.assertEqual(result.due_today, [])

    def test_due_on_schedule_from_last_completion_anchor(self):
        routine = make_routine(
            "n3-1",
            cadence_type="every_n_days",
            cadence_config={"n": 3},
            created_at_utc="2026-06-01T00:00:00+00:00",
        )
        completion = make_completion("n3-1", "2026-06-04")
        result = compute_due_and_owed([routine], [completion], as_of_date="2026-06-07")
        self.assertEqual(result.due_today, ["n3-1"])

    def test_not_due_when_already_completed_today(self):
        routine = make_routine(
            "n3-1",
            cadence_type="every_n_days",
            cadence_config={"n": 3},
            created_at_utc="2026-06-01T00:00:00+00:00",
        )
        completion = make_completion("n3-1", "2026-06-04")
        result = compute_due_and_owed([routine], [completion], as_of_date="2026-06-04")
        self.assertEqual(result.due_today, [])

    def test_not_due_when_inactive(self):
        self.assert_never_due_for_inactive_states(
            {
                "cadence_type": "every_n_days",
                "cadence_config": {"n": 3},
                "created_at_utc": "2026-06-01T00:00:00+00:00",
            },
            as_of="2026-06-04",
        )


class ManualOnlyCadenceTests(unittest.TestCase):
    def test_never_appears_in_due_today(self):
        routine = make_routine("manual-1", cadence_type="manual_only")
        result = compute_due_and_owed([routine], [], as_of_date=THU_W28)
        self.assertEqual(result.due_today, [])
        self.assertEqual(result.owed, [])

    def test_never_due_even_with_long_history_of_no_completions(self):
        routine = make_routine(
            "manual-1", cadence_type="manual_only", created_at_utc="2020-01-01T00:00:00+00:00"
        )
        result = compute_due_and_owed([routine], [], as_of_date=THU_W28)
        self.assertEqual(result.due_today, [])
        self.assertEqual(result.owed, [])


class WeeklyTargetCountFamilyTests(unittest.TestCase, StatusFilteringMatrixMixin):
    """x_times_per_week, weekly_target_count, and the baseline "weekly" type share logic."""

    def test_due_when_shortfall_remains(self):
        for cadence_type in ("x_times_per_week", "weekly_target_count"):
            with self.subTest(cadence_type=cadence_type):
                routine = make_routine(cadence_type + "-1", cadence_type=cadence_type, weekly_target=4)
                completions = [
                    make_completion(routine["routine_id"], MON_W28),
                ]
                result = compute_due_and_owed([routine], completions, as_of_date=WED_W28)
                self.assertEqual(result.due_today, [routine["routine_id"]])
                self.assertEqual(
                    result.owed,
                    [
                        OwedEntry(
                            routine_id=routine["routine_id"],
                            kind="weekly_shortfall",
                            week_start=MON_W28,
                            amount=3,
                            unit="count",
                        )
                    ],
                )

    def test_not_due_when_target_met_this_week(self):
        routine = make_routine("wtc-1", cadence_type="weekly_target_count", weekly_target=2)
        completions = [
            make_completion("wtc-1", MON_W28),
            make_completion("wtc-1", TUE_W28),
        ]
        result = compute_due_and_owed([routine], completions, as_of_date=WED_W28)
        self.assertEqual(result.due_today, [])
        self.assertEqual(result.owed, [])

    def test_not_due_when_completed_today_reaches_target(self):
        routine = make_routine("wtc-1", cadence_type="weekly_target_count", weekly_target=1)
        completion = make_completion("wtc-1", THU_W28)
        result = compute_due_and_owed([routine], [completion], as_of_date=THU_W28)
        self.assertEqual(result.due_today, [])

    def test_monday_boundary_reset_excludes_last_week_completions(self):
        routine = make_routine("wtc-1", cadence_type="weekly_target_count", weekly_target=1)
        # Completion is from last week (Sunday of week 27); trailing-7-days would
        # include it (only 3 days before Wed W28) but the fixed ISO week must not.
        completion = make_completion("wtc-1", "2026-07-05")
        result = compute_due_and_owed([routine], [completion], as_of_date=WED_W28)
        self.assertEqual(result.due_today, ["wtc-1"])
        self.assertEqual(
            result.owed,
            [OwedEntry(routine_id="wtc-1", kind="weekly_shortfall", week_start=MON_W28, amount=1, unit="count")],
        )

    def test_weekly_cadence_defaults_target_to_one(self):
        routine = make_routine("weekly-1", cadence_type="weekly", weekly_target=None)
        result = compute_due_and_owed([routine], [], as_of_date=WED_W28)
        self.assertEqual(result.due_today, ["weekly-1"])
        completion = make_completion("weekly-1", WED_W28)
        result_after = compute_due_and_owed([routine], [completion], as_of_date=WED_W28)
        self.assertEqual(result_after.due_today, [])

    def test_same_day_duplicate_completions_each_count_toward_target(self):
        # Two completions on the same calendar date must both count toward the
        # weekly target (e.g. two Reading sessions in one day). A dedup-by-date
        # bug would undercount this as 2 completions instead of 3.
        routine = make_routine("wtc-1", cadence_type="weekly_target_count", weekly_target=4)
        completions = [
            make_completion("wtc-1", MON_W28, completion_id="wtc-1-mon-a"),
            make_completion("wtc-1", MON_W28, completion_id="wtc-1-mon-b"),
            make_completion("wtc-1", TUE_W28),
        ]
        result = compute_due_and_owed([routine], completions, as_of_date=WED_W28)
        self.assertEqual(result.due_today, ["wtc-1"])
        self.assertEqual(
            result.owed,
            [OwedEntry(routine_id="wtc-1", kind="weekly_shortfall", week_start=MON_W28, amount=1, unit="count")],
        )

    def test_not_due_when_inactive(self):
        self.assert_never_due_for_inactive_states(
            {"cadence_type": "weekly_target_count", "weekly_target": 3}, as_of=WED_W28
        )


class WeeklyTargetRepsCadenceTests(unittest.TestCase, StatusFilteringMatrixMixin):
    def test_due_when_reps_shortfall_remains(self):
        routine = make_routine("gtg-pushups", cadence_type="weekly_target_reps", weekly_target=45)
        completions = [make_completion("gtg-pushups", MON_W28, metadata={"reps": 15})]
        result = compute_due_and_owed([routine], completions, as_of_date=WED_W28)
        self.assertEqual(result.due_today, ["gtg-pushups"])
        self.assertEqual(
            result.owed,
            [
                OwedEntry(
                    routine_id="gtg-pushups",
                    kind="weekly_shortfall",
                    week_start=MON_W28,
                    amount=30,
                    unit="reps",
                )
            ],
        )

    def test_not_due_when_reps_target_met(self):
        routine = make_routine("gtg-pushups", cadence_type="weekly_target_reps", weekly_target=45)
        completions = [
            make_completion("gtg-pushups", MON_W28, metadata={"reps": 20}),
            make_completion("gtg-pushups", TUE_W28, metadata={"reps": 25}),
        ]
        result = compute_due_and_owed([routine], completions, as_of_date=WED_W28)
        self.assertEqual(result.due_today, [])
        self.assertEqual(result.owed, [])

    def test_not_due_when_already_completed_today_reaches_target(self):
        routine = make_routine("gtg-pushups", cadence_type="weekly_target_reps", weekly_target=10)
        completion = make_completion("gtg-pushups", THU_W28, metadata={"reps": 10})
        result = compute_due_and_owed([routine], [completion], as_of_date=THU_W28)
        self.assertEqual(result.due_today, [])

    def test_monday_boundary_reset_excludes_last_week_reps(self):
        routine = make_routine("gtg-pushups", cadence_type="weekly_target_reps", weekly_target=45)
        completion = make_completion("gtg-pushups", "2026-07-05", metadata={"reps": 45})
        result = compute_due_and_owed([routine], [completion], as_of_date=WED_W28)
        self.assertEqual(result.due_today, ["gtg-pushups"])
        self.assertEqual(result.owed[0].amount, 45)

    def test_missing_reps_key_counts_as_zero(self):
        routine = make_routine("gtg-pushups", cadence_type="weekly_target_reps", weekly_target=45)
        completion = make_completion("gtg-pushups", MON_W28, metadata={})
        result = compute_due_and_owed([routine], [completion], as_of_date=WED_W28)
        self.assertEqual(result.owed[0].amount, 45)

    def test_not_due_when_inactive(self):
        self.assert_never_due_for_inactive_states(
            {"cadence_type": "weekly_target_reps", "weekly_target": 45}, as_of=WED_W28
        )


class RotatingSequenceCadenceTests(unittest.TestCase, StatusFilteringMatrixMixin):
    def _pool(self, missed_behavior_default="combine_with_next"):
        return [
            make_routine(
                rid,
                cadence_type="rotating_sequence",
                rotation_group="cleaning-test",
                missed_behavior_default=missed_behavior_default,
                created_at_utc=f"{MON_W28}T00:00:00+00:00",
            )
            for rid in ("clean-a", "clean-b", "clean-c")
        ]

    def test_only_next_member_is_due(self):
        result = compute_due_and_owed(self._pool(), [], as_of_date=MON_W28)
        self.assertEqual(result.due_today, ["clean-a"])

    def test_advances_after_completion(self):
        pool = self._pool()
        completions = [make_completion("clean-a", MON_W28)]
        result = compute_due_and_owed(pool, completions, as_of_date=TUE_W28)
        self.assertEqual(result.due_today, ["clean-b"])

    def test_advances_across_multiple_occurrences_and_wraps(self):
        pool = self._pool()
        completions = [
            make_completion("clean-a", MON_W28),
            make_completion("clean-b", TUE_W28),
            make_completion("clean-c", WED_W28),
        ]
        result = compute_due_and_owed(pool, completions, as_of_date=THU_W28)
        self.assertEqual(result.due_today, ["clean-a"])

    def test_not_due_when_inactive(self):
        # A lone inactive pool member is simply excluded from the group.
        routine = make_routine(
            "solo-inactive",
            cadence_type="rotating_sequence",
            rotation_group="solo-group",
            status="paused",
            created_at_utc=f"{MON_W28}T00:00:00+00:00",
        )
        result = compute_due_and_owed([routine], [], as_of_date=MON_W28)
        self.assertEqual(result.due_today, [])


class RotatingWeekdayPoolCadenceTests(unittest.TestCase):
    def _pool(self, missed_behavior_default="combine_with_next"):
        return [
            make_routine(
                rid,
                cadence_type="rotating_weekday_pool",
                cadence_config={"days": ["mon", "tue", "wed", "thu", "fri"]},
                rotation_group="pool-test",
                missed_behavior_default=missed_behavior_default,
                created_at_utc=f"{MON_W28}T00:00:00+00:00",
            )
            for rid in ("gym-a", "gym-b")
        ]

    def test_not_due_on_weekend(self):
        result = compute_due_and_owed(self._pool(), [], as_of_date=SAT_W28)
        self.assertEqual(result.due_today, [])
        self.assertEqual(result.owed, [])

    def test_advances_only_on_configured_weekdays(self):
        pool = self._pool()
        completions = [
            make_completion("gym-a", MON_W28),
            make_completion("gym-b", TUE_W28),
            make_completion("gym-a", WED_W28),
            make_completion("gym-b", THU_W28),
        ]
        result = compute_due_and_owed(pool, completions, as_of_date=FRI_W28)
        self.assertEqual(result.due_today, ["gym-a"])

    def test_not_due_when_disabled(self):
        pool = self._pool()
        pool[0]["enabled"] = False
        pool[1]["enabled"] = False
        result = compute_due_and_owed(pool, [], as_of_date=MON_W28)
        self.assertEqual(result.due_today, [])


class MissedBehaviorTests(unittest.TestCase):
    """One test per missed_behavior type proving its distinct handling."""

    def test_combine_with_next_piles_up_with_no_owed_entry(self):
        routine = make_routine(
            "n3-combine",
            cadence_type="every_n_days",
            cadence_config={"n": 3},
            missed_behavior_default="combine_with_next",
            created_at_utc="2026-06-01T00:00:00+00:00",
        )
        # Natural due date is 2026-06-04; nothing is ever completed.
        result = compute_due_and_owed([routine], [], as_of_date="2026-06-05")
        self.assertEqual(result.due_today, ["n3-combine"])
        self.assertEqual(result.owed, [])
        # Still overdue days later -- the obligation folds forward, it never clears
        # itself and never produces debt.
        result_later = compute_due_and_owed([routine], [], as_of_date="2026-06-06")
        self.assertEqual(result_later.due_today, ["n3-combine"])
        self.assertEqual(result_later.owed, [])

    def test_bump_schedule_by_one_day_shifts_next_due_date(self):
        bumped = make_routine(
            "n3-bump",
            cadence_type="every_n_days",
            cadence_config={"n": 3},
            missed_behavior_default="bump_schedule_by_one_day",
            created_at_utc="2026-06-01T00:00:00+00:00",
        )
        control = make_routine(
            "n3-control",
            cadence_type="every_n_days",
            cadence_config={"n": 3},
            missed_behavior_default="combine_with_next",
            created_at_utc="2026-06-01T00:00:00+00:00",
        )
        # Natural due date 2026-06-04 is missed by both. Without bump, 06-07 would be
        # due (pileup, still overdue). With bump, the schedule shifts to 06-05 + 3 =
        # 06-08, so 06-07 is NOT due -- proving the one-day shift.
        result = compute_due_and_owed([bumped, control], [], as_of_date="2026-06-07")
        self.assertEqual(result.due_today, ["n3-control"])
        self.assertEqual(result.owed, [])

        result_shifted_date = compute_due_and_owed([bumped, control], [], as_of_date="2026-06-08")
        self.assertIn("n3-bump", result_shifted_date.due_today)

    def test_skip_and_continue_has_no_pileup_and_no_debt(self):
        skipped = make_routine(
            "n3-skip",
            cadence_type="every_n_days",
            cadence_config={"n": 3},
            missed_behavior_default="skip_and_continue",
            created_at_utc="2026-06-01T00:00:00+00:00",
        )
        control = make_routine(
            "n3-control",
            cadence_type="every_n_days",
            cadence_config={"n": 3},
            missed_behavior_default="combine_with_next",
            created_at_utc="2026-06-01T00:00:00+00:00",
        )
        # Natural due date 2026-06-04 is missed by both. skip_and_continue resumes the
        # *original* cadence (next due 06-07); combine_with_next piles up (overdue
        # every day from 06-04). On 06-05 that's the observable difference.
        result = compute_due_and_owed([skipped, control], [], as_of_date="2026-06-05")
        self.assertEqual(result.due_today, ["n3-control"])
        self.assertEqual(result.owed, [])

        result_on_schedule = compute_due_and_owed([skipped, control], [], as_of_date="2026-06-07")
        self.assertIn("n3-skip", result_on_schedule.due_today)

    def test_carry_forward_within_week_expires_at_week_boundary(self):
        completions = [
            make_completion("daily-carry", d)
            for d in date_range(MON_W28, SUN_W28, skip=frozenset({TUE_W28}))
        ]
        routine = make_routine(
            "daily-carry",
            cadence_type="daily",
            missed_behavior_default="carry_forward_within_week",
            created_at_utc=f"{MON_W28}T00:00:00+00:00",
        )

        same_week = compute_due_and_owed([routine], completions, as_of_date=THU_W28)
        self.assertEqual(
            same_week.owed,
            [
                OwedEntry(
                    routine_id="daily-carry",
                    kind="missed_occurrence",
                    due_date=TUE_W28,
                    missed_behavior="carry_forward_within_week",
                )
            ],
        )

        next_week = compute_due_and_owed([routine], completions, as_of_date=MON_W29)
        self.assertEqual(next_week.owed, [])

    def test_escalate_to_review_persists_past_week_boundary_until_resolved(self):
        completions = [
            make_completion("daily-escalate", d)
            for d in date_range(MON_W27, THU_W28, skip=frozenset({MON_W27}))
        ]
        routine = make_routine(
            "daily-escalate",
            cadence_type="daily",
            missed_behavior_default="escalate_to_review",
            created_at_utc=f"{MON_W27}T00:00:00+00:00",
        )

        result = compute_due_and_owed([routine], completions, as_of_date=THU_W28)
        self.assertEqual(
            result.owed,
            [
                OwedEntry(
                    routine_id="daily-escalate",
                    kind="missed_occurrence",
                    due_date=MON_W27,
                    missed_behavior="escalate_to_review",
                )
            ],
        )

        backfilled = completions + [make_completion("daily-escalate", MON_W27)]
        resolved = compute_due_and_owed([routine], backfilled, as_of_date=THU_W28)
        self.assertEqual(resolved.owed, [])


class OccurrenceOverrideTests(unittest.TestCase):
    def test_override_applies_only_to_targeted_routine_and_date(self):
        cleaning = make_routine(
            "cleaning-task",
            cadence_type="daily",
            missed_behavior_default="escalate_to_review",
            created_at_utc=f"{MON_W28}T00:00:00+00:00",
        )
        other = make_routine(
            "other-task",
            cadence_type="daily",
            missed_behavior_default="escalate_to_review",
            created_at_utc=f"{MON_W28}T00:00:00+00:00",
        )
        # Both routines miss both Monday and Tuesday (no completions recorded at all).
        overrides = {("cleaning-task", MON_W28): "skip_and_continue"}

        result = compute_due_and_owed(
            [cleaning, other], [], as_of_date=WED_W28, occurrence_overrides=overrides
        )

        cleaning_owed = [e for e in result.owed if e.routine_id == "cleaning-task"]
        other_owed = [e for e in result.owed if e.routine_id == "other-task"]

        # cleaning-task's Monday occurrence was overridden to skip -> no owed entry for
        # Monday, but Tuesday still uses the default (escalate) -> owed entry remains.
        self.assertEqual([e.due_date for e in cleaning_owed], [TUE_W28])

        # other-task was not targeted by the override at all -- both misses escalate.
        self.assertEqual(sorted(e.due_date for e in other_owed), [MON_W28, TUE_W28])


class SeedRoutineIntegrationTests(unittest.TestCase):
    """One integration-shaped test per D-PO-010 seed routine."""

    def test_cleaning_rotating_pool_one_per_weekday(self):
        members = [
            make_routine(
                f"cleaning-{n}",
                cadence_type="rotating_weekday_pool",
                cadence_config={"days": ["mon", "tue", "wed", "thu", "fri"]},
                rotation_group="cleaning",
                missed_behavior_default="escalate_to_review",
                created_at_utc=f"{MON_W28}T00:00:00+00:00",
            )
            for n in range(1, 6)
        ]
        result = compute_due_and_owed(members, [], as_of_date=MON_W28)
        self.assertEqual(len(result.due_today), 1)
        self.assertIn(result.due_today[0], [m["routine_id"] for m in members])

        # Chris's reply overrides the missed-cleaning-task's default handling for that
        # one occurrence, per D-PO-010's dynamic cleaning-pool mechanism.
        overrides = {(result.due_today[0], MON_W28): "skip_and_continue"}
        next_day = compute_due_and_owed(
            members, [], as_of_date=TUE_W28, occurrence_overrides=overrides
        )
        self.assertEqual(len(next_day.owed), 0)
        self.assertNotEqual(next_day.due_today[0], result.due_today[0])

    def test_reading_weekly_target_count_four_times_a_week(self):
        routine = make_routine(
            "reading", cadence_type="weekly_target_count", weekly_target=4, name="Reading"
        )
        completions = [make_completion("reading", d) for d in (MON_W28, TUE_W28, WED_W28)]
        result = compute_due_and_owed([routine], completions, as_of_date=THU_W28)
        self.assertEqual(result.due_today, ["reading"])
        self.assertEqual(result.owed[0].amount, 1)

        completions.append(make_completion("reading", THU_W28))
        met = compute_due_and_owed([routine], completions, as_of_date=THU_W28)
        self.assertEqual(met.due_today, [])

    def test_prayer_meditation_weekly_target_count_twice_a_week(self):
        routine = make_routine(
            "prayer", cadence_type="weekly_target_count", weekly_target=2, name="Prayer/Meditation"
        )
        result = compute_due_and_owed([routine], [], as_of_date=MON_W28)
        self.assertEqual(result.due_today, ["prayer"])

        completions = [make_completion("prayer", MON_W28), make_completion("prayer", TUE_W28)]
        met = compute_due_and_owed([routine], completions, as_of_date=WED_W28)
        self.assertEqual(met.due_today, [])

    def test_grease_the_groove_per_exercise_reps_target(self):
        pushups = make_routine(
            "gtg-pushups",
            cadence_type="weekly_target_reps",
            rotation_group="gtg",
            weekly_target=45,
            name="GTG Pushups",
        )
        pullups = make_routine(
            "gtg-pullups",
            cadence_type="weekly_target_reps",
            rotation_group="gtg",
            weekly_target=45,
            name="GTG Pullups",
        )
        completions = [
            make_completion("gtg-pushups", MON_W28, metadata={"reps": 45}),
            make_completion("gtg-pullups", MON_W28, metadata={"reps": 10}),
        ]
        result = compute_due_and_owed([pushups, pullups], completions, as_of_date=TUE_W28)
        # Sharing rotation_group="gtg" is a label only for this cadence type -- both
        # exercises are independently due, not gated to "one at a time."
        self.assertEqual(sorted(result.due_today), ["gtg-pullups"])
        self.assertEqual(result.owed[0].routine_id, "gtg-pullups")
        self.assertEqual(result.owed[0].amount, 35)

    def test_shutdown_review_daily_evening(self):
        routine = make_routine("shutdown-review", cadence_type="daily", name="Shutdown/Review")
        result = compute_due_and_owed([routine], [], as_of_date=THU_W28)
        self.assertEqual(result.due_today, ["shutdown-review"])

        completion = make_completion("shutdown-review", THU_W28)
        result_done = compute_due_and_owed([routine], [completion], as_of_date=THU_W28)
        self.assertEqual(result_done.due_today, [])


class PurityTests(unittest.TestCase):
    def test_deterministic_across_repeated_calls(self):
        routine = make_routine("daily-1", cadence_type="daily")
        completion = make_completion("daily-1", MON_W28)
        first = compute_due_and_owed([routine], [completion], as_of_date=THU_W28)
        second = compute_due_and_owed([routine], [completion], as_of_date=THU_W28)
        self.assertEqual(first, second)

    def test_inputs_are_not_mutated(self):
        routine = make_routine("daily-1", cadence_type="daily")
        completion = make_completion("daily-1", MON_W28)
        routines = [routine]
        completions = [completion]
        routines_before = copy.deepcopy(routines)
        completions_before = copy.deepcopy(completions)

        compute_due_and_owed(routines, completions, as_of_date=THU_W28)

        self.assertEqual(routines, routines_before)
        self.assertEqual(completions, completions_before)

    def test_accepts_date_object_as_of_date(self):
        routine = make_routine("daily-1", cadence_type="daily")
        result = compute_due_and_owed([routine], [], as_of_date=date.fromisoformat(THU_W28))
        self.assertEqual(result.due_today, ["daily-1"])


if __name__ == "__main__":
    unittest.main()
