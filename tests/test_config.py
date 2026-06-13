import unittest

from personalos.config import (
    DEFAULT_TIMEZONE,
    RUNTIME_DIR,
    Environment,
    ProductionConfigUnavailable,
    load_config,
)


class ConfigBoundaryTest(unittest.TestCase):
    def test_default_environment_is_safe_non_production(self) -> None:
        config = load_config()

        self.assertEqual(config.environment, Environment.DEVELOPMENT)
        self.assertFalse(config.is_production)

    def test_default_timezone_is_america_chicago(self) -> None:
        self.assertEqual(load_config().timezone, DEFAULT_TIMEZONE)
        self.assertEqual(DEFAULT_TIMEZONE, "America/Chicago")

    def test_dev_and_test_database_paths_stay_inside_runtime_area(self) -> None:
        expected_runtime_dirs = {
            Environment.DEVELOPMENT: "dev",
            Environment.TEST: "test",
        }

        for environment in (Environment.DEVELOPMENT, Environment.TEST):
            with self.subTest(environment=environment):
                config = load_config(environment)

                self.assertEqual(config.database_path.suffix, ".sqlite3")
                runtime_relative_path = config.database_path.resolve().relative_to(
                    RUNTIME_DIR.resolve()
                )
                self.assertEqual(runtime_relative_path.parts[0], expected_runtime_dirs[environment])

    def test_production_config_is_not_selected_by_default(self) -> None:
        self.assertNotEqual(load_config().environment, Environment.PRODUCTION)

    def test_production_config_is_unavailable(self) -> None:
        with self.assertRaises(ProductionConfigUnavailable):
            load_config(Environment.PRODUCTION)
