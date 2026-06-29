import json
import unittest
from pathlib import Path

from personalos.openclaw_model_strategy import (
    OPENCLAW_MODEL_STRATEGY_SCHEMA_VERSION,
    REASONING_LANE,
    SMOKE_LANE,
    build_openclaw_model_call_plan,
    build_openclaw_model_strategy_config,
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
            "call nemotron super, glm 5.2, openrouter, or any live provider",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
