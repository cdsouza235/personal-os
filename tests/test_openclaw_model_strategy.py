import json
import unittest
from pathlib import Path

from personalos.openclaw_model_strategy import (
    OPENCLAW_MODEL_STRATEGY_SCHEMA_VERSION,
    OPENCLAW_MODEL_PROVIDER_CONFIG_ENTRY_NAMES,
    OPENCLAW_MODEL_SMOKE_EXPECTED_TEXT,
    OPENCLAW_MODEL_SMOKE_MISSING_CLIENT,
    OPENCLAW_MODEL_SMOKE_MISSING_PROVIDER_CONFIG,
    OPENCLAW_MODEL_SMOKE_PASSED,
    REASONING_LANE,
    SMOKE_LANE,
    build_openclaw_model_call_plan,
    build_openclaw_model_provider_readiness_report,
    build_openclaw_model_strategy_config,
    run_openclaw_model_smoke_probe,
    sanitize_openclaw_model_run_metadata,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_STRATEGY_DOC = REPO_ROOT / "docs" / "OPENCLAW_MODEL_STRATEGY.md"


class OpenClawModelStrategyTest(unittest.TestCase):
    def test_strategy_records_deterministic_lane_routing(self) -> None:
        config = build_openclaw_model_strategy_config()

        self.assertEqual(
            config["schema_version"], OPENCLAW_MODEL_STRATEGY_SCHEMA_VERSION
        )
        self.assertEqual(config["strategy"], "deterministic_explicit_lane_routing")
        self.assertTrue(config["constraints"]["routing_explicit_by_lane"])
        self.assertFalse(config["constraints"]["self_modifying_routing_logic"])
        self.assertFalse(config["constraints"]["hidden_model_choice"])
        self.assertFalse(config["constraints"]["provider_auto_escalation"])
        self.assertEqual(config["constraints"]["max_primary_calls_per_probe"], 1)
        self.assertEqual(config["constraints"]["max_fallback_calls_per_probe"], 1)
        self.assertFalse(config["constraints"]["log_full_prompts"])
        self.assertFalse(config["constraints"]["log_credential_values"])

    def test_smoke_lane_uses_nemotron_primary_and_glm_fallback(self) -> None:
        plan = build_openclaw_model_call_plan(
            SMOKE_LANE,
            task_type="openclaw_no_op_smoke_probe",
        )

        self.assertEqual(plan["primary"]["alias"], "nemotron_super")
        self.assertEqual(plan["fallback"]["alias"], "glm_5_2")
        self.assertEqual(
            plan["primary"]["provider_model_hint"],
            "nvidia/nemotron-3-super-120b-a12b",
        )
        self.assertEqual(plan["fallback"]["provider_model_hint"], "z-ai/glm-5.2")
        self.assertEqual(plan["max_primary_calls"], 1)
        self.assertEqual(plan["max_fallback_calls"], 1)
        self.assertEqual(plan["max_total_calls"], 2)
        self.assertEqual(plan["max_output_tokens"], 256)

    def test_reasoning_lane_uses_glm_primary_and_nemotron_fallback(self) -> None:
        plan = build_openclaw_model_call_plan(
            REASONING_LANE,
            task_type="ambiguous_multi_step_operator_reasoning",
        )

        self.assertEqual(plan["primary"]["alias"], "glm_5_2")
        self.assertEqual(plan["fallback"]["alias"], "nemotron_super")
        self.assertEqual(plan["max_primary_calls"], 1)
        self.assertEqual(plan["max_fallback_calls"], 1)
        self.assertEqual(plan["max_output_tokens"], 768)

    def test_provider_hints_are_configurable_by_alias(self) -> None:
        config = build_openclaw_model_strategy_config(
            model_aliases={
                "nemotron_super": {
                    "alias": "nemotron_super",
                    "provider_model_hint": "provider-specific-nemotron-id",
                },
                "glm_5_2": {
                    "alias": "glm_5_2",
                    "provider_model_hint": "provider-specific-glm-id",
                },
            }
        )

        smoke = config["lanes"][SMOKE_LANE]
        reasoning = config["lanes"][REASONING_LANE]
        self.assertEqual(
            smoke["primary"]["provider_model_hint"],
            "provider-specific-nemotron-id",
        )
        self.assertEqual(reasoning["primary"]["provider_model_hint"], "provider-specific-glm-id")

    def test_rejects_unknown_lane_and_wrong_task_type(self) -> None:
        with self.assertRaisesRegex(ValueError, "lane must be smoke or reasoning"):
            build_openclaw_model_call_plan("auto")
        with self.assertRaisesRegex(ValueError, "task_type is not allowed"):
            build_openclaw_model_call_plan(
                SMOKE_LANE,
                task_type="future_high_complexity_openclaw_planning",
            )

    def test_sanitized_metadata_drops_prompt_and_credential_values(self) -> None:
        metadata = sanitize_openclaw_model_run_metadata(
            {
                "provider_alias": "openrouter",
                "model_alias": "nemotron_super",
                "lane": SMOKE_LANE,
                "success": False,
                "failure_category": "timeout",
                "latency_ms": 1200,
                "input_tokens": 40,
                "output_tokens": 12,
                "prompt": "secret prompt text",
                "api_key": "secret-token-value",
                "raw_response": "raw model payload",
            }
        )
        serialized = json.dumps(metadata, sort_keys=True)

        self.assertEqual(metadata["provider_alias"], "openrouter")
        self.assertEqual(metadata["model_alias"], "nemotron_super")
        self.assertEqual(metadata["failure_category"], "timeout")
        self.assertNotIn("secret prompt text", serialized)
        self.assertNotIn("secret-token-value", serialized)
        self.assertNotIn("raw model payload", serialized)

    def test_model_readiness_reports_missing_config_names_only(self) -> None:
        report = build_openclaw_model_provider_readiness_report(
            available_config_names={
                "PERSONALOS_OPENCLAW_MODEL_PROVIDER": "secret-provider-value"
            }
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], OPENCLAW_MODEL_SMOKE_MISSING_PROVIDER_CONFIG)
        self.assertEqual(
            report["provider_config"]["missing_config_entry_names"],
            [
                "PERSONALOS_OPENCLAW_MODEL_API_KEY",
                "PERSONALOS_OPENCLAW_NEMOTRON_SUPER_MODEL",
                "PERSONALOS_OPENCLAW_GLM_5_2_MODEL",
            ],
        )
        self.assertFalse(report["model_smoke_probe_executed"])
        self.assertTrue(report["provider_config"]["reports_missing_names_only"])
        self.assertFalse(report["provider_config"]["available_config_entry_names_reported"])
        self.assertFalse(report["provider_config"]["credential_values_read"])
        self.assertNotIn("secret-provider-value", serialized)
        self.assertNotIn("PERSONALOS_OPENCLAW_MODEL_PROVIDER", serialized)

    def test_model_readiness_blocks_without_injected_client(self) -> None:
        report = build_openclaw_model_provider_readiness_report(
            available_config_names=OPENCLAW_MODEL_PROVIDER_CONFIG_ENTRY_NAMES
        )

        self.assertEqual(report["status"], OPENCLAW_MODEL_SMOKE_MISSING_CLIENT)
        self.assertFalse(report["client"]["available"])
        self.assertEqual(report["provider_config"]["missing_config_entry_names"], [])
        self.assertFalse(report["model_smoke_probe_executed"])
        self.assertEqual(report["routing"]["primary_alias"], "nemotron_super")
        self.assertEqual(report["routing"]["fallback_alias"], "glm_5_2")

    def test_model_smoke_probe_uses_primary_when_validation_passes(self) -> None:
        client = _RecordingModelSmokeClient(
            [{"success": True, "response_text": OPENCLAW_MODEL_SMOKE_EXPECTED_TEXT}]
        )

        report = run_openclaw_model_smoke_probe(
            available_config_names=OPENCLAW_MODEL_PROVIDER_CONFIG_ENTRY_NAMES,
            client=client,
            client_type="fake_test_model_client",
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], OPENCLAW_MODEL_SMOKE_PASSED)
        self.assertTrue(report["model_smoke_probe_executed"])
        self.assertEqual(report["call_limits"]["primary_calls"], 1)
        self.assertEqual(report["call_limits"]["fallback_calls"], 0)
        self.assertEqual(len(client.requests), 1)
        self.assertEqual(client.requests[0]["model_alias"], "nemotron_super")
        self.assertNotIn("Personal OS Phase 14-C model smoke probe", serialized)

    def test_model_smoke_probe_uses_fallback_only_after_primary_validation_failure(
        self,
    ) -> None:
        client = _RecordingModelSmokeClient(
            [
                {"success": True, "response_text": "malformed"},
                {"success": True, "response_text": OPENCLAW_MODEL_SMOKE_EXPECTED_TEXT},
            ]
        )

        report = run_openclaw_model_smoke_probe(
            available_config_names=OPENCLAW_MODEL_PROVIDER_CONFIG_ENTRY_NAMES,
            client=client,
        )

        self.assertEqual(report["status"], OPENCLAW_MODEL_SMOKE_PASSED)
        self.assertEqual(report["call_limits"]["primary_calls"], 1)
        self.assertEqual(report["call_limits"]["fallback_calls"], 1)
        self.assertEqual([request["model_alias"] for request in client.requests], [
            "nemotron_super",
            "glm_5_2",
        ])
        self.assertFalse(report["probe_results"][0]["validation_passed"])
        self.assertTrue(report["probe_results"][1]["validation_passed"])

    def test_model_smoke_probe_keeps_safe_failure_diagnostics(self) -> None:
        client = _RecordingModelSmokeClient(
            [
                {
                    "success": False,
                    "failure_category": "http_error",
                    "error_kind": "HTTPError",
                    "http_status": 401,
                    "response_text": "unsafe response text",
                },
                {
                    "success": False,
                    "failure_category": "transport_or_parse_error",
                    "error_kind": "SSLCertVerificationError",
                    "raw_error": "unsafe raw error",
                },
            ]
        )

        report = run_openclaw_model_smoke_probe(
            available_config_names=OPENCLAW_MODEL_PROVIDER_CONFIG_ENTRY_NAMES,
            client=client,
        )
        serialized = json.dumps(report, sort_keys=True)

        self.assertEqual(report["status"], "openclaw_model_smoke_validation_failed")
        self.assertEqual(report["call_limits"]["primary_calls"], 1)
        self.assertEqual(report["call_limits"]["fallback_calls"], 1)
        primary_metadata = report["probe_results"][0]["metadata"]
        fallback_metadata = report["probe_results"][1]["metadata"]
        self.assertEqual(primary_metadata["failure_category"], "http_error")
        self.assertEqual(primary_metadata["error_kind"], "HTTPError")
        self.assertEqual(primary_metadata["http_status"], 401)
        self.assertEqual(
            fallback_metadata["failure_category"],
            "transport_or_parse_error",
        )
        self.assertEqual(fallback_metadata["error_kind"], "SSLCertVerificationError")
        self.assertNotIn("unsafe response text", serialized)
        self.assertNotIn("unsafe raw error", serialized)

    def test_model_strategy_doc_records_aliases_lanes_and_boundaries(self) -> None:
        text = " ".join(MODEL_STRATEGY_DOC.read_text(encoding="utf-8").lower().split())

        required_phrases = (
            "phase_14c_supervised_smoke_test.md",
            "nemotron super",
            "glm 5.2",
            "smoke / low-cost lane",
            "reasoning / high-complexity lane",
            "no self-modifying routing logic",
            "no hidden model choice",
            "no provider auto-escalation",
            "max one primary call and one fallback call per smoke probe",
            "full prompts must not be logged",
            "credential values must not be logged",
            "error_kind",
            "http_status",
            "phase14c live-smoke-diagnostics --json",
            "call nemotron super, glm 5.2, openrouter, or any live provider",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


class _RecordingModelSmokeClient:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, object]] = []

    def run_probe(self, request: dict[str, object]) -> dict[str, object]:
        self.requests.append(dict(request))
        if not self.responses:
            return {"success": False, "failure_category": "missing_fake_response"}
        return dict(self.responses.pop(0))


if __name__ == "__main__":
    unittest.main()
