import sys
import types
import unittest


sys.modules.setdefault("models", types.SimpleNamespace(JSONResume=object))

from transform import transform_evaluation_response


class TransformGitHubCsvTests(unittest.TestCase):
    def test_uses_nested_github_profile_data(self):
        row = transform_evaluation_response(
            github_data={
                "profile": {
                    "public_repos": 12,
                    "followers": 34,
                    "following": 5,
                    "created_at": "2024-01-01T00:00:00Z",
                    "bio": "Software engineer",
                },
                "projects": [],
            }
        )

        self.assertEqual(row["github_repos"], 12)
        self.assertEqual(row["github_followers"], 34)
        self.assertEqual(row["github_following"], 5)
        self.assertEqual(row["github_created_at"], "2024-01-01T00:00:00Z")
        self.assertEqual(row["github_bio"], "Software engineer")

    def test_supports_flat_github_data_for_compatibility(self):
        row = transform_evaluation_response(
            github_data={
                "public_repos": 7,
                "followers": 8,
                "following": 9,
                "created_at": "2025-01-01T00:00:00Z",
                "bio": "Builder",
            }
        )

        self.assertEqual(row["github_repos"], 7)
        self.assertEqual(row["github_followers"], 8)
        self.assertEqual(row["github_following"], 9)
        self.assertEqual(row["github_created_at"], "2025-01-01T00:00:00Z")
        self.assertEqual(row["github_bio"], "Builder")


if __name__ == "__main__":
    unittest.main()
