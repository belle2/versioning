import unittest
from versioning import (
    _recommended_release,
    _supported_releases,
    _supported_pre_releases,
    _supported_light_releases,
    supported_release,
    recommended_global_tags_v2,
    get_supported_releases,
    get_recommended_training_release,
    recommended_b2bii_analysis_global_tag,
    performance_recommendation_global_tag,
)


class TestVersioning(unittest.TestCase):
    def test_supported_release_none(self):
        # Test with no release provided, should return the recommended release
        self.assertEqual(supported_release(None), _recommended_release)

    def test_supported_release_full(self):
        # Test with a supported full release
        self.assertEqual(
            supported_release(_supported_releases[3]), _supported_releases[3]
        )
        # Test with a newer full release that is not explicitly in the list but should be considered supported
        self.assertEqual(supported_release("release-09-99-10"), "release-09-99-10")
        # Test with a release that should snap to the next supported one
        self.assertEqual(supported_release("release-06-00-00"), _supported_releases[0])

    def test_supported_release_prerelease(self):
        # Test with a supported prerelease
        self.assertEqual(
            supported_release(_supported_pre_releases[0]), _supported_pre_releases[0]
        )
        # Test with a newer prerelease that is not explicitly in the list but should be considered supported
        self.assertEqual(
            supported_release(_supported_pre_releases[-1][:-1]+'z'), _supported_pre_releases[-1][:-1]+'z'
        )
        # Test with a prerelease that should snap to the next supported one
        self.assertEqual(
            supported_release('prerelease-10-00-00z'), _supported_pre_releases[-1]
        )

    def test_supported_release_light(self):
        # Test with a supported light release
        self.assertEqual(
            supported_release(_supported_light_releases[0]),
            _supported_light_releases[0],
        )
        # Test with an unsupported light release, should return the latest supported light release
        self.assertEqual(
            supported_release("light-2000-unsupported"), _recommended_release
        )

    def test_supported_release_latest(self):
        # Test with "release-" should return the latest full release
        self.assertEqual(supported_release("release-"), _supported_releases[-1])
        # Test with "prerelease-" should return the latest prerelease
        self.assertEqual(supported_release("prerelease-"), _supported_pre_releases[-1])

    def test_supported_release_unknown(self):
        # Test with an unknown release, should return the latest full release
        self.assertEqual(supported_release("unknown-release"), _supported_releases[-1])

    def test_get_supported_releases(self):
        # Test get_supported_releases without light argument
        releases = get_supported_releases()
        self.assertIsInstance(releases, list)
        self.assertIn(_supported_releases[-1], releases)
        self.assertIn(_supported_pre_releases[-1], releases)
        self.assertNotIn(_recommended_release, releases)

        # Test get_supported_releases with light=True
        light_releases = list(get_supported_releases(light=True))
        self.assertIsInstance(light_releases, list)
        self.assertIn(_recommended_release, light_releases)
        self.assertNotIn(_supported_releases[-1], light_releases)
        self.assertNotIn(_supported_pre_releases[-1], light_releases)

    def test_get_recommended_training_release(self):
        self.assertEqual(get_recommended_training_release(), _recommended_release)

    def test_recommended_global_tags_v2_default(self):
        # Test with default parameters (no base_tags, no user_tags, no metadata)
        result = recommended_global_tags_v2(
            release="release-09-00-06", base_tags=[], user_tags=[], metadata=None
        )
        expected_tags = [
            "analysis_tools_light-2406-ragdoll",
            "online",
            "mc_production_mc12",
            "data_reprocessing_proc9",
        ]
        self.assertIsInstance(result, dict)
        self.assertListEqual(sorted(result["tags"]), sorted(expected_tags))
        self.assertIn(
            f"You are using release-09-00-06, but we recommend to use {supported_release('release-09-00-06')}.\n",
            result["message"],
        )
        self.assertIn(
            "The recommended tags differ from the base tags: \nUse the default conditions configuration if you want to take the base tags.\n",
            result["message"],
        )

    def test_recommended_global_tags_v2_with_base_tags(self):
        # Test with existing base tags
        result = recommended_global_tags_v2(
            release="release-09-00-08",
            base_tags=["main_v1", "data_v2"],
            user_tags=[],
            metadata=None,
        )
        expected_tags = [
            "analysis_tools_light-2406-ragdoll",
            "online",
            "mc_production_mc12",
            "data_reprocessing_proc9",
            "main_v1",
        ]
        self.assertIsInstance(result, dict)
        self.assertListEqual(sorted(result["tags"]), sorted(expected_tags))
        self.assertIn(
            f"You are using release-09-00-08, but we recommend to use {supported_release('release-09-00-08')}.\n",
            result["message"],
        )
        self.assertIn(
            "The recommended tags differ from the base tags: main_v1 data_v2\nUse the default conditions configuration if you want to take the base tags.\n",
            result["message"],
        )

    def test_recommended_global_tags_v2_with_metadata_data(self):
        # Test with metadata for data (isMC=False)
        metadata = [
            {
                "release": "release-08-01-06",
                "isMC": False,
                "experimentLow": 1,
                "experimentHigh": 1,
            }
        ]
        result = recommended_global_tags_v2(
            release="release-09-00-02", base_tags=[], user_tags=[], metadata=metadata
        )
        # For data, mc_production_mc12 should not be added if not already present in base_tags
        expected_tags = [
            "analysis_tools_light-2406-ragdoll",
            "online",
            "data_reprocessing_proc9",
        ]
        self.assertIsInstance(result, dict)
        self.assertListEqual(sorted(result["tags"]), sorted(expected_tags))
        self.assertIn(
            f"You are using release-09-00-02, but we recommend to use {supported_release('release-09-00-08')}.\n",
            result["message"],
        )
        self.assertIn(
            "The recommended tags differ from the base tags: \nUse the default conditions configuration if you want to take the base tags.\n",
            result["message"],
        )

    def test_recommended_global_tags_b2bii(self):
        # Test for B2BII case (metadata is an empty list)
        result = recommended_global_tags_v2(
            release=_recommended_release, base_tags=[], user_tags=[], metadata=[]
        )
        self.assertIsInstance(result, dict)
        self.assertListEqual(
            result["tags"], [f"analysis_tools_{_recommended_release}", "B2BII"]
        )
        self.assertIn(
            "The recommended tags differ from the base tags: \nUse the default conditions configuration if you want to take the base tags.\n",
            result["message"],
        )

    def test_recommended_global_tags_analysis_tag_from_release(self):
        # Test that analysis tag is correctly derived from release
        result = recommended_global_tags_v2(
            release="release-08-00-10", base_tags=[], user_tags=[], metadata=None
        )
        self.assertIn("analysis_tools_light-2305-korat", result["tags"])

        result = recommended_global_tags_v2(
            release=_supported_light_releases[2],
            base_tags=[],
            user_tags=[],
            metadata=None,
        )
        self.assertIn(f"analysis_tools_{_supported_light_releases[2]}", result["tags"])

    def test_recommended_b2bii_analysis_global_tag(self):
        self.assertEqual(recommended_b2bii_analysis_global_tag(), "analysis_b2bii")

    def test_performance_recommendation_global_tag(self):
        result_mc15 = performance_recommendation_global_tag(campaign="MC15")
        self.assertEqual(
            result_mc15["global_tag"], "analysis_performance_recommendation_MC15"
        )
        self.assertEqual(result_mc15["payload"], "recommendation_payload")

        result_mc16 = performance_recommendation_global_tag(campaign="MC16")
        self.assertEqual(
            result_mc16["global_tag"], "analysis_performance_recommendation_MC16"
        )
        self.assertEqual(result_mc16["payload"], "recommendation_payload")

        result_mc17 = performance_recommendation_global_tag(campaign="MC17")
        self.assertEqual(result_mc17["global_tag"], "")
        self.assertEqual(result_mc17["payload"], "recommendation_payload")

        result_default = performance_recommendation_global_tag()  # Defaults to MC15
        self.assertEqual(
            result_default["global_tag"], "analysis_performance_recommendation_MC15"
        )


if __name__ == "__main__":
    unittest.main()
