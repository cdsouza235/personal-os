import json
import unittest

from personalos.phase14c_wide_net_calendar_bridge import (
    CalendarBridgeContractError,
    PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT,
    WideNetGoogleCalendarConnectorBridge,
    count_matching_calendar_events,
    require_explicit_calendar_matching_event_count,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
)


class Phase14CWideNetCalendarBridgeTest(unittest.TestCase):
    def test_bridge_counts_exact_marker_matches_without_logging_event_details(self) -> None:
        search_calls: list[dict[str, object]] = []
        create_calls: list[dict[str, object]] = []

        def search_events(payload: dict[str, object]) -> dict[str, object]:
            search_calls.append(dict(payload))
            return {
                "items": [
                    {"summary": PHASE14C_WIDE_NET_REHEARSAL_MARKER, "id": "hidden-id"},
                    {"summary": "Different title", "id": "other-hidden-id"},
                ]
            }

        def create_event(payload: dict[str, object]) -> dict[str, object]:
            create_calls.append(dict(payload))
            return {"id": "calendar-test-id", "status": "confirmed"}

        bridge = WideNetGoogleCalendarConnectorBridge(
            search_events=search_events,
            create_event=create_event,
        )

        precheck = bridge.find_events_by_title(_valid_precheck_payload())
        serialized = json.dumps(precheck, sort_keys=True)

        self.assertEqual(precheck["contract"], PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT)
        self.assertEqual(precheck["matching_event_count"], 1)
        self.assertFalse(precheck["event_details_logged"])
        self.assertFalse(precheck["attendee_addresses_logged"])
        self.assertEqual(len(search_calls), 1)
        self.assertNotIn("hidden-id", serialized)

    def test_bridge_rejects_unrecognized_precheck_response_shape(self) -> None:
        bridge = WideNetGoogleCalendarConnectorBridge(
            search_events=lambda _payload: {"unexpected": []},
            create_event=lambda payload: dict(payload),
        )

        with self.assertRaises(CalendarBridgeContractError):
            bridge.find_events_by_title(_valid_precheck_payload())

    def test_bridge_rejects_unsafe_calendar_create_payload(self) -> None:
        bridge = WideNetGoogleCalendarConnectorBridge(
            search_events=lambda _payload: {"items": []},
            create_event=lambda payload: dict(payload),
        )
        unsafe_payload = {
            **_valid_create_payload(),
            "attendees": ["chris@example.com"],
        }

        with self.assertRaises(CalendarBridgeContractError):
            bridge.create_event(unsafe_payload)

    def test_runner_precheck_contract_requires_explicit_count_and_contract(self) -> None:
        valid = {
            "contract": PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT,
            "matching_event_count": 0,
        }

        self.assertEqual(require_explicit_calendar_matching_event_count(valid), 0)
        with self.assertRaises(CalendarBridgeContractError):
            require_explicit_calendar_matching_event_count({"matching_event_count": 0})
        with self.assertRaises(CalendarBridgeContractError):
            require_explicit_calendar_matching_event_count(
                {
                    "contract": PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT,
                    "events": [],
                }
            )

    def test_connector_search_shape_must_be_recognized(self) -> None:
        self.assertEqual(
            count_matching_calendar_events(
                {"events": [{"title": PHASE14C_WIDE_NET_REHEARSAL_MARKER}]},
                title=PHASE14C_WIDE_NET_REHEARSAL_MARKER,
            ),
            1,
        )
        with self.assertRaises(CalendarBridgeContractError):
            count_matching_calendar_events(
                {"events": {"summary": PHASE14C_WIDE_NET_REHEARSAL_MARKER}},
                title=PHASE14C_WIDE_NET_REHEARSAL_MARKER,
            )
        with self.assertRaises(CalendarBridgeContractError):
            count_matching_calendar_events(
                {"unexpected": []},
                title=PHASE14C_WIDE_NET_REHEARSAL_MARKER,
            )


def _valid_precheck_payload() -> dict[str, object]:
    return {
        "calendar_id": "primary",
        "title": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "time_min": "2026-07-06T00:00:00",
        "time_max": "2026-07-07T00:00:00",
        "timezone_str": "America/Chicago",
        "exact_title_match_required": True,
        "attendee_data_required": False,
    }


def _valid_create_payload() -> dict[str, object]:
    return {
        "calendar_id": "primary",
        "title": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "start_time": "2026-07-06T17:00:00",
        "end_time": "2026-07-06T17:15:00",
        "timezone_str": "America/Chicago",
        "attendees": [],
        "add_google_meet": False,
        "recurrence": None,
        "attachments": [],
        "description": "Bounded Phase 14-C marker.",
    }


if __name__ == "__main__":
    unittest.main()
