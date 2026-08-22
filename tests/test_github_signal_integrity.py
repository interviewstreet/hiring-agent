"""Tests that computed GitHub signals survive to the scoring prompt.

criteria.jinja:60 makes "all projects are self_project" a hard 10-point ceiling on
open_source, and system_message.jinja:23/49 tells the model to read project_type.
Those fields are computed in github.py at the cost of one API call per repository.
If they never reach the prompt the rule is decided by hallucination, which is what
happened before these tests existed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from transform import convert_github_data_to_text  # noqa: E402


def project(name, **overrides):
    base = {
        "name": name,
        "description": f"{name} description",
        "github_url": f"https://github.com/u/{name}",
        "live_url": None,
        "technologies": ["Python"],
        "project_type": "self_project",
        "contributor_count": 1,
        "author_commit_count": 42,
        "total_commit_count": 42,
        "github_details": {"stars": 1, "forks": 0, "language": "Python"},
    }
    base.update(overrides)
    return base


def test_project_type_reaches_the_prompt():
    """The field the rubric's hard ceiling branches on must be present."""
    text = convert_github_data_to_text(
        {"projects": [project("a", project_type="open_source")]}
    )
    assert "Project Type: open_source" in text


def test_both_project_types_are_distinguishable_in_the_prompt():
    text = convert_github_data_to_text(
        {
            "projects": [
                project("multi", project_type="open_source", contributor_count=3),
                project("solo", project_type="self_project", contributor_count=1),
            ]
        }
    )
    assert "Project Type: open_source" in text
    assert "Project Type: self_project" in text


def test_commit_attribution_reaches_the_prompt():
    """github_project_selection.jinja states a >=4 author-commit requirement."""
    text = convert_github_data_to_text(
        {"projects": [project("a", author_commit_count=7, total_commit_count=120)]}
    )
    assert "Author Commits: 7 of 120 total" in text


def test_contributor_count_reaches_the_prompt():
    text = convert_github_data_to_text(
        {"projects": [project("a", contributor_count=5)]}
    )
    assert "Contributors: 5" in text


def test_live_demo_url_reaches_the_prompt():
    """A working demo is the largest single modifier in the rubric."""
    text = convert_github_data_to_text(
        {"projects": [project("a", live_url="https://demo.example.com")]}
    )
    assert "Live Demo URL: https://demo.example.com" in text


def test_absent_live_url_renders_as_None_not_a_blank():
    """The model must be able to tell 'no demo' from a missing field."""
    text = convert_github_data_to_text({"projects": [project("a", live_url=None)]})
    assert "Live Demo URL: None" in text


def test_missing_computed_fields_render_as_unknown_rather_than_vanishing():
    """A cache written before this change lacks the fields; say so explicitly."""
    stripped = {
        "name": "legacy",
        "description": "d",
        "github_url": "u",
        "github_details": {"stars": 0, "forks": 0, "language": "Go"},
    }
    text = convert_github_data_to_text({"projects": [stripped]})
    assert "Project Type: unknown" in text
    assert "Contributors: N/A" in text


def test_existing_fields_are_still_emitted():
    """Regression guard: the change must be additive."""
    text = convert_github_data_to_text({"projects": [project("a")]})
    for expected in ("1. a", "Description: a description", "URL: https://", "Stars: 1"):
        assert expected in text
