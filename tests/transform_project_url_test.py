import sys
import types
import unittest


sys.modules.setdefault("models", types.SimpleNamespace(JSONResume=object))

from transform import transform_projects


class TransformProjectUrlTests(unittest.TestCase):
    def test_uses_github_url_when_url_is_missing(self):
        projects = transform_projects(
            [
                {
                    "name": "Example",
                    "description": "Example project",
                    "github_url": "https://github.com/example/project",
                    "technologies": ["Python"],
                }
            ]
        )

        self.assertEqual(projects[0]["url"], "https://github.com/example/project")

    def test_uses_live_url_when_url_and_github_url_are_missing(self):
        projects = transform_projects(
            [
                {
                    "name": "Example",
                    "description": "Example project",
                    "live_url": "https://example.com",
                    "technologies": ["Python"],
                }
            ]
        )

        self.assertEqual(projects[0]["url"], "https://example.com")

    def test_preserves_explicit_url_over_fallbacks(self):
        projects = transform_projects(
            [
                {
                    "name": "Example",
                    "url": "https://docs.example.com",
                    "github_url": "https://github.com/example/project",
                    "live_url": "https://example.com",
                }
            ]
        )

        self.assertEqual(projects[0]["url"], "https://docs.example.com")


if __name__ == "__main__":
    unittest.main()
