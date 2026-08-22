"""Tests that LLM-restated project facts never override fetched data.

The selection call asks the model to echo each project back, and its echo drops
project_type and contributor_count while re-typing stars and commit counts from
memory. resolve_selected_projects keeps the model's *choice* and its stated
rationale, and takes every fact from the fetched record.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from github import resolve_selected_projects  # noqa: E402


def fetched(name, **overrides):
    base = {
        "name": name,
        "description": "real description",
        "github_url": f"https://github.com/u/{name}",
        "live_url": None,
        "project_type": "open_source",
        "contributor_count": 3,
        "author_commit_count": 42,
        "total_commit_count": 120,
        "github_details": {"stars": 7, "forks": 2, "language": "Python"},
    }
    base.update(overrides)
    return base


def test_computed_fields_survive_the_llm_echo():
    """project_type and contributor_count are absent from the model's echo."""
    llm_echo = [{"name": "trelix", "description": "whatever the model recalled"}]
    resolved, seen = resolve_selected_projects(llm_echo, [fetched("trelix")])
    assert seen == {"trelix"}
    assert resolved[0]["project_type"] == "open_source"
    assert resolved[0]["contributor_count"] == 3


def test_hallucinated_facts_are_discarded_in_favour_of_fetched_ones():
    """A model-invented star or commit count must not reach the prompt."""
    llm_echo = [
        {
            "name": "trelix",
            "description": "INVENTED",
            "author_commit_count": 9999,
            "total_commit_count": 9999,
            "github_details": {"stars": 5000, "forks": 900, "language": "Rust"},
        }
    ]
    resolved, _ = resolve_selected_projects(llm_echo, [fetched("trelix")])
    assert resolved[0]["description"] == "real description"
    assert resolved[0]["author_commit_count"] == 42
    assert resolved[0]["total_commit_count"] == 120
    assert resolved[0]["github_details"]["stars"] == 7
    assert resolved[0]["github_details"]["language"] == "Python"


def test_model_rationale_is_preserved():
    """The reason is the model's own contribution, not a restatement."""
    llm_echo = [
        {"name": "trelix", "reason_for_project_selection": "hybrid retrieval depth"}
    ]
    resolved, _ = resolve_selected_projects(llm_echo, [fetched("trelix")])
    assert resolved[0]["reason_for_project_selection"] == "hybrid retrieval depth"


def test_invented_project_names_are_dropped():
    """The model must not be able to add repositories that were never fetched."""
    llm_echo = [{"name": "trelix"}, {"name": "does-not-exist"}]
    resolved, seen = resolve_selected_projects(llm_echo, [fetched("trelix")])
    assert [p["name"] for p in resolved] == ["trelix"]
    assert seen == {"trelix"}


def test_duplicate_selections_are_collapsed():
    llm_echo = [{"name": "trelix"}, {"name": "trelix"}]
    resolved, _ = resolve_selected_projects(llm_echo, [fetched("trelix")])
    assert len(resolved) == 1


def test_nameless_selections_are_skipped():
    llm_echo = [{"description": "no name"}, {"name": ""}]
    resolved, seen = resolve_selected_projects(llm_echo, [fetched("trelix")])
    assert resolved == [] and seen == set()


def test_selection_order_is_the_models_ranking():
    """The model's ordering is a genuine judgement and must be preserved."""
    llm_echo = [{"name": "b"}, {"name": "a"}]
    resolved, _ = resolve_selected_projects(llm_echo, [fetched("a"), fetched("b")])
    assert [p["name"] for p in resolved] == ["b", "a"]


def test_resolution_does_not_mutate_the_fetched_records():
    source = fetched("trelix")
    resolve_selected_projects(
        [{"name": "trelix", "reason_for_project_selection": "x"}], [source]
    )
    assert "reason_for_project_selection" not in source
