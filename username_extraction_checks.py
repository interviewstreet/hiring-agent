"""Smoke tests for github.extract_github_username.

Runs with the standard library only (no pytest dependency):

    python -m unittest username_extraction_checks

Named without the ``test_`` prefix because the repository's .gitignore
excludes ``test_*.py``.
"""

import unittest

from github import extract_github_username


class ExtractGithubUsernameTests(unittest.TestCase):
    def test_plain_url(self):
        self.assertEqual(
            extract_github_username("https://github.com/octocat"), "octocat"
        )

    def test_no_scheme(self):
        self.assertEqual(extract_github_username("github.com/octocat"), "octocat")

    def test_trailing_slash(self):
        self.assertEqual(
            extract_github_username("https://github.com/octocat/"), "octocat"
        )

    def test_query_parameters_stripped(self):
        self.assertEqual(
            extract_github_username("https://github.com/octocat?tab=repositories"),
            "octocat",
        )

    def test_fragment_stripped(self):
        # Regression for #335: "#projects" must not leak into the username.
        self.assertEqual(
            extract_github_username("https://github.com/octocat#projects"), "octocat"
        )

    def test_trailing_period_stripped(self):
        # Regression for #335: URL pulled from prose ends with a period.
        self.assertEqual(extract_github_username("github.com/octocat."), "octocat")

    def test_trailing_comma_stripped(self):
        # Regression for #335: URL pulled from prose ends with a comma.
        self.assertEqual(extract_github_username("github.com/octocat,"), "octocat")

    def test_at_handle(self):
        self.assertEqual(extract_github_username("@octocat"), "octocat")

    def test_bare_username(self):
        self.assertEqual(extract_github_username("octocat"), "octocat")

    def test_empty_input(self):
        self.assertIsNone(extract_github_username(""))

    def test_none_input(self):
        self.assertIsNone(extract_github_username(None))

    def test_hyphenated_username_preserved(self):
        # Internal hyphens are valid and must survive.
        self.assertEqual(
            extract_github_username("https://github.com/oct-o-cat"), "oct-o-cat"
        )


if __name__ == "__main__":
    unittest.main()
