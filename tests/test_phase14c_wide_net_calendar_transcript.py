import json
import unittest

from personalos.phase14c_wide_net_calendar_bridge import (
    PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT,
)
from personalos.phase14c_wide_net_calendar_transcript import (
    PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_BLOCKED,
    PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_INPUT_MAX_BYTES,
    PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_TEMPLATE_STATUS,
    PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_VALID,
    build_phase14c_wide_net_calendar_transcript_input_size_report,
    build_phase14c_wide_net_calendar_transcript_template,
    validate_phase14c_wide_net_calendar_transcript,
)
from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
)


class Phase14CWideNetCalendarTranscriptTest(unittest.TestCase):
    def test_template_is_inert_and_reports_expected_connector_args(self) -> None:
        template = build_phase14c_wide_net_calendar_transcript_template()

        self.assertEqual(
            template["status"],
            PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_TEMPLATE_STATUS,
        )
        self.assertEqual(template["marker"], PHASE14C_WIDE_NET_REHEARSAL_MARKER)
        self.assertFalse(template["ready_for_live_execution"])
        self.assertTrue(template["template_only_not_authorization"])
        self.assertFalse(template["calendar_app_connector_called"])
        self.assertFalse(template["credential_values_read"])
        self.assertFalse(template["external_mutation"])
        self.assertEqual(
            template["expected_duplicate_precheck"]["connector_action"],
            "search_events",
        )
        self.assertEqual(
            template["expected_duplicate_precheck"]["normalized_response_contract"],
            PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT,
        )
        self.assertEqual(
            template["expected_calendar_create"]["connector_action"],
            "create_event",
        )
        self.assertFalse(template["safety_assertions"]["calendar_app_connector_called"])

    def test_validator_accepts_precheck_clear_transcript(self) -> None:
        validation = validate_phase14c_wide_net_calendar_transcript(
            _precheck_clear_transcript()
        )

        self.assertEqual(validation["status"], PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_VALID)
        self.assertTrue(validation["accepted"])
        self.assertEqual(validation["stage"], "duplicate_precheck_clear")
        self.assertTrue(validation["create_allowed_after_precheck"])
        self.assertEqual(validation["failure_reasons"], [])
        self.assertEqual(validation["precheck_summary"]["matching_event_count"], 0)
        self.assertFalse(validation["precheck_summary"]["event_details_logged"])
        self.assertFalse(validation["raw_transcript_returned"])
        self.assertFalse(validation["input_values_echoed"])

    def test_validator_accepts_complete_create_transcript(self) -> None:
        transcript = _precheck_clear_transcript()
        transcript["calendar_create"] = {
            "performed": True,
            "connector_action": "create_event",
            "connector_args": _template_create_args(),
            "sanitized_result": {"id": "evt_123", "status": "confirmed"},
        }

        validation = validate_phase14c_wide_net_calendar_transcript(transcript)
        serialized = json.dumps(validation, sort_keys=True)

        self.assertEqual(validation["status"], PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_VALID)
        self.assertTrue(validation["accepted"])
        self.assertEqual(validation["stage"], "calendar_create_confirmed")
        self.assertFalse(validation["create_allowed_after_precheck"])
        self.assertTrue(validation["calendar_create_summary"]["performed"])
        self.assertEqual(
            validation["calendar_create_summary"]["result_keys"],
            ("id", "status"),
        )
        self.assertNotIn("evt_123", serialized)

    def test_validator_blocks_duplicate_precheck_count(self) -> None:
        transcript = _precheck_clear_transcript()
        transcript["duplicate_precheck"]["normalized_response"][
            "matching_event_count"
        ] = 1

        validation = validate_phase14c_wide_net_calendar_transcript(transcript)

        self.assertEqual(
            validation["status"],
            PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_BLOCKED,
        )
        self.assertFalse(validation["accepted"])
        self.assertIn(
            "calendar_duplicate_precheck_count_not_zero",
            validation["failure_reasons"],
        )
        self.assertTrue(validation["precheck_summary"]["duplicate_marker_found"])

    def test_validator_blocks_raw_details_and_does_not_echo_values(self) -> None:
        transcript = _precheck_clear_transcript()
        transcript["calendar_create"] = {
            "performed": True,
            "connector_action": "create_event",
            "connector_args": _template_create_args(),
            "sanitized_result": {
                "id": "evt_123",
                "htmlLink": "https://calendar.google.com/event?token=secret",
                "attendee": "chris@example.com",
            },
        }

        validation = validate_phase14c_wide_net_calendar_transcript(transcript)
        serialized = json.dumps(validation, sort_keys=True)

        self.assertEqual(
            validation["status"],
            PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_BLOCKED,
        )
        self.assertFalse(validation["accepted"])
        self.assertIn(
            "calendar_create_result_contains_unapproved_fields",
            validation["failure_reasons"],
        )
        self.assertIn("unmasked_email_value_present", validation["failure_reasons"])
        self.assertIn("secret_like_value_present", validation["failure_reasons"])
        self.assertNotIn("chris@example.com", serialized)
        self.assertNotIn("token=secret", serialized)
        self.assertNotIn("evt_123", serialized)

    def test_input_size_report_blocks_without_values(self) -> None:
        validation = build_phase14c_wide_net_calendar_transcript_input_size_report(
            PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_INPUT_MAX_BYTES + 1
        )

        self.assertEqual(
            validation["status"],
            PHASE14C_WIDE_NET_CALENDAR_TRANSCRIPT_BLOCKED,
        )
        self.assertFalse(validation["accepted"])
        self.assertEqual(validation["failure_reasons"], ["input_file_too_large"])
        self.assertFalse(validation["raw_transcript_returned"])
        self.assertFalse(validation["input_values_echoed"])


def _template_precheck_args() -> dict[str, object]:
    template = build_phase14c_wide_net_calendar_transcript_template()
    return dict(template["expected_duplicate_precheck"]["connector_args"])


def _template_create_args() -> dict[str, object]:
    template = build_phase14c_wide_net_calendar_transcript_template()
    return dict(template["expected_calendar_create"]["connector_args"])


def _precheck_clear_transcript() -> dict[str, object]:
    return {
        "marker": PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        "duplicate_precheck": {
            "performed": True,
            "connector_action": "search_events",
            "connector_args": _template_precheck_args(),
            "normalized_response": {
                "contract": PHASE14C_WIDE_NET_CALENDAR_PRECHECK_CONTRACT,
                "matching_event_count": 0,
                "event_details_logged": False,
                "attendee_addresses_logged": False,
            },
        },
        "calendar_create": {"performed": False},
    }


if __name__ == "__main__":
    unittest.main()
