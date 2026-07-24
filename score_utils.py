"""Shared score-aggregation helpers.

This is the single source of truth for turning an ``EvaluationData`` into a
final numeric score. Both the CLI (``score.py``) and the evaluation framework
(``evals/``) use it, so the benchmark measures exactly the number users see.

Kept dependency-light (only ``models``) so it imports without pulling PyMuPDF,
ollama, or the network.
"""

from dataclasses import dataclass
from typing import Dict

from models import EvaluationData

# Category caps, mirroring the scoring criteria in
# prompts/templates/resume_evaluation_criteria.jinja.
CATEGORY_MAXES: Dict[str, int] = {
    "open_source": 35,
    "self_projects": 30,
    "production": 25,
    "technical_skills": 10,
}

# Mirrors evaluator.MAX_BONUS_POINTS and evaluator.MAX_FINAL_SCORE.
MAX_BONUS = 20
MAX_FINAL_SCORE = 120  # 100 category points + 20 bonus


@dataclass
class ScoreAggregate:
    """The aggregated view of an evaluation."""

    per_category: Dict[str, float]  # capped category scores
    category_total: float  # sum of capped category scores (<= 100)
    category_max: int  # sum of category maxima (== 100)
    bonus: float
    deductions: float
    total: float  # category_total + bonus - deductions, capped


def aggregate_scores(evaluation: EvaluationData) -> ScoreAggregate:
    """Aggregate an ``EvaluationData`` into capped per-category scores and a total.

    Each category score is capped at the category's declared ``max`` (an LLM may
    return an out-of-bounds value). The final total is
    ``sum(capped categories) + bonus - deductions`` capped at ``MAX_FINAL_SCORE``.
    """
    per_category: Dict[str, float] = {}
    category_total = 0.0
    category_max = 0

    for name, data in evaluation.scores.model_dump().items():
        capped = min(data["score"], data["max"])
        per_category[name] = capped
        category_total += capped
        category_max += data["max"]

    bonus = evaluation.bonus_points.total if evaluation.bonus_points else 0.0
    deductions = evaluation.deductions.total if evaluation.deductions else 0.0

    total = category_total + bonus - deductions
    if total > MAX_FINAL_SCORE:
        total = MAX_FINAL_SCORE

    return ScoreAggregate(
        per_category=per_category,
        category_total=category_total,
        category_max=category_max,
        bonus=bonus,
        deductions=deductions,
        total=total,
    )
