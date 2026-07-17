"""P-KE-2C: shadow_live admission fence tests (personalos.knowledge_edge.shadow_mode).

No network-capable import anywhere in this module or the module under test.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from personalos import config as config_module
from personalos.knowledge_edge import shadow_mode


class ShadowDatabasePathTest(unittest.TestCase):
    def test_shadow_db_path_matches_ad4_exactly(self) -> None:
        self.assertEqual(
            shadow_mode.SHADOW_DB_PATH,
            (Path.home() / ".personalos" / "shadow" / "personalos-shadow.sqlite3").expanduser(),
        )

    def test_shadow_db_path_is_outside_the_repo(self) -> None:
        # P-KE-2E regression (the COLLISION defect): the shadow DB must not live
        # under REPO_ROOT, or the harness's untracked-file wipe destroys it on every
        # packet run -- exactly what happened to the original var/shadow/ location.
        self.assertFalse(
            shadow_mode.SHADOW_DB_PATH.is_relative_to(config_module.REPO_ROOT.resolve())
        )

    def test_require_shadow_database_path_accepts_the_exact_path(self) -> None:
        resolved = shadow_mode.require_shadow_database_path(shadow_mode.SHADOW_DB_PATH)
        self.assertEqual(resolved, shadow_mode.SHADOW_DB_PATH.resolve())

    def test_require_shadow_database_path_refuses_any_other_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            other_path = Path(temp_dir) / "not-shadow.sqlite3"
            with self.assertRaises(shadow_mode.ShadowModeViolation):
                shadow_mode.require_shadow_database_path(other_path)

    def test_require_shadow_database_path_refuses_dev_path(self) -> None:
        with self.assertRaises(shadow_mode.ShadowModeViolation):
            shadow_mode.require_shadow_database_path(config_module.DEV_DB_PATH)

    def test_require_shadow_database_path_refuses_the_old_repo_local_path(self) -> None:
        # Regression for the exact COLLISION defect (P-KE-2E): the pre-amendment
        # repo-local path must now be refused, not silently still admitted.
        old_repo_local_path = config_module.RUNTIME_DIR / "shadow" / "personalos-shadow.sqlite3"
        with self.assertRaises(shadow_mode.ShadowModeViolation):
            shadow_mode.require_shadow_database_path(old_repo_local_path)


class RefusalSurfaceTest(unittest.TestCase):
    def test_notification_send_refused_in_shadow_live(self) -> None:
        with self.assertRaises(shadow_mode.ShadowModeViolation):
            shadow_mode.refuse_notification_send("shadow_live")

    def test_obsidian_write_refused_in_shadow_live(self) -> None:
        with self.assertRaises(shadow_mode.ShadowModeViolation):
            shadow_mode.refuse_obsidian_write("shadow_live")

    def test_scheduler_activation_refused_in_shadow_live(self) -> None:
        with self.assertRaises(shadow_mode.ShadowModeViolation):
            shadow_mode.refuse_scheduler_activation("shadow_live")

    def test_every_refusal_surface_is_a_no_op_outside_shadow_live(self) -> None:
        for mode in ("disabled", "fixture", "active_read_only", "active_with_obsidian_handoff"):
            with self.subTest(mode=mode):
                shadow_mode.refuse_notification_send(mode)
                shadow_mode.refuse_obsidian_write(mode)
                shadow_mode.refuse_scheduler_activation(mode)

    def test_refuse_if_shadow_live_names_the_surface_in_the_error(self) -> None:
        with self.assertRaises(shadow_mode.ShadowModeViolation) as ctx:
            shadow_mode.refuse_if_shadow_live("shadow_live", surface="a made-up surface")
        self.assertIn("a made-up surface", str(ctx.exception))


class ProductionDatabaseRefusalTest(unittest.TestCase):
    def test_production_path_refused_in_shadow_live(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            stand_in = Path(temp_dir) / "PersonalOS" / "personal_os.db"
            with mock.patch.object(config_module, "PRODUCTION_DB_PATH", stand_in):
                with self.assertRaises(shadow_mode.ShadowModeViolation):
                    shadow_mode.refuse_production_database("shadow_live", stand_in)

    def test_production_path_allowed_outside_shadow_live(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            stand_in = Path(temp_dir) / "PersonalOS" / "personal_os.db"
            with mock.patch.object(config_module, "PRODUCTION_DB_PATH", stand_in):
                # No exception: this function only narrows shadow_live, never any
                # other mode -- production-path admission for other modes is a
                # different packet's own gate (Session 3), not this module's job.
                shadow_mode.refuse_production_database("active_read_only", stand_in)

    def test_non_production_path_allowed_in_shadow_live(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            other_path = Path(temp_dir) / "not-production.sqlite3"
            shadow_mode.refuse_production_database("shadow_live", other_path)


class ValidateShadowAdmissionTest(unittest.TestCase):
    def test_no_op_outside_shadow_live(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            arbitrary_path = Path(temp_dir) / "whatever.sqlite3"
            shadow_mode.validate_shadow_admission(
                feature_mode="fixture", database_path=arbitrary_path
            )

    def test_accepts_shadow_path_in_shadow_live(self) -> None:
        shadow_mode.validate_shadow_admission(
            feature_mode="shadow_live", database_path=shadow_mode.SHADOW_DB_PATH
        )

    def test_refuses_non_shadow_path_in_shadow_live(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            other_path = Path(temp_dir) / "not-shadow.sqlite3"
            with self.assertRaises(shadow_mode.ShadowModeViolation):
                shadow_mode.validate_shadow_admission(
                    feature_mode="shadow_live", database_path=other_path
                )

    def test_refuses_production_path_in_shadow_live_even_though_it_also_fails_the_shadow_check(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            stand_in = Path(temp_dir) / "PersonalOS" / "personal_os.db"
            with mock.patch.object(config_module, "PRODUCTION_DB_PATH", stand_in):
                with self.assertRaises(shadow_mode.ShadowModeViolation) as ctx:
                    shadow_mode.validate_shadow_admission(
                        feature_mode="shadow_live", database_path=stand_in
                    )
                self.assertIn("production database path is refused", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
