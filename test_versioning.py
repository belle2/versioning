import subprocess
import unittest
from unittest import mock

from versioning import (
    _recommended_release,
    _supported_releases,
    _supported_pre_releases,
    _supported_light_releases,
    _analysis_tags_per_major_version,
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
        latest_release = _supported_releases[-1]
        base, patch = latest_release.rsplit("-", 1)
        newer_release = f"{base}-{int(patch) + 1:02d}"
        self.assertEqual(supported_release(newer_release), newer_release)
        # Test with a release that should snap to the next supported one
        self.assertEqual(supported_release("release-06-00-00"), _supported_releases[0])

    def test_supported_release_prerelease(self):
        if _supported_pre_releases:
            # Test with a supported prerelease
            self.assertEqual(
                supported_release(_supported_pre_releases[0]), _supported_pre_releases[0]
            )
            # Test with a newer prerelease that is not explicitly in the list but should be considered supported
            self.assertEqual(
                supported_release(_supported_pre_releases[-1][:-1]+'z'), _supported_pre_releases[-1][:-1]+'z'
            )
        else:
            # If no prerelease is officially supported, newer prereleases fall back to the latest full release
            self.assertEqual(
                supported_release("prerelease-99-00-00z"), _supported_releases[-1]
            )

        # Test with a prerelease that should snap to the next supported full release
        self.assertEqual(
            supported_release('prerelease-00-00-00z'), _supported_releases[0]
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
        # Test with "prerelease-" should return the latest prerelease, if any
        expected_pre_release = (
            _supported_pre_releases[-1]
            if _supported_pre_releases
            else _supported_releases[-1]
        )
        self.assertEqual(supported_release("prerelease-"), expected_pre_release)

    def test_supported_release_unknown(self):
        # Test with an unknown release, should return the latest full release
        self.assertEqual(supported_release("unknown-release"), _supported_releases[-1])

    def test_get_supported_releases(self):
        # Test get_supported_releases without light argument
        releases = get_supported_releases()
        self.assertIsInstance(releases, list)
        self.assertIn(_supported_releases[-1], releases)
        if _supported_pre_releases:
            self.assertIn(_supported_pre_releases[-1], releases)
        else:
            self.assertFalse(any(release.startswith("prerelease-") for release in releases))
        self.assertNotIn(_recommended_release, releases)

        # Test get_supported_releases with light=True
        light_releases = list(get_supported_releases(light=True))
        self.assertIsInstance(light_releases, list)
        self.assertIn(_recommended_release, light_releases)
        self.assertNotIn(_supported_releases[-1], light_releases)
        self.assertFalse(any(release.startswith("prerelease-") for release in light_releases))

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

    def test_recommended_global_tags_v2_latest_release(self):
        # Data and MC tags are only mapped for the latest full release
        result = recommended_global_tags_v2(
            release=_supported_releases[-1], base_tags=[], user_tags=[], metadata=None
        )
        self.assertIn("data_reprocessing_proc9", result["tags"])
        self.assertIn("mc_production_mc12", result["tags"])
        self.assertIn("online", result["tags"])

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

    def test_recommended_global_tags_analysis_tag_release_11(self):
        # release-11 must get an analysis GT (it was missing after moving it from prerelease to full release)
        result = recommended_global_tags_v2(
            release="release-11-00-00", base_tags=[], user_tags=[], metadata=None
        )
        self.assertEqual(result["tags"][0], "analysis_tools_light-2603-ina")
        self.assertNotIn("There is no recommended analysis global tag", result["message"])

    def test_analysis_tags_per_major_version_complete(self):
        # Every supported full release and prerelease must have its major version mapped to an analysis GT
        for release in _supported_releases + _supported_pre_releases:
            with self.subTest(release=release):
                self.assertIn(release.split("-")[1], _analysis_tags_per_major_version)

    def test_recommended_global_tags_analysis_tag_all_supported(self):
        # Every supported release must have a recommended analysis GT
        for release in _supported_releases + _supported_pre_releases + _supported_light_releases:
            with self.subTest(release=release):
                result = recommended_global_tags_v2(
                    release=release, base_tags=[], user_tags=[], metadata=None
                )
                self.assertTrue(result["tags"][0].startswith("analysis_tools_"))
                self.assertNotIn("There is no recommended analysis global tag", result["message"])

    def test_recommended_global_tags_analysis_tag_newer_patch_release(self):
        # A patch release newer than the latest supported one gets the analysis GT of its major version
        latest_release = _supported_releases[-1]
        base, patch = latest_release.rsplit("-", 1)
        newer_release = f"{base}-{int(patch) + 1:02d}"
        latest_result = recommended_global_tags_v2(
            release=latest_release, base_tags=[], user_tags=[], metadata=None
        )
        newer_result = recommended_global_tags_v2(
            release=newer_release, base_tags=[], user_tags=[], metadata=None
        )
        self.assertTrue(newer_result["tags"][0].startswith("analysis_tools_"))
        self.assertEqual(newer_result["tags"][0], latest_result["tags"][0])

    def test_recommended_global_tags_analysis_tag_unknown_major(self):
        # A release with an unknown major version has no analysis GT and the user is warned
        result = recommended_global_tags_v2(
            release="release-99-00-00", base_tags=[], user_tags=[], metadata=None
        )
        self.assertFalse(any(tag.startswith("analysis_") for tag in result["tags"]))
        self.assertIn("There is no recommended analysis global tag", result["message"])

    def test_recommended_global_tags_analysis_tag_git_hash(self):
        # For a local build ("release" is a git hash) the analysis GT is taken
        # from the closest supported ancestor tag
        for ancestor, expected in [
            ("release-11-00-00", "analysis_tools_light-2603-ina"),
            ("release-09-00-20", "analysis_tools_light-2406-ragdoll"),
            (_supported_light_releases[0], f"analysis_tools_{_supported_light_releases[0]}"),
        ]:
            with self.subTest(ancestor=ancestor):
                with mock.patch("versioning.subprocess.check_output",
                                return_value=f"some-unsupported-tag\n{ancestor}\nrelease-06-00-14\n"):
                    result = recommended_global_tags_v2(
                        release="846b6bffa5-modified", base_tags=[], user_tags=[], metadata=None
                    )
                self.assertEqual(result["tags"][0], expected)

        # No supported ancestor or not a git repository: fall back to the recommended release
        expected = f"analysis_tools_{_recommended_release}"
        with mock.patch("versioning.subprocess.check_output", return_value="some-unsupported-tag\n"):
            result = recommended_global_tags_v2(
                release="846b6bffa5", base_tags=[], user_tags=[], metadata=None
            )
        self.assertEqual(result["tags"][0], expected)
        error = subprocess.CalledProcessError(128, "git", output="fatal: not a git repository")
        with mock.patch("versioning.subprocess.check_output", side_effect=error):
            result = recommended_global_tags_v2(
                release="846b6bffa5", base_tags=[], user_tags=[], metadata=None
            )
        self.assertEqual(result["tags"][0], expected)

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
