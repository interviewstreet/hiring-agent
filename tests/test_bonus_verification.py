import json, pathlib, sys

root = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(root), str(root / "benchmark")]
import pytest
import bonus_verifier
from bonus_verifier import verify_claim
from evaluator import ResumeEvaluator
from models import build_evaluation_model
from roles import load_role

role = load_role("software_engineering_intern")
model = build_evaluation_model(role)


def payload(**awarded):
    items = {r["key"]: {"points": 0, "evidence": "none"} for r in role.bonus_rules}
    items["orchestrate"]["rank"] = None
    for key, value in awarded.items():
        items[key].update(value)
    cat = {"score": 1, "max": 1, "evidence": "e"}
    scores = {c.key: {**cat, "max": c.max} for c in role.categories}
    return {
        "scores": scores,
        "bonus_points": {"items": items},
        "deductions": {"total": 0, "reasons": "none"},
        "key_strengths": ["a"],
        "areas_for_improvement": ["b"],
    }


def run(text, data):
    ev = ResumeEvaluator.__new__(ResumeEvaluator)
    ResumeEvaluator.__init__.__globals__["initialize_llm_provider"] = lambda name: None
    ev.__init__(role, model, model_name="test")
    ev.provider = type(
        "P", (), {"chat": lambda self, **k: {"message": {"content": json.dumps(data)}}}
    )()
    return ev, ev.evaluate_resume(text)


def test_invented_claim_loses_only_its_own_points():
    data = payload(
        gsoc={"points": 5, "evidence": "GSoC"},
        linkedin={"points": 1, "evidence": "url"},
    )
    _, result = run("Built a todo app.", data)
    assert result.bonus_points.items.gsoc.points == 0
    assert result.bonus_points.total == 1


def test_supported_claim_keeps_points():
    data = payload(gsoc={"points": 5, "evidence": "GSoC"})
    _, result = run("Google Summer of Code 2024 contributor at CNCF.", data)
    assert result.bonus_points.total == 5


def test_uncertain_claim_keeps_points_and_is_flagged():
    data = payload(gsoc={"points": 5, "evidence": "GSoC"})
    ev, result = run("Applied to GSoC 2025.", data)
    assert result.bonus_points.total == 5
    assert ev.bonus_verdicts[0].action == "review"
    assert "review" in result.bonus_points.items.gsoc.evidence


def test_resume_rank_replaces_wrong_model_rank():
    data = payload(orchestrate={"points": 4, "rank": 31, "evidence": "rank"})
    _, result = run("HackerRank Orchestrate rank 310.", data)
    assert result.bonus_points.total == 1


def test_student_club_founder_is_not_auto_kept():
    assert (
        verify_claim(
            "founder", "Founder and President, Coding Society, Amrita University."
        ).action
        == "review"
    )


@pytest.mark.parametrize(
    "text",
    [
        "Gooogle Summer of Code 2024 developer at Fedora.",
        "Google SoC 2023 student at QEMU.",
    ],
)
def test_near_wording_is_not_removed(text):
    assert verify_claim("gsoc", text).action != "remove"


def test_runs_without_language_model(monkeypatch):
    monkeypatch.setattr(bonus_verifier, "NLP", None)
    assert verify_claim("gsoc", "Built a todo app.").action == "remove"
    assert verify_claim("gsoc", "Applied to GSoC 2025.").action == "review"


@pytest.mark.parametrize(
    "text, rank, points",
    [
        ("HackerRank Orchestrate 2026 Rank #8.", 8, 4),
        ("Secured rank #312 at HackerRank Orchestrate June 2026.", 312, 1),
        ("HackerRank Orchestrate, position 45 on the leaderboard.", 45, 4),
        ("Ranked 199th at HackerRank Orchestrate.", 199, 3),
        ("LeetCode Weekly Contest rank 87.", None, 0),
        (
            "Codeforces Global Round rank 42; HackerRank Orchestrate participant.",
            None,
            0,
        ),
        (
            "Rank 30 at ICPC regionals, and later joined HackerRank Orchestrate.",
            None,
            0,
        ),
        ("GSSoC'23 contributor, ranked in top 100.", None, 0),
        ("HackerRank Orchestrate rank 950.", None, 0),
    ],
)
def test_mismatched_rank_never_crashes_and_uses_resume_rank(text, rank, points):
    data = payload(orchestrate={"points": 1, "rank": 30, "evidence": "rank"})
    _, result = run(text, data)
    item = result.bonus_points.items.orchestrate
    assert (item.rank, item.points) == (rank, points)


def test_missed_claim_is_recovered_at_lowest_points():
    _, result = run("GSSoC 2024 contributor with 12 merged pull requests.", payload())
    assert result.bonus_points.items.girl_script.points == 3


def test_personal_blog_founder_is_not_auto_kept():
    assert (
        verify_claim("founder", "Founder of a personal blog about Rust.").action
        == "review"
    )


@pytest.mark.parametrize(
    "text",
    [
        "Waitlisted for Google Summer of Code 2023.",
        "Rejected from GSoC 2024 mentor selection.",
    ],
)
def test_failed_applications_are_not_grade_a(text):
    assert verify_claim("gsoc", text).grade != "A"
