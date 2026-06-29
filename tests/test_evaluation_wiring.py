"""The evaluation orchestration in score._evaluate_resume must feed the
evaluator REDACTED text when the config flag is on, and raw text when it is
off. We capture the text handed to the evaluator via a fake provider, so no
LLM is involved.
"""

import score
from models import (
    JSONResume,
    Basics,
    Location,
    EvaluationData,
    Scores,
    CategoryScore,
    BonusPoints,
    Deductions,
)


def _dummy_evaluation() -> EvaluationData:
    cat = CategoryScore(score=1, max=10, evidence="x")
    return EvaluationData(
        scores=Scores(
            open_source=CategoryScore(score=1, max=35, evidence="x"),
            self_projects=CategoryScore(score=1, max=30, evidence="x"),
            production=CategoryScore(score=1, max=25, evidence="x"),
            technical_skills=cat,
        ),
        bonus_points=BonusPoints(total=0, breakdown="none"),
        deductions=Deductions(total=0, reasons="none"),
        key_strengths=["s"],
        areas_for_improvement=["a"],
    )


class _CapturingEvaluator:
    """Stand-in for ResumeEvaluator that records the text it is asked to score."""

    captured_text = None

    def __init__(self, model_name=None, model_params=None):
        pass

    def evaluate_resume(self, resume_text):
        _CapturingEvaluator.captured_text = resume_text
        return _dummy_evaluation()


def _resume_with_identity() -> JSONResume:
    return JSONResume(
        basics=Basics(
            name="Jane Q. Candidate",
            email="jane@example.com",
            location=Location(city="Austin", region="Texas"),
        )
    )


def test_evaluation_redacts_identity_when_flag_on(monkeypatch):
    monkeypatch.setattr(score, "ResumeEvaluator", _CapturingEvaluator)
    monkeypatch.setattr(score, "REDACT_PII_FOR_EVALUATION", True)
    _CapturingEvaluator.captured_text = None

    score._evaluate_resume(_resume_with_identity())

    assert _CapturingEvaluator.captured_text is not None
    assert "Jane Q. Candidate" not in _CapturingEvaluator.captured_text
    assert "Austin" not in _CapturingEvaluator.captured_text


def test_evaluation_keeps_identity_when_flag_off(monkeypatch):
    monkeypatch.setattr(score, "ResumeEvaluator", _CapturingEvaluator)
    monkeypatch.setattr(score, "REDACT_PII_FOR_EVALUATION", False)
    _CapturingEvaluator.captured_text = None

    score._evaluate_resume(_resume_with_identity())

    assert "Jane Q. Candidate" in _CapturingEvaluator.captured_text
