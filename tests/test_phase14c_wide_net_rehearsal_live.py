import json
import unittest
from datetime import date
from urllib.error import HTTPError

from personalos.phase14c_wide_net_rehearsal import (
    PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_WIDE_NET_REHEARSAL_MARKER,
)
from personalos.phase14c_wide_net_rehearsal_live import (
    WIDE_NET_CALENDAR_FAILED,
    WIDE_NET_CALENDAR_PRECHECK_FAILED,
    WIDE_NET_NOT_RUN_MISSING_CALENDAR_CLIENT,
    WIDE_NET_NOT_RUN_MISSING_EXECUTE_FLAG,
    WIDE_NET_NOT_RUN_DUPLICATE_CALENDAR_MARKER,
    WIDE_NET_NOT_RUN_UNAPPROVED_REFERENCE,
    WIDE_NET_PASSED,
    WIDE_NET_PASSED_WITH_MODEL_DIAGNOSTIC_FAILURE,
    WIDE_NET_REQUIRED_CONFIG_NAMES,
    WIDE_NET_TODOIST_FAILED,
    run_phase14c_wide_net_rehearsal,
)


class Phase14CWideNetRehearsalLiveTest(unittest.TestCase):
    def test_default_path_does_not_read_values_or_call_clients(self) -> None:
        report = run_phase14c_wide_net_rehearsal(
            available_config_names=WIDE_NET_REQUIRED_CONFIG_NAMES,
            provider="openrouter",
            api_key="secret-openrouter-key",
            todoist_token="secret-todoist-token",
            gmail_app_password="secret-gmail-password",
            calendar_connector_label="secret-calendar-label",
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], WIDE_NET_NOT_RUN_MISSING_EXECUTE_FLAG)
        self.assertFalse(report["safety_assertions"]["credential_values_read"])
        self.assertFalse(report["safety_assertions"]["model_provider_called"])
        self.assertFalse(report["safety_assertions"]["external_mutation"])
        self.assertEqual(report["call_limits"]["openrouter_primary_calls"], 0)
        self.assertEqual(report["call_limits"]["todoist_task_create_calls"], 0)
        self.assertEqual(report["call_limits"]["gmail_email_send_calls"], 0)
        self.assertEqual(report["call_limits"]["calendar_event_create_calls"], 0)
        self.assertEqual(
            report["sequence"][0],
            "google_calendar_duplicate_precheck",
        )
        self.assertNotIn("secret-openrouter-key", serialized)
        self.assertNotIn("secret-todoist-token", serialized)
        self.assertNotIn("secret-gmail-password", serialized)
        self.assertNotIn("secret-calendar-label", serialized)

    def test_live_path_requires_exact_approval_before_value_use(self) -> None:
        report = run_phase14c_wide_net_rehearsal(
            available_config_names=WIDE_NET_REQUIRED_CONFIG_NAMES,
            execute_live=True,
            approval_reference="wrong-reference",
            provider="openrouter",
            api_key="secret-openrouter-key",
            todoist_token="secret-todoist-token",
            gmail_app_password="secret-gmail-password",
            calendar_connector_label="secret-calendar-label",
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], WIDE_NET_NOT_RUN_UNAPPROVED_REFERENCE)
        self.assertFalse(report["safety_assertions"]["credential_values_read"])
        self.assertEqual(report["call_limits"]["openrouter_primary_calls"], 0)
        self.assertNotIn("secret-openrouter-key", serialized)
        self.assertNotIn("secret-todoist-token", serialized)
        self.assertNotIn("secret-gmail-password", serialized)
        self.assertNotIn("secret-calendar-label", serialized)

    def test_live_path_fails_closed_without_calendar_client_before_value_use(self) -> None:
        report = run_phase14c_wide_net_rehearsal(
            available_config_names=WIDE_NET_REQUIRED_CONFIG_NAMES,
            execute_live=True,
            approval_reference=PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
            provider="openrouter",
            api_key="secret-openrouter-key",
            todoist_token="secret-todoist-token",
            gmail_app_password="secret-gmail-password",
            calendar_connector_label="secret-calendar-label",
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], WIDE_NET_NOT_RUN_MISSING_CALENDAR_CLIENT)
        self.assertFalse(report["safety_assertions"]["credential_values_read"])
        self.assertFalse(report["safety_assertions"]["live_clients_initialized"])
        self.assertFalse(report["safety_assertions"]["external_mutation"])
        self.assertEqual(report["call_limits"]["openrouter_primary_calls"], 0)
        self.assertNotIn("secret-openrouter-key", serialized)
        self.assertNotIn("secret-todoist-token", serialized)
        self.assertNotIn("secret-gmail-password", serialized)
        self.assertNotIn("secret-calendar-label", serialized)

    def test_injected_live_path_runs_all_fixed_marker_rails_once(self) -> None:
        model = _RecordingModelClient(
            [
                {
                    "success": True,
                    "response_text": "PHASE14C_WIDE_NET_DIAGNOSTIC_OK",
                    "provider_alias": "openrouter",
                    "input_tokens": 20,
                    "output_tokens": 8,
                }
            ]
        )
        todoist = _RecordingTodoistClient()
        gmail = _RecordingGmailClient()
        calendar = _RecordingCalendarClient()

        report = run_phase14c_wide_net_rehearsal(
            available_config_names=WIDE_NET_REQUIRED_CONFIG_NAMES,
            execute_live=True,
            approval_reference=PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
            provider="openrouter",
            api_key="secret-openrouter-key",
            nemotron_super_model="secret-nemotron-model-id",
            glm_5_2_model="secret-glm-model-id",
            todoist_token="secret-todoist-token",
            gmail_sender_email="chris@example.com",
            gmail_app_password="secret-gmail-password",
            gmail_controlled_recipient="chris@example.com",
            calendar_connector_label="google_calendar_connector",
            model_client=model,
            todoist_client=todoist,
            gmail_client=gmail,
            calendar_client=calendar,
            source_date=date(2026, 7, 1),
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], WIDE_NET_PASSED)
        self.assertEqual(len(model.requests), 1)
        self.assertEqual(model.requests[0]["model_alias"], "nemotron_super")
        self.assertEqual(len(todoist.payloads), 1)
        self.assertEqual(todoist.payloads[0]["content"], PHASE14C_WIDE_NET_REHEARSAL_MARKER)
        self.assertEqual(todoist.payloads[0]["due_date"], "2026-07-06")
        self.assertEqual(len(gmail.payloads), 1)
        self.assertEqual(gmail.payloads[0]["subject"], PHASE14C_WIDE_NET_REHEARSAL_MARKER)
        self.assertNotIn("PHASE14C_WIDE_NET_DIAGNOSTIC_OK", gmail.payloads[0]["body"])
        self.assertEqual(len(calendar.precheck_payloads), 1)
        self.assertEqual(
            calendar.precheck_payloads[0]["title"],
            PHASE14C_WIDE_NET_REHEARSAL_MARKER,
        )
        self.assertEqual(calendar.precheck_payloads[0]["time_min"], "2026-07-06T00:00:00")
        self.assertEqual(calendar.precheck_payloads[0]["time_max"], "2026-07-07T00:00:00")
        self.assertEqual(len(calendar.payloads), 1)
        self.assertEqual(calendar.payloads[0]["title"], PHASE14C_WIDE_NET_REHEARSAL_MARKER)
        self.assertEqual(calendar.payloads[0]["start_time"], "2026-07-06T17:00:00")
        self.assertEqual(calendar.payloads[0]["end_time"], "2026-07-06T17:15:00")
        self.assertEqual(calendar.payloads[0]["attendees"], [])
        self.assertFalse(calendar.payloads[0]["add_google_meet"])
        self.assertIsNone(calendar.payloads[0]["recurrence"])
        self.assertEqual(report["call_limits"]["openrouter_primary_calls"], 1)
        self.assertEqual(report["call_limits"]["openrouter_fallback_calls"], 0)
        self.assertEqual(report["call_limits"]["calendar_duplicate_precheck_calls"], 1)
        self.assertEqual(report["call_limits"]["todoist_task_create_calls"], 1)
        self.assertEqual(report["call_limits"]["gmail_email_send_calls"], 1)
        self.assertEqual(report["call_limits"]["calendar_event_create_calls"], 1)
        self.assertTrue(report["calendar_duplicate_precheck"]["performed"])
        self.assertFalse(report["calendar_duplicate_precheck"]["duplicate_marker_found"])
        self.assertEqual(report["calendar_duplicate_precheck"]["matching_event_count"], 0)
        self.assertTrue(report["safety_assertions"]["external_mutation"])
        self.assertNotIn("PHASE14C_WIDE_NET_DIAGNOSTIC_OK", serialized)
        self.assertNotIn("secret-openrouter-key", serialized)
        self.assertNotIn("secret-todoist-token", serialized)
        self.assertNotIn("secret-gmail-password", serialized)
        self.assertNotIn("secret-nemotron-model-id", serialized)
        self.assertNotIn("chris@example.com", serialized)

    def test_model_diagnostic_failure_does_not_drive_or_block_fixed_marker_writes(self) -> None:
        model = _RecordingModelClient(
            [
                {"success": False, "failure_category": "transport_or_parse_error"},
                {
                    "success": False,
                    "failure_category": "http_error",
                    "http_status": 402,
                },
            ]
        )
        todoist = _RecordingTodoistClient()
        gmail = _RecordingGmailClient()
        calendar = _RecordingCalendarClient()

        report = run_phase14c_wide_net_rehearsal(
            available_config_names=WIDE_NET_REQUIRED_CONFIG_NAMES,
            execute_live=True,
            approval_reference=PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
            provider="openrouter",
            api_key="secret-openrouter-key",
            nemotron_super_model="secret-nemotron-model-id",
            glm_5_2_model="secret-glm-model-id",
            todoist_token="secret-todoist-token",
            gmail_sender_email="chris@example.com",
            gmail_app_password="secret-gmail-password",
            gmail_controlled_recipient="chris@example.com",
            calendar_connector_label="google_calendar_connector",
            model_client=model,
            todoist_client=todoist,
            gmail_client=gmail,
            calendar_client=calendar,
            source_date=date(2026, 7, 1),
        )

        self.assertEqual(report["status"], WIDE_NET_PASSED_WITH_MODEL_DIAGNOSTIC_FAILURE)
        self.assertEqual([request["model_alias"] for request in model.requests], [
            "nemotron_super",
            "glm_5_2",
        ])
        self.assertFalse(report["model_diagnostic"]["selected_validation_passed"])
        self.assertTrue(report["model_diagnostic"]["diagnostic_only"])
        self.assertFalse(report["model_diagnostic"]["model_output_drives_external_writes"])
        self.assertEqual(len(todoist.payloads), 1)
        self.assertEqual(len(gmail.payloads), 1)
        self.assertEqual(len(calendar.precheck_payloads), 1)
        self.assertEqual(len(calendar.payloads), 1)

    def test_calendar_duplicate_precheck_stops_before_any_mutation(self) -> None:
        model = _RecordingModelClient(
            [
                {
                    "success": True,
                    "response_text": "PHASE14C_WIDE_NET_DIAGNOSTIC_OK",
                }
            ]
        )
        todoist = _RecordingTodoistClient()
        gmail = _RecordingGmailClient()
        calendar = _RecordingCalendarClient(matching_event_count=1)

        report = run_phase14c_wide_net_rehearsal(
            available_config_names=WIDE_NET_REQUIRED_CONFIG_NAMES,
            execute_live=True,
            approval_reference=PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
            provider="openrouter",
            api_key="secret-openrouter-key",
            nemotron_super_model="secret-nemotron-model-id",
            glm_5_2_model="secret-glm-model-id",
            todoist_token="secret-todoist-token",
            gmail_sender_email="chris@example.com",
            gmail_app_password="secret-gmail-password",
            gmail_controlled_recipient="chris@example.com",
            calendar_connector_label="google_calendar_connector",
            model_client=model,
            todoist_client=todoist,
            gmail_client=gmail,
            calendar_client=calendar,
            source_date=date(2026, 7, 1),
        )

        self.assertEqual(report["status"], WIDE_NET_NOT_RUN_DUPLICATE_CALENDAR_MARKER)
        self.assertFalse(report["external_mutation"])
        self.assertEqual(report["external_writes"], "none")
        self.assertEqual(report["mutation_state"], "calendar_duplicate_marker_found_before_external_mutation")
        self.assertEqual(len(calendar.precheck_payloads), 1)
        self.assertEqual(model.requests, [])
        self.assertEqual(todoist.payloads, [])
        self.assertEqual(gmail.payloads, [])
        self.assertEqual(calendar.payloads, [])
        self.assertEqual(report["call_limits"]["calendar_duplicate_precheck_calls"], 1)
        self.assertEqual(report["call_limits"]["openrouter_primary_calls"], 0)
        self.assertEqual(report["call_limits"]["todoist_task_create_calls"], 0)
        self.assertEqual(report["calendar_duplicate_precheck"]["matching_event_count"], 1)
        self.assertTrue(report["calendar_duplicate_precheck"]["duplicate_marker_found"])

    def test_calendar_precheck_failure_stops_before_any_mutation(self) -> None:
        model = _RecordingModelClient(
            [
                {
                    "success": True,
                    "response_text": "PHASE14C_WIDE_NET_DIAGNOSTIC_OK",
                }
            ]
        )
        todoist = _RecordingTodoistClient()
        gmail = _RecordingGmailClient()
        error = _make_http_error(code=503, message="chris@example.com unavailable")
        calendar = _FailingCalendarPrecheckClient(error)

        report = run_phase14c_wide_net_rehearsal(
            available_config_names=WIDE_NET_REQUIRED_CONFIG_NAMES,
            execute_live=True,
            approval_reference=PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
            provider="openrouter",
            api_key="secret-openrouter-key",
            nemotron_super_model="secret-nemotron-model-id",
            glm_5_2_model="secret-glm-model-id",
            todoist_token="secret-todoist-token",
            gmail_sender_email="chris@example.com",
            gmail_app_password="secret-gmail-password",
            gmail_controlled_recipient="chris@example.com",
            calendar_connector_label="google_calendar_connector",
            model_client=model,
            todoist_client=todoist,
            gmail_client=gmail,
            calendar_client=calendar,
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], WIDE_NET_CALENDAR_PRECHECK_FAILED)
        self.assertFalse(report["external_mutation"])
        self.assertEqual(report["external_writes"], "none")
        self.assertEqual(report["calendar_precheck_failure"]["http_status"], 503)
        self.assertNotIn("chris@example.com", serialized)
        self.assertTrue(error.fp.closed)
        self.assertEqual(model.requests, [])
        self.assertEqual(todoist.payloads, [])
        self.assertEqual(gmail.payloads, [])

    def test_todoist_failure_stops_before_gmail_and_calendar(self) -> None:
        model = _RecordingModelClient(
            [
                {
                    "success": True,
                    "response_text": "PHASE14C_WIDE_NET_DIAGNOSTIC_OK",
                }
            ]
        )
        todoist = _FailingTodoistClient()
        gmail = _RecordingGmailClient()
        calendar = _RecordingCalendarClient()

        report = run_phase14c_wide_net_rehearsal(
            available_config_names=WIDE_NET_REQUIRED_CONFIG_NAMES,
            execute_live=True,
            approval_reference=PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
            provider="openrouter",
            api_key="secret-openrouter-key",
            nemotron_super_model="secret-nemotron-model-id",
            glm_5_2_model="secret-glm-model-id",
            todoist_token="secret-todoist-token",
            gmail_sender_email="chris@example.com",
            gmail_app_password="secret-gmail-password",
            gmail_controlled_recipient="chris@example.com",
            calendar_connector_label="google_calendar_connector",
            model_client=model,
            todoist_client=todoist,
            gmail_client=gmail,
            calendar_client=calendar,
        )

        self.assertEqual(report["status"], WIDE_NET_TODOIST_FAILED)
        self.assertIsNone(report["external_mutation"])
        self.assertEqual(report["mutation_state"], "unconfirmed_after_task_create_attempt")
        self.assertEqual(report["call_limits"]["todoist_task_create_calls"], 1)
        self.assertEqual(report["call_limits"]["gmail_email_send_calls"], 0)
        self.assertEqual(report["call_limits"]["calendar_event_create_calls"], 0)
        self.assertEqual(gmail.payloads, [])
        self.assertEqual(calendar.payloads, [])

    def test_calendar_create_http_error_reports_safe_status_and_closes(self) -> None:
        model = _RecordingModelClient(
            [
                {
                    "success": True,
                    "response_text": "PHASE14C_WIDE_NET_DIAGNOSTIC_OK",
                }
            ]
        )
        todoist = _RecordingTodoistClient()
        gmail = _RecordingGmailClient()
        error = _make_http_error(code=409, message="chris@example.com duplicate")
        calendar = _FailingCalendarCreateClient(error)

        report = run_phase14c_wide_net_rehearsal(
            available_config_names=WIDE_NET_REQUIRED_CONFIG_NAMES,
            execute_live=True,
            approval_reference=PHASE14C_WIDE_NET_REHEARSAL_APPROVAL_REFERENCE,
            provider="openrouter",
            api_key="secret-openrouter-key",
            nemotron_super_model="secret-nemotron-model-id",
            glm_5_2_model="secret-glm-model-id",
            todoist_token="secret-todoist-token",
            gmail_sender_email="chris@example.com",
            gmail_app_password="secret-gmail-password",
            gmail_controlled_recipient="chris@example.com",
            calendar_connector_label="google_calendar_connector",
            model_client=model,
            todoist_client=todoist,
            gmail_client=gmail,
            calendar_client=calendar,
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], WIDE_NET_CALENDAR_FAILED)
        self.assertEqual(report["calendar_failure"]["http_status"], 409)
        self.assertNotIn("chris@example.com", serialized)
        self.assertTrue(error.fp.closed)
        self.assertEqual(len(todoist.payloads), 1)
        self.assertEqual(len(gmail.payloads), 1)
        self.assertEqual(len(calendar.precheck_payloads), 1)
        self.assertEqual(len(calendar.payloads), 1)


class _RecordingModelClient:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, object]] = []

    def run_probe(self, request: dict[str, object]) -> dict[str, object]:
        self.requests.append(dict(request))
        return dict(self.responses.pop(0))


class _RecordingTodoistClient:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    def create_task(self, payload: dict[str, object]) -> dict[str, object]:
        self.payloads.append(dict(payload))
        return {
            "id": "todoist-test-id",
            "content": str(payload["content"]),
            "due": {"date": str(payload["due_date"])},
        }


class _FailingTodoistClient:
    def create_task(self, payload: dict[str, object]) -> dict[str, object]:
        raise OSError("redacted failure with chris@example.com")


class _RecordingGmailClient:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    def send_email(self, payload: dict[str, object]) -> dict[str, object]:
        self.payloads.append(dict(payload))
        return {"provider": "gmail_smtp", "message_accepted": True}


class _RecordingCalendarClient:
    def __init__(self, *, matching_event_count: int = 0) -> None:
        self.matching_event_count = matching_event_count
        self.precheck_payloads: list[dict[str, object]] = []
        self.payloads: list[dict[str, object]] = []

    def find_events_by_title(self, payload: dict[str, object]) -> dict[str, object]:
        self.precheck_payloads.append(dict(payload))
        return {"matching_event_count": self.matching_event_count}

    def create_event(self, payload: dict[str, object]) -> dict[str, object]:
        self.payloads.append(dict(payload))
        return {"id": "calendar-test-id", "status": "confirmed"}


class _FailingCalendarPrecheckClient(_RecordingCalendarClient):
    def __init__(self, error: HTTPError) -> None:
        super().__init__()
        self.error = error

    def find_events_by_title(self, payload: dict[str, object]) -> dict[str, object]:
        self.precheck_payloads.append(dict(payload))
        raise self.error


class _FailingCalendarCreateClient(_RecordingCalendarClient):
    def __init__(self, error: HTTPError) -> None:
        super().__init__()
        self.error = error

    def create_event(self, payload: dict[str, object]) -> dict[str, object]:
        self.payloads.append(dict(payload))
        raise self.error


class _ClosableBody:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _make_http_error(*, code: int, message: str) -> HTTPError:
    return HTTPError(
        url="https://calendar.example.invalid",
        code=code,
        msg=message,
        hdrs={},
        fp=_ClosableBody(),
    )


if __name__ == "__main__":
    unittest.main()
