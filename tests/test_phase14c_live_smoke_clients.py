import json
import smtplib
import unittest
from datetime import date

from personalos.openclaw_model_strategy import (
    OPENCLAW_MODEL_PROVIDER_CONFIG_ENTRY_NAMES,
    OPENCLAW_MODEL_SMOKE_EXPECTED_TEXT,
    OPENCLAW_MODEL_SMOKE_PASSED,
    run_openclaw_model_smoke_probe,
)
from personalos.openrouter_model_smoke_client import OpenRouterModelSmokeClient
from personalos.phase14c_gmail_live_smoke import (
    GMAIL_SMOKE_FAILED,
    GMAIL_SMOKE_NOT_RUN_MISSING_APPROVAL_REFERENCE,
    GMAIL_SMOKE_NOT_RUN_MISSING_EXECUTE_FLAG,
    GMAIL_SMOKE_PASSED,
    PHASE14C_GMAIL_APP_PASSWORD_CONFIG_NAME,
    PHASE14C_GMAIL_CONTROLLED_RECIPIENT_CONFIG_NAME,
    PHASE14C_GMAIL_SMOKE_SUBJECT,
    PHASE14C_GMAIL_SMTP_ADDRESS_CONFIG_NAME,
    PHASE14C_GMAIL_SMTP_CONFIG_ENTRY_NAMES,
    build_phase14c_gmail_email_payload,
    run_phase14c_gmail_smtp_smoke,
)
from personalos.phase14c_todoist_live_smoke import (
    PHASE14C_TODOIST_TASK_TITLE,
    PHASE14C_TODOIST_TOKEN_CONFIG_NAME,
    TODOIST_SMOKE_NOT_RUN_MISSING_APPROVAL_REFERENCE,
    TODOIST_SMOKE_NOT_RUN_MISSING_EXECUTE_FLAG,
    TODOIST_SMOKE_FAILED,
    TODOIST_SMOKE_PASSED,
    build_phase14c_todoist_task_payload,
    next_upcoming_monday,
    run_phase14c_todoist_inbox_smoke,
)


class Phase14CGmailLiveSmokeClientTest(unittest.TestCase):
    def test_gmail_payload_is_one_controlled_email_only(self) -> None:
        payload = build_phase14c_gmail_email_payload(
            sender_email="chris@example.com",
            recipient_email="chris@example.com",
        )

        self.assertEqual(payload["from"], "chris@example.com")
        self.assertEqual(payload["to"], "chris@example.com")
        self.assertEqual(payload["subject"], PHASE14C_GMAIL_SMOKE_SUBJECT)
        self.assertIn("bounded Phase 14-C supervised Gmail", payload["body"])
        self.assertEqual(payload["cc"], [])
        self.assertEqual(payload["bcc"], [])
        self.assertEqual(payload["attachments"], [])
        self.assertIsNone(payload["thread_id"])
        self.assertFalse(payload["reply_to_existing_thread"])
        self.assertFalse(payload["forward_existing_thread"])

    def test_gmail_default_path_does_not_read_password_or_send(self) -> None:
        report = run_phase14c_gmail_smtp_smoke(
            available_config_names=PHASE14C_GMAIL_SMTP_CONFIG_ENTRY_NAMES,
            sender_email="chris@example.com",
            app_password="secret-app-password",
            controlled_recipient="chris@example.com",
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], GMAIL_SMOKE_NOT_RUN_MISSING_EXECUTE_FLAG)
        self.assertFalse(report["gmail_email_sent"])
        self.assertEqual(report["mutation_state"], "not_attempted")
        self.assertEqual(report["call_limits"]["email_send_calls"], 0)
        self.assertFalse(report["safety_assertions"]["credential_values_read"])
        self.assertFalse(report["safety_assertions"]["live_client_initialized"])
        self.assertNotIn("secret-app-password", serialized)
        self.assertNotIn("chris@example.com", serialized)
        self.assertIn("c***@example.com", serialized)

    def test_gmail_live_path_requires_approval_before_password_use(self) -> None:
        report = run_phase14c_gmail_smtp_smoke(
            available_config_names=PHASE14C_GMAIL_SMTP_CONFIG_ENTRY_NAMES,
            execute_live=True,
            sender_email="chris@example.com",
            app_password="secret-app-password",
            controlled_recipient="chris@example.com",
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(
            report["status"],
            GMAIL_SMOKE_NOT_RUN_MISSING_APPROVAL_REFERENCE,
        )
        self.assertFalse(report["gmail_email_sent"])
        self.assertEqual(report["call_limits"]["email_send_calls"], 0)
        self.assertFalse(report["safety_assertions"]["credential_values_read"])
        self.assertNotIn("secret-app-password", serialized)

    def test_gmail_live_path_uses_injected_client_once_and_redacts_password(
        self,
    ) -> None:
        client = _RecordingGmailSmtpClient()

        report = run_phase14c_gmail_smtp_smoke(
            available_config_names=PHASE14C_GMAIL_SMTP_CONFIG_ENTRY_NAMES,
            execute_live=True,
            approval_reference="approved-phase14c-test",
            sender_email="chris@example.com",
            app_password="secret-app-password",
            controlled_recipient="chris@example.com",
            client=client,
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], GMAIL_SMOKE_PASSED)
        self.assertTrue(report["gmail_email_sent"])
        self.assertEqual(report["mutation_state"], "confirmed_email_sent")
        self.assertEqual(report["call_limits"]["email_send_calls"], 1)
        self.assertEqual(len(client.payloads), 1)
        self.assertEqual(client.payloads[0]["to"], "chris@example.com")
        self.assertTrue(report["safety_assertions"]["credential_values_read"])
        self.assertTrue(report["safety_assertions"]["max_one_email_send"])
        self.assertFalse(report["safety_assertions"]["cc_created"])
        self.assertFalse(report["safety_assertions"]["attachments_created"])
        self.assertNotIn("secret-app-password", serialized)
        self.assertNotIn("chris@example.com", serialized)

    def test_gmail_send_attempt_failure_reports_unconfirmed_mutation(self) -> None:
        client = _FailingAfterAttemptGmailSmtpClient()

        report = run_phase14c_gmail_smtp_smoke(
            available_config_names=PHASE14C_GMAIL_SMTP_CONFIG_ENTRY_NAMES,
            execute_live=True,
            approval_reference="approved-phase14c-test",
            sender_email="chris@example.com",
            app_password="secret-app-password",
            controlled_recipient="chris@example.com",
            client=client,
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], GMAIL_SMOKE_FAILED)
        self.assertIsNone(report["gmail_email_sent"])
        self.assertEqual(report["mutation_state"], "unconfirmed_after_send_attempt")
        self.assertEqual(report["call_limits"]["email_send_calls"], 1)
        self.assertEqual(len(client.payloads), 1)
        self.assertIsNone(report["safety_assertions"]["external_mutation"])
        self.assertIsNone(report["safety_assertions"]["gmail_email_sent"])
        self.assertTrue(report["safety_assertions"]["credential_values_read"])
        self.assertEqual(report["failure"]["type"], "SMTPRecipientsRefused")
        self.assertEqual(
            report["failure"]["message"],
            "Gmail SMTP send attempt failed; details redacted.",
        )
        self.assertNotIn("secret-app-password", serialized)
        self.assertNotIn("chris@example.com", serialized)

    def test_gmail_missing_names_are_reported_without_present_name_echo(self) -> None:
        report = run_phase14c_gmail_smtp_smoke(
            available_config_names=(PHASE14C_GMAIL_SMTP_ADDRESS_CONFIG_NAME,),
        )
        preflight = report["config_preflight"]

        self.assertEqual(
            preflight["missing_config_entry_names"],
            [
                PHASE14C_GMAIL_APP_PASSWORD_CONFIG_NAME,
                PHASE14C_GMAIL_CONTROLLED_RECIPIENT_CONFIG_NAME,
            ],
        )
        self.assertFalse(preflight["available_config_entry_names_reported"])


class Phase14CTodoistLiveSmokeClientTest(unittest.TestCase):
    def test_next_upcoming_monday_is_strictly_future(self) -> None:
        self.assertEqual(
            next_upcoming_monday(date(2026, 6, 29)),
            date(2026, 7, 6),
        )
        self.assertEqual(
            next_upcoming_monday(date(2026, 7, 1)),
            date(2026, 7, 6),
        )

    def test_todoist_payload_is_inbox_default_one_task_only(self) -> None:
        payload = build_phase14c_todoist_task_payload(due_date=date(2026, 7, 6))

        self.assertEqual(payload["content"], PHASE14C_TODOIST_TASK_TITLE)
        self.assertEqual(payload["due_date"], "2026-07-06")
        self.assertNotIn("project_id", payload)
        self.assertNotIn("labels", payload)
        self.assertNotIn("description", payload)
        self.assertNotIn("parent_id", payload)

    def test_todoist_default_path_does_not_read_token_or_create_task(self) -> None:
        report = run_phase14c_todoist_inbox_smoke(
            available_config_names=(PHASE14C_TODOIST_TOKEN_CONFIG_NAME,),
            source_date=date(2026, 6, 29),
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], TODOIST_SMOKE_NOT_RUN_MISSING_EXECUTE_FLAG)
        self.assertFalse(report["todoist_task_created"])
        self.assertEqual(report["mutation_state"], "not_attempted")
        self.assertEqual(report["call_limits"]["task_create_calls"], 0)
        self.assertFalse(report["safety_assertions"]["credential_values_read"])
        self.assertFalse(report["safety_assertions"]["live_client_initialized"])
        self.assertNotIn(PHASE14C_TODOIST_TOKEN_CONFIG_NAME, serialized)

    def test_todoist_live_path_requires_approval_before_token_use(self) -> None:
        report = run_phase14c_todoist_inbox_smoke(
            available_config_names=(PHASE14C_TODOIST_TOKEN_CONFIG_NAME,),
            execute_live=True,
            token="secret-token-value",
            source_date=date(2026, 6, 29),
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(
            report["status"],
            TODOIST_SMOKE_NOT_RUN_MISSING_APPROVAL_REFERENCE,
        )
        self.assertFalse(report["todoist_task_created"])
        self.assertEqual(report["call_limits"]["task_create_calls"], 0)
        self.assertFalse(report["safety_assertions"]["credential_values_read"])
        self.assertNotIn("secret-token-value", serialized)

    def test_todoist_live_path_uses_injected_client_once_and_redacts_token(self) -> None:
        client = _RecordingTodoistClient()

        report = run_phase14c_todoist_inbox_smoke(
            available_config_names=(PHASE14C_TODOIST_TOKEN_CONFIG_NAME,),
            execute_live=True,
            approval_reference="approved-phase14c-test",
            token="secret-token-value",
            client=client,
            source_date=date(2026, 6, 29),
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], TODOIST_SMOKE_PASSED)
        self.assertTrue(report["todoist_task_created"])
        self.assertEqual(report["mutation_state"], "confirmed_task_created")
        self.assertEqual(report["call_limits"]["task_create_calls"], 1)
        self.assertEqual(len(client.payloads), 1)
        self.assertEqual(client.payloads[0]["content"], PHASE14C_TODOIST_TASK_TITLE)
        self.assertEqual(client.payloads[0]["due_date"], "2026-07-06")
        self.assertNotIn("project_id", client.payloads[0])
        self.assertTrue(report["safety_assertions"]["credential_values_read"])
        self.assertTrue(report["safety_assertions"]["max_one_task_create"])
        self.assertFalse(report["safety_assertions"]["recurrence_created"])
        self.assertNotIn("secret-token-value", serialized)

    def test_todoist_live_post_attempt_failure_reports_unconfirmed_mutation(
        self,
    ) -> None:
        client = _FailingAfterAttemptTodoistClient()

        report = run_phase14c_todoist_inbox_smoke(
            available_config_names=(PHASE14C_TODOIST_TOKEN_CONFIG_NAME,),
            execute_live=True,
            approval_reference="approved-phase14c-test",
            token="secret-token-value",
            client=client,
            source_date=date(2026, 6, 29),
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], TODOIST_SMOKE_FAILED)
        self.assertIsNone(report["todoist_task_created"])
        self.assertEqual(
            report["mutation_state"],
            "unconfirmed_after_task_create_attempt",
        )
        self.assertEqual(report["call_limits"]["task_create_calls"], 1)
        self.assertEqual(len(client.payloads), 1)
        self.assertIsNone(report["safety_assertions"]["external_mutation"])
        self.assertIsNone(report["safety_assertions"]["todoist_task_created"])
        self.assertTrue(report["safety_assertions"]["credential_values_read"])
        self.assertNotIn("secret-token-value", serialized)


class Phase14COpenRouterModelSmokeClientTest(unittest.TestCase):
    def test_openrouter_client_returns_safe_metadata_only(self) -> None:
        client = OpenRouterModelSmokeClient(
            api_key="secret-openrouter-key",
            models_by_alias={"nemotron_super": "configured-model-id"},
            opener=_FakeOpenRouterOpener(),
        )

        result = client.run_probe(
            {
                "model_alias": "nemotron_super",
                "prompt": "short smoke prompt",
                "max_output_tokens": 16,
            }
        )
        serialized = json.dumps(result, sort_keys=True)

        self.assertTrue(result["success"])
        self.assertEqual(result["provider_alias"], "openrouter")
        self.assertEqual(result["response_text"], OPENCLAW_MODEL_SMOKE_EXPECTED_TEXT)
        self.assertEqual(result["input_tokens"], 7)
        self.assertEqual(result["output_tokens"], 5)
        self.assertNotIn("secret-openrouter-key", serialized)
        self.assertNotIn("configured-model-id", serialized)
        self.assertNotIn("short smoke prompt", serialized)

    def test_openrouter_smoke_probe_sets_live_safety_flags(self) -> None:
        client = OpenRouterModelSmokeClient(
            api_key="secret-openrouter-key",
            models_by_alias={"nemotron_super": "configured-model-id"},
            opener=_FakeOpenRouterOpener(),
        )

        report = run_openclaw_model_smoke_probe(
            available_config_names=OPENCLAW_MODEL_PROVIDER_CONFIG_ENTRY_NAMES,
            client=client,
            client_type="openrouter_stdlib_http_client",
            credential_values_read=True,
            model_provider_called=True,
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], OPENCLAW_MODEL_SMOKE_PASSED)
        self.assertEqual(report["call_limits"]["primary_calls"], 1)
        self.assertEqual(report["call_limits"]["fallback_calls"], 0)
        self.assertTrue(report["safety_assertions"]["credential_values_read"])
        self.assertTrue(report["safety_assertions"]["model_provider_called"])
        self.assertFalse(report["safety_assertions"]["full_prompt_logged"])
        self.assertNotIn("secret-openrouter-key", serialized)
        self.assertNotIn("configured-model-id", serialized)


class _RecordingTodoistClient:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    def create_task(self, payload: dict[str, object]) -> dict[str, object]:
        self.payloads.append(dict(payload))
        return {
            "id": "task-id-123",
            "content": payload["content"],
            "due": {"date": payload["due_date"]},
            "url": "https://todoist.com/showTask?id=task-id-123",
            "user_id": "dropped-user-id",
        }


class _FailingAfterAttemptTodoistClient:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    def create_task(self, payload: dict[str, object]) -> dict[str, object]:
        self.payloads.append(dict(payload))
        raise ValueError("response body was not a JSON object")


class _RecordingGmailSmtpClient:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    def send_email(self, payload: dict[str, object]) -> dict[str, object]:
        self.payloads.append(dict(payload))
        return {
            "provider": "gmail_smtp",
            "message_accepted": True,
            "message_id": "gmail-smoke-message-id",
            "raw_recipient": payload["to"],
        }


class _FailingAfterAttemptGmailSmtpClient:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    def send_email(self, payload: dict[str, object]) -> dict[str, object]:
        self.payloads.append(dict(payload))
        raise smtplib.SMTPRecipientsRefused(
            {"chris@example.com": (550, b"bad recipient chris@example.com")}
        )


class _FakeOpenRouterOpener:
    def __call__(self, request: object, timeout: float) -> "_FakeHTTPResponse":
        return _FakeHTTPResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": OPENCLAW_MODEL_SMOKE_EXPECTED_TEXT,
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 7,
                    "completion_tokens": 5,
                },
            }
        )


class _FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")
