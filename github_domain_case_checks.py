"""Smoke tests for GitHub profile URLs whose domain is capitalized.

Runs with the standard library only (no pytest dependency):

    python -m unittest github_domain_case_checks

Named without the ``test_`` prefix because the repository's .gitignore
excludes ``test_*.py``.
"""

import unittest

from github import extract_github_username
from transform import transform_basics


class ExtractGithubUsernameDomainCaseTests(unittest.TestCase):
    def test_lowercase_domain(self):
        self.assertEqual(
            extract_github_username("https://github.com/octocat"), "octocat"
        )

    def test_capitalized_domain(self):
        self.assertEqual(
            extract_github_username("https://GitHub.com/octocat"), "octocat"
        )

    def test_capitalized_domain_without_scheme(self):
        self.assertEqual(extract_github_username("GitHub.com/octocat"), "octocat")

    def test_uppercase_scheme_and_domain(self):
        self.assertEqual(
            extract_github_username("HTTPS://GITHUB.COM/octocat"), "octocat"
        )

    def test_username_case_is_kept(self):
        self.assertEqual(
            extract_github_username("https://GitHub.com/OctoCat"), "OctoCat"
        )


class TransformBasicsDomainCaseTests(unittest.TestCase):
    def _profile(self, url):
        basics = transform_basics({"name": "x", "profiles": [{"url": url}]})
        return basics["profiles"][0]

    def test_capitalized_github_domain_sets_network_and_username(self):
        profile = self._profile("https://GitHub.com/OctoCat")
        self.assertEqual(profile["network"], "GitHub")
        self.assertEqual(profile["username"], "OctoCat")

    def test_capitalized_linkedin_domain_sets_network_and_username(self):
        profile = self._profile("https://www.LinkedIn.com/in/octo-cat")
        self.assertEqual(profile["network"], "LinkedIn")
        self.assertEqual(profile["username"], "octo-cat")

    def test_lowercase_domain_unchanged(self):
        profile = self._profile("https://github.com/octocat")
        self.assertEqual(profile["network"], "GitHub")
        self.assertEqual(profile["username"], "octocat")


if __name__ == "__main__":
    unittest.main()
