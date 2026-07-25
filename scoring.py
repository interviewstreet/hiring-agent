"""Deterministic score arithmetic used by the resume evaluation CLI."""

from typing import Dict, Tuple

from models import EvaluationData

MAX_BONUS_POINTS = 20


def calculate_total_score(
    evaluation: EvaluationData,
) -> Tuple[float, int, Dict[str, float], bool]:
    """Return total score, category maximum, capped category scores, and cap status.

    LLM output is validated by Pydantic, but category scores can still be above
    their declared maximum. Keeping the cap arithmetic in one pure helper makes
    the CLI behavior deterministic and easy to regression-test.
    """

    capped_scores: Dict[str, float] = {}
    max_score = 0
    total_score = 0.0

    for category_name, category_data in evaluation.scores.model_dump().items():
        capped_score = min(category_data["score"], category_data["max"])
        capped_scores[category_name] = capped_score
        total_score += capped_score
        max_score += category_data["max"]

    total_score += evaluation.bonus_points.total
    total_score -= evaluation.deductions.total

    max_possible_score = max_score + MAX_BONUS_POINTS
    capped_at_maximum = total_score > max_possible_score
    if capped_at_maximum:
        total_score = float(max_possible_score)

    return total_score, max_score, capped_scores, capped_at_maximum
