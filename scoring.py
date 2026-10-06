"""Shared scoring arithmetic for evaluations and role rubrics."""


def compute_totals(evaluation, role, cap=True):
    """Return (total_score, max_score) for an evaluation under a role rubric.

    Mirrors the printed report: category scores are capped at their max, bonus
    points are added, deductions subtracted, and (unless ``cap=False``) the
    total is capped at ``max_score + role.bonus_max``.

    This is the single source of truth for the arithmetic; the report
    (``score.print_evaluation_results``), the rewrite delta, and the CSV row
    must all call it instead of re-implementing the math.
    """
    total_score = 0
    max_score = 0

    if hasattr(evaluation, "scores") and evaluation.scores:
        for category_data in evaluation.scores.model_dump().values():
            total_score += min(category_data["score"], category_data["max"])
            max_score += category_data["max"]

    if hasattr(evaluation, "bonus_points") and evaluation.bonus_points:
        total_score += evaluation.bonus_points.total

    if hasattr(evaluation, "deductions") and evaluation.deductions:
        total_score -= evaluation.deductions.total

    if cap:
        max_possible_score = max_score + role.bonus_max
        total_score = min(total_score, max_possible_score)

    return total_score, max_score
