import dataclasses
from typing import Optional

import pytest

import github


@dataclasses.dataclass(frozen=True)
class Scenario:
    github_url: str
    expected_username: Optional[str]


@pytest.mark.parametrize(
    "scenario",
    [
        pytest.param(
            Scenario(
                github_url="https://github.com/nistepanov",
                expected_username="nistepanov",
            ),
            id="plain_url",
        ),
        pytest.param(
            Scenario(
                github_url="https://github.com/nistepanov/",
                expected_username="nistepanov",
            ),
            id="trailing_slash",
        ),
        pytest.param(
            Scenario(
                github_url="github.com/nistepanov?tab=repositories",
                expected_username="nistepanov",
            ),
            id="query_string",
        ),
        pytest.param(
            Scenario(
                github_url="http://www.github.com/a-b/repo",
                expected_username="a-b",
            ),
            id="repo_path_and_hyphen",
        ),
        pytest.param(
            Scenario(
                github_url="https://github.com/ nistepanov",
                expected_username="nistepanov",
            ),
            id="url_split_by_space",
        ),
        pytest.param(
            Scenario(github_url="@octocat", expected_username="octocat"),
            id="at_handle",
        ),
        pytest.param(
            Scenario(github_url="octocat", expected_username="octocat"),
            id="bare_username",
        ),
    ],
)
def test_extract_github_username_accepts_valid_forms(scenario):
    """Checks that every common way to write a profile gives the username."""
    # given
    github_url = scenario.github_url

    # when
    username = github.extract_github_username(github_url)

    # then
    assert username == scenario.expected_username


@pytest.mark.parametrize(
    "scenario",
    [
        pytest.param(
            Scenario(
                github_url=(
                    "https://github.com/nistepanovmodel: wait, "
                    "url format schema requires valid JSON"
                ),
                expected_username=None,
            ),
            id="llm_text_glued_to_url",
        ),
        pytest.param(
            Scenario(github_url="https://github.com/-bad", expected_username=None),
            id="leading_hyphen",
        ),
        pytest.param(
            Scenario(
                github_url="https://linkedin.com/in/someone", expected_username=None
            ),
            id="non_github_url",
        ),
        pytest.param(
            Scenario(github_url="", expected_username=None),
            id="empty_string",
        ),
    ],
)
def test_extract_github_username_rejects_malformed_input(scenario):
    """Checks that junk input gives None, not a wrong account to query."""
    # given
    github_url = scenario.github_url

    # when
    username = github.extract_github_username(github_url)

    # then
    assert username == scenario.expected_username
