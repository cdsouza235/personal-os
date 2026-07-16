"""P-KE-1B: engine.directness -- amendment §11.3 directness + §8.3 P0 inclusion
rule / §8.2 P2 gate boundary cases."""

from __future__ import annotations

import unittest

from personalos.knowledge_edge.engine import directness
from personalos.knowledge_edge.state.media import DIRECTNESS_CLASSES


class ClassifyDirectnessTest(unittest.TestCase):
    def test_every_format_hint_maps_to_a_known_directness_class(self) -> None:
        for format_hint in directness.ALL_FORMAT_HINTS:
            duration = 600 if format_hint == directness.FINANCIAL_MEDIA_SEGMENT else None
            result = directness.classify_directness(format_hint=format_hint, duration_seconds=duration)
            self.assertIn(result, DIRECTNESS_CLASSES)

    def test_financial_media_segment_unknown_duration_is_ambiguous(self) -> None:
        result = directness.classify_directness(format_hint="financial_media_segment", duration_seconds=None)
        self.assertEqual(result, "ambiguous")

    def test_financial_media_segment_known_duration_is_direct_primary_regardless_of_length(self) -> None:
        short = directness.classify_directness(format_hint="financial_media_segment", duration_seconds=30)
        long = directness.classify_directness(format_hint="financial_media_segment", duration_seconds=600)
        self.assertEqual(short, "direct_primary")
        self.assertEqual(long, "direct_primary")

    def test_original_long_form_interview_is_direct_primary(self) -> None:
        self.assertEqual(
            directness.classify_directness(format_hint="original_long_form_interview", duration_seconds=None),
            "direct_primary",
        )

    def test_panel_fireside_is_panel_participant(self) -> None:
        self.assertEqual(
            directness.classify_directness(format_hint="panel_fireside", duration_seconds=None),
            "panel_participant",
        )

    def test_reaction_video_is_commentary_about(self) -> None:
        self.assertEqual(
            directness.classify_directness(format_hint="reaction_video", duration_seconds=None),
            "commentary_about",
        )

    def test_unknown_format_hint_rejected(self) -> None:
        with self.assertRaises(ValueError):
            directness.classify_directness(format_hint="not_a_real_format", duration_seconds=None)


class ClassifySubstantiveAppearanceTest(unittest.TestCase):
    def test_ambiguous_never_promoted_and_never_reason_says_dropped(self) -> None:
        directness_class = directness.classify_directness(
            format_hint="financial_media_segment", duration_seconds=None
        )
        eligible, reason = directness.classify_substantive_appearance(
            format_hint="financial_media_segment",
            directness_class=directness_class,
            duration_seconds=None,
        )
        self.assertFalse(eligible)
        self.assertEqual(reason, "ambiguous_unknown_duration_demoted")

    def test_financial_media_segment_below_threshold_not_substantive(self) -> None:
        directness_class = directness.classify_directness(
            format_hint="financial_media_segment", duration_seconds=60
        )
        eligible, reason = directness.classify_substantive_appearance(
            format_hint="financial_media_segment",
            directness_class=directness_class,
            duration_seconds=60,
            duration_threshold_seconds=300,
        )
        self.assertFalse(eligible)
        self.assertEqual(reason, "financial_media_segment_duration_below_threshold")

    def test_financial_media_segment_at_threshold_is_substantive(self) -> None:
        directness_class = directness.classify_directness(
            format_hint="financial_media_segment", duration_seconds=300
        )
        eligible, reason = directness.classify_substantive_appearance(
            format_hint="financial_media_segment",
            directness_class=directness_class,
            duration_seconds=300,
            duration_threshold_seconds=300,
        )
        self.assertTrue(eligible)
        self.assertEqual(reason, "financial_media_segment_duration_threshold_met")

    def test_each_of_the_seven_substantive_formats_is_eligible(self) -> None:
        for format_hint in directness.SUBSTANTIVE_FORMATS_NO_DURATION_CHECK:
            directness_class = directness.classify_directness(format_hint=format_hint, duration_seconds=None)
            eligible, _reason = directness.classify_substantive_appearance(
                format_hint=format_hint, directness_class=directness_class, duration_seconds=None
            )
            self.assertTrue(eligible, f"{format_hint} should be substantive")

    def test_each_excluded_format_is_never_substantive_even_with_generous_duration(self) -> None:
        for format_hint in directness.EXCLUDED_FORMATS:
            directness_class = directness.classify_directness(format_hint=format_hint, duration_seconds=9999)
            eligible, _reason = directness.classify_substantive_appearance(
                format_hint=format_hint, directness_class=directness_class, duration_seconds=9999
            )
            self.assertFalse(eligible, f"{format_hint} must never be substantive")

    def test_mentioned_only_and_host_or_interviewer_are_never_substantive(self) -> None:
        for format_hint in ("mentioned_only_appearance", "host_or_interviewer_appearance"):
            directness_class = directness.classify_directness(format_hint=format_hint, duration_seconds=None)
            eligible, _reason = directness.classify_substantive_appearance(
                format_hint=format_hint, directness_class=directness_class, duration_seconds=None
            )
            self.assertFalse(eligible)


if __name__ == "__main__":
    unittest.main()
