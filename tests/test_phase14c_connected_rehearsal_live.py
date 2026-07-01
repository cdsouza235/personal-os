import json
import unittest
from datetime import date

from personalos.phase14c_connected_rehearsal import (
    PHASE14C_CONNECTED_REHEARSAL_APPROVAL_REFERENCE,
    PHASE14C_CONNECTED_REHEARSAL_MARKER,
)
from personalos.phase14c_connected_rehearsal_live import (
    CONNECTED_REHEARSAL_MODEL_FAILED,
    CONNECTED_REHEARSAL_NOT_RUN_MISSING_EXECUTE_FLAG,
    CONNECTED_REHEARSAL_NOT_RUN_UNAPPROVED_REFERENCE,
    CONNECTED_REHEARSAL_PASSED,
    CONNECTED_REHEARSAL_REQUIRED_CONFIG_NAMES,
    run_phase14c_connected_rehearsal,
)


class Phase14CConnectedRehearsalLiveTest(unittest.TestCase):
    def test_default_path_does_not_read_values_or_call_clients(self) -> None:
        report = run_phase14c_connected_rehearsal(
            available_config_names=CONNECTED_REHEARSAL_REQUIRED_CONFIG_NAMES,
            provider="openrouter",
            api_key="secret-openrouter-key",
            todoist_token="secret-todoist-token",
            gmail_app_password="secret-gmail-password",
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], CONNECTED_REHEARSAL_NOT_RUN_MISSING_EXECUTE_FLAG)
        self.assertFalse(report["safety_assertions"]["credential_values_read"])
        self.assertFalse(report["safety_assertions"]["model_provider_called"])
        self.assertFalse(report["safety_assertions"]["external_mutation"])
        self.assertEqual(report["call_limits"]["openrouter_primary_calls"], 0)
        self.assertEqual(report["call_limits"]["todoist_task_create_calls"], 0)
        self.assertEqual(report["call_limits"]["gmail_email_send_calls"], 0)
        self.assertNotIn("secret-openrouter-key", serialized)
        self.assertNotIn("secret-todoist-token", serialized)
        self.assertNotIn("secret-gmail-password", serialized)

    def test_live_path_requires_exact_approval_before_value_use(self) -> None:
        report = run_phase14c_connected_rehearsal(
            available_config_names=CONNECTED_REHEARSAL_REQUIRED_CONFIG_NAMES,
            execute_live=True,
            approval_reference="wrong-reference",
            provider="openrouter",
            api_key="secret-openrouter-key",
            todoist_token="secret-todoist-token",
            gmail_app_password="secret-gmail-password",
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], CONNECTED_REHEARSAL_NOT_RUN_UNAPPROVED_REFERENCE)
        self.assertFalse(report["safety_assertions"]["credential_values_read"])
        self.assertEqual(report["call_limits"]["openrouter_primary_calls"], 0)
        self.assertNotIn("secret-openrouter-key", serialized)
        self.assertNotIn("secret-todoist-token", serialized)
        self.assertNotIn("secret-gmail-password", serialized)

    def test_live_path_links_model_task_and_email_once(self) -> None:
        model = _RecordingModelClient(
            [
                {
                    "success": True,
                    "response_text": "Clear counters\nWipe stovetop\nPut supplies away",
                    "provider_alias": "openrouter",
                    "input_tokens": 32,
                    "output_tokens": 24,
                }
            ]
        )
        todoist = _RecordingTodoistClient()
        gmail = _RecordingGmailClient()

        report = run_phase14c_connected_rehearsal(
            available_config_names=CONNECTED_REHEARSAL_REQUIRED_CONFIG_NAMES,
            execute_live=True,
            approval_reference=PHASE14C_CONNECTED_REHEARSAL_APPROVAL_REFERENCE,
            provider="openrouter",
            api_key="secret-openrouter-key",
            nemotron_super_model="secret-nemotron-model-id",
            glm_5_2_model="secret-glm-model-id",
            todoist_token="secret-todoist-token",
            gmail_sender_email="chris@example.com",
            gmail_app_password="secret-gmail-password",
            gmail_controlled_recipient="chris@example.com",
            model_client=model,
            todoist_client=todoist,
            gmail_client=gmail,
            source_date=date(2026, 7, 1),
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], CONNECTED_REHEARSAL_PASSED)
        self.assertEqual(len(model.requests), 1)
        self.assertEqual(model.requests[0]["model_alias"], "nemotron_super")
        self.assertEqual(len(todoist.payloads), 1)
        self.assertEqual(todoist.payloads[0]["content"], PHASE14C_CONNECTED_REHEARSAL_MARKER)
        self.assertEqual(todoist.payloads[0]["due_date"], "2026-07-06")
        self.assertEqual(len(gmail.payloads), 1)
        self.assertEqual(gmail.payloads[0]["subject"], PHASE14C_CONNECTED_REHEARSAL_MARKER)
        self.assertIn("Clear counters", gmail.payloads[0]["body"])
        self.assertEqual(report["call_limits"]["openrouter_primary_calls"], 1)
        self.assertEqual(report["call_limits"]["openrouter_fallback_calls"], 0)
        self.assertEqual(report["call_limits"]["todoist_task_create_calls"], 1)
        self.assertEqual(report["call_limits"]["gmail_email_send_calls"], 1)
        self.assertTrue(report["safety_assertions"]["credential_values_read"])
        self.assertTrue(report["safety_assertions"]["external_mutation"])
        self.assertFalse(report["model_brief_summary"]["brief_text_logged"])
        self.assertNotIn("Clear counters", serialized)
        self.assertNotIn("secret-openrouter-key", serialized)
        self.assertNotIn("secret-todoist-token", serialized)
        self.assertNotIn("secret-gmail-password", serialized)
        self.assertNotIn("secret-nemotron-model-id", serialized)
        self.assertNotIn("chris@example.com", serialized)

    def test_live_path_rolls_stale_todoist_due_date_to_next_monday(self) -> None:
        model = _RecordingModelClient(
            [
                {
                    "success": True,
                    "response_text": "Clear counters\nWipe stovetop\nPut supplies away",
                    "provider_alias": "openrouter",
                }
            ]
        )
        todoist = _RecordingTodoistClient()

        report = run_phase14c_connected_rehearsal(
            available_config_names=CONNECTED_REHEARSAL_REQUIRED_CONFIG_NAMES,
            execute_live=True,
            approval_reference=PHASE14C_CONNECTED_REHEARSAL_APPROVAL_REFERENCE,
            provider="openrouter",
            api_key="secret-openrouter-key",
            nemotron_super_model="secret-nemotron-model-id",
            glm_5_2_model="secret-glm-model-id",
            todoist_token="secret-todoist-token",
            gmail_sender_email="chris@example.com",
            gmail_app_password="secret-gmail-password",
            gmail_controlled_recipient="chris@example.com",
            model_client=model,
            todoist_client=todoist,
            gmail_client=_RecordingGmailClient(),
            source_date=date(2026, 7, 7),
        )

        self.assertEqual(report["status"], CONNECTED_REHEARSAL_PASSED)
        self.assertEqual(report["due_date"], "2026-07-13")
        self.assertEqual(len(todoist.payloads), 1)
        self.assertEqual(todoist.payloads[0]["due_date"], "2026-07-13")

    def test_fallback_runs_only_after_primary_validation_failure(self) -> None:
        model = _RecordingModelClient(
            [
                {"success": False, "failure_category": "explicit_validation_failure"},
                {
                    "success": True,
                    "response_text": "Clear counters\nWipe stovetop\nPut supplies away",
                    "provider_alias": "openrouter",
                },
            ]
        )

        report = run_phase14c_connected_rehearsal(
            available_config_names=CONNECTED_REHEARSAL_REQUIRED_CONFIG_NAMES,
            execute_live=True,
            approval_reference=PHASE14C_CONNECTED_REHEARSAL_APPROVAL_REFERENCE,
            provider="openrouter",
            api_key="secret-openrouter-key",
            nemotron_super_model="secret-nemotron-model-id",
            glm_5_2_model="secret-glm-model-id",
            todoist_token="secret-todoist-token",
            gmail_sender_email="chris@example.com",
            gmail_app_password="secret-gmail-password",
            gmail_controlled_recipient="chris@example.com",
            model_client=model,
            todoist_client=_RecordingTodoistClient(),
            gmail_client=_RecordingGmailClient(),
        )

        self.assertEqual(report["status"], CONNECTED_REHEARSAL_PASSED)
        self.assertEqual([request["model_alias"] for request in model.requests], [
            "nemotron_super",
            "glm_5_2",
        ])
        self.assertEqual(report["call_limits"]["openrouter_primary_calls"], 1)
        self.assertEqual(report["call_limits"]["openrouter_fallback_calls"], 1)

    def test_model_validation_failure_stops_before_external_writes(self) -> None:
        model = _RecordingModelClient(
            [
                {"success": False, "failure_category": "transport_or_parse_error"},
                {"success": True, "response_text": "token should fail validation"},
            ]
        )
        todoist = _RecordingTodoistClient()
        gmail = _RecordingGmailClient()

        report = run_phase14c_connected_rehearsal(
            available_config_names=CONNECTED_REHEARSAL_REQUIRED_CONFIG_NAMES,
            execute_live=True,
            approval_reference=PHASE14C_CONNECTED_REHEARSAL_APPROVAL_REFERENCE,
            provider="openrouter",
            api_key="secret-openrouter-key",
            nemotron_super_model="secret-nemotron-model-id",
            glm_5_2_model="secret-glm-model-id",
            todoist_token="secret-todoist-token",
            gmail_sender_email="chris@example.com",
            gmail_app_password="secret-gmail-password",
            gmail_controlled_recipient="chris@example.com",
            model_client=model,
            todoist_client=todoist,
            gmail_client=gmail,
        )

        self.assertEqual(report["status"], CONNECTED_REHEARSAL_MODEL_FAILED)
        self.assertEqual(report["call_limits"]["openrouter_primary_calls"], 1)
        self.assertEqual(report["call_limits"]["openrouter_fallback_calls"], 1)
        self.assertEqual(report["call_limits"]["todoist_task_create_calls"], 0)
        self.assertEqual(report["call_limits"]["gmail_email_send_calls"], 0)
        self.assertEqual(todoist.payloads, [])
        self.assertEqual(gmail.payloads, [])
        self.assertFalse(report["safety_assertions"]["external_mutation"])


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


class _RecordingGmailClient:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    def send_email(self, payload: dict[str, object]) -> dict[str, object]:
        self.payloads.append(dict(payload))
        return {"provider": "gmail_smtp", "message_accepted": True}


if __name__ == "__main__":
    unittest.main()
