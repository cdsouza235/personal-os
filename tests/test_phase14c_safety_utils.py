import ssl
import unittest
import urllib.error

from personalos.phase14c_safety_utils import (
    config_names_only,
    optional_email,
    optional_string,
    redaction_failure_reasons,
    safe_error_kind,
    unique_reason_codes,
)


class Phase14CSafetyUtilsTest(unittest.TestCase):
    def test_config_names_only_reports_names_not_values(self) -> None:
        names = config_names_only(
            {
                "PERSONALOS_OPENCLAW_MODEL_API_KEY": "secret-openrouter-key",
                "PERSONALOS_PHASE14C_TODOIST_TOKEN": "secret-todoist-token",
            }
        )

        self.assertEqual(
            names,
            (
                "PERSONALOS_OPENCLAW_MODEL_API_KEY",
                "PERSONALOS_PHASE14C_TODOIST_TOKEN",
            ),
        )
        self.assertNotIn("secret-openrouter-key", names)
        self.assertNotIn("secret-todoist-token", names)
        self.assertEqual(config_names_only(["A", "B"]), ("A", "B"))

    def test_optional_string_and_email_are_shape_only(self) -> None:
        self.assertEqual(optional_string("  value  "), "value")
        self.assertIsNone(optional_string("  "))
        self.assertIsNone(optional_string(123))
        self.assertEqual(optional_email("  chris@example.com  "), "chris@example.com")
        self.assertIsNone(optional_email("not an email"))
        self.assertIsNone(optional_email("chris@example"))

    def test_safe_error_kind_reports_class_not_message(self) -> None:
        error = urllib.error.URLError(ssl.SSLError("secret host api_key=abc"))

        self.assertEqual(safe_error_kind(error), "SSLError")
        self.assertNotIn("secret", safe_error_kind(error).lower())
        self.assertEqual(safe_error_kind(ValueError("secret")), "ValueError")

    def test_redaction_failure_reasons_are_codes_only_and_bounded(self) -> None:
        unsafe = {
            "api_key": "secret-openrouter-key",
            "nested": [{"recipient": "chris@example.com"}],
            "message": "Bearer token=abc",
        }

        reasons = redaction_failure_reasons(unsafe)
        serialized = " ".join(reasons)

        self.assertIn("forbidden_raw_field_present", reasons)
        self.assertIn("unmasked_email_value_present", reasons)
        self.assertIn("secret_like_value_present", reasons)
        self.assertNotIn("secret-openrouter-key", serialized)
        self.assertNotIn("chris@example.com", serialized)
        self.assertNotIn("Bearer token=abc", serialized)
        self.assertEqual(
            unique_reason_codes(["a", "b", "a", "c", "b"]),
            ["a", "b", "c"],
        )

    def test_redaction_failure_reasons_fail_closed_on_scan_limits(self) -> None:
        deep: object = "safe"
        for _ in range(4):
            deep = {"child": deep}

        self.assertEqual(
            redaction_failure_reasons(deep, max_depth=2),
            ["redaction_scan_depth_limit_exceeded"],
        )
        self.assertEqual(
            redaction_failure_reasons(["safe", "safe", "safe"], max_nodes=2),
            ["redaction_scan_node_limit_exceeded"],
        )


if __name__ == "__main__":
    unittest.main()
