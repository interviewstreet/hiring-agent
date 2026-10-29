import pytest
from github import extract_github_username, fetch_contributions_count


def test_extract_github_username_standard_urls():
    assert extract_github_username("https://github.com/octocat") == "octocat"
    assert extract_github_username("http://github.com/octocat") == "octocat"
    assert extract_github_username("github.com/octocat") == "octocat"
    assert extract_github_username("@octocat") == "octocat"
    assert extract_github_username("octocat") == "octocat"


def test_extract_github_username_with_query_fragment_and_git_suffix():
    # Query parameters
    assert extract_github_username("https://github.com/octocat?tab=repositories") == "octocat"
    # Fragment identifiers
    assert extract_github_username("https://github.com/octocat#profile") == "octocat"
    # Trailing .git extension
    assert extract_github_username("https://github.com/octocat.git") == "octocat"
    # Trailing slash
    assert extract_github_username("https://github.com/octocat/") == "octocat"
    # Combined fragment and trailing slash
    assert extract_github_username("https://github.com/octocat/#readme") == "octocat"


def test_extract_github_username_empty_and_whitespace():
    assert extract_github_username("") is None
    assert extract_github_username("   ") is None
    assert extract_github_username(None) is None


def test_fetch_contributions_count_standard():
    contributors = [
        {"login": "Alice", "contributions": 42},
        {"login": "Bob", "contributions": 10},
    ]
    user_cnt, total_cnt = fetch_contributions_count("Alice", contributors)
    assert user_cnt == 42
    assert total_cnt == 52

    # Case-insensitive owner match
    user_cnt, total_cnt = fetch_contributions_count("alice", contributors)
    assert user_cnt == 42
    assert total_cnt == 52


def test_fetch_contributions_count_resilience_to_null_and_missing_fields():
    # Anonymous contributor without login, string contribution counts, None owner
    contributors = [
        {"login": None, "contributions": 15},
        {"login": "charlie", "contributions": "5"},
        {"contributions": 3},
        {"login": "david", "contributions": None},
    ]
    # Should not raise AttributeError or TypeError
    user_cnt, total_cnt = fetch_contributions_count("Charlie", contributors)
    assert user_cnt == 5
    assert total_cnt == 23

    # None owner should not crash
    user_cnt, total_cnt = fetch_contributions_count(None, contributors)
    assert user_cnt == 0
    assert total_cnt == 23

    # None or non-list contributors_data should return (0, 0)
    assert fetch_contributions_count("Alice", None) == (0, 0)
    assert fetch_contributions_count("Alice", {}) == (0, 0)

