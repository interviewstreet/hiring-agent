"""Deterministic score normalization and confidence estimation."""

from __future__ import annotations

import statistics
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field

from models import BonusPoints, CategoryScore, Deductions, EvaluationData, Scores

MAX_BONUS_POINTS = 20
MIN_FINAL_SCORE = -20
MAX_FINAL_SCORE = 120
BASE_CATEGORY_MAX = 100

CATEGORY_KEYS = ("open_source", "self_projects", "production", "technical_skills")
UNSTABLE_CATEGORIES = frozenset({"open_source", "self_projects"})
EVIDENCE_MIN_LENGTH = 20


class ScoreConfidence(BaseModel):
    runs: int
    mean_score: float
    std_dev: float
    min_score: float
    max_score: float
    confidence_level: str
    unstable_categories: List[str] = Field(default_factory=list)


class ValidatedEvaluation(BaseModel):
    evaluation: EvaluationData
    category_total: float
    final_score: float
    adjustments: List[str] = Field(default_factory=list)
    confidence: Optional[ScoreConfidence] = None


def _cap_category(category: CategoryScore) -> Tuple[CategoryScore, Optional[str]]:
    capped = min(category.score, category.max)
    if capped < category.score:
        return (
            category.model_copy(update={"score": capped}),
            f"{category.score:.0f}→{capped:.0f} (max {category.max})",
        )
    return category, None


def normalize_evaluation(evaluation: EvaluationData) -> Tuple[EvaluationData, List[str]]:
    """Cap category scores, bonus, and final score bounds; return adjustments."""
    adjustments: List[str] = []
    score_updates = {}

    for key in CATEGORY_KEYS:
        category = getattr(evaluation.scores, key)
        capped_category, adjustment = _cap_category(category)
        score_updates[key] = capped_category
        if adjustment:
            adjustments.append(f"{key} capped {adjustment}")

    bonus_total = evaluation.bonus_points.total
    if bonus_total > MAX_BONUS_POINTS:
        adjustments.append(f"bonus capped {bonus_total:.0f}→{MAX_BONUS_POINTS}")
        bonus_total = MAX_BONUS_POINTS

    deductions_total = max(0.0, evaluation.deductions.total)

    normalized = evaluation.model_copy(
        update={
            "scores": evaluation.scores.model_copy(update=score_updates),
            "bonus_points": BonusPoints(
                total=bonus_total,
                breakdown=evaluation.bonus_points.breakdown,
            ),
            "deductions": Deductions(
                total=deductions_total,
                reasons=evaluation.deductions.reasons,
            ),
        }
    )

    final_before_bounds = compute_final_score(normalized)
    if final_before_bounds > MAX_FINAL_SCORE:
        adjustments.append(
            f"final score capped {final_before_bounds:.1f}→{MAX_FINAL_SCORE}"
        )
    elif final_before_bounds < MIN_FINAL_SCORE:
        adjustments.append(
            f"final score raised {final_before_bounds:.1f}→{MIN_FINAL_SCORE}"
        )

    return normalized, adjustments


def compute_category_total(evaluation: EvaluationData) -> float:
    total = 0.0
    for key in CATEGORY_KEYS:
        category = getattr(evaluation.scores, key)
        total += min(category.score, category.max)
    return total


def compute_final_score(evaluation: EvaluationData) -> float:
    """Single source of truth: categories + bonus − deductions, bounded."""
    total = compute_category_total(evaluation)
    total += min(evaluation.bonus_points.total, MAX_BONUS_POINTS)
    total -= max(0.0, evaluation.deductions.total)
    return max(MIN_FINAL_SCORE, min(MAX_FINAL_SCORE, total))


def heuristic_confidence(
    evaluation: EvaluationData, adjustments: List[str]
) -> ScoreConfidence:
    unstable: List[str] = []
    for key in CATEGORY_KEYS:
        category = getattr(evaluation.scores, key)
        evidence = (category.evidence or "").strip()
        at_boundary = category.score <= 0 or category.score >= category.max
        weak_evidence = len(evidence) < EVIDENCE_MIN_LENGTH
        if key in UNSTABLE_CATEGORIES and (at_boundary or weak_evidence):
            unstable.append(key)

    if adjustments or unstable:
        level = "medium" if not unstable else "low"
    else:
        level = "high"

    final_score = compute_final_score(evaluation)
    return ScoreConfidence(
        runs=1,
        mean_score=final_score,
        std_dev=0.0,
        min_score=final_score,
        max_score=final_score,
        confidence_level=level,
        unstable_categories=unstable,
    )


def ensemble_confidence(final_scores: List[float]) -> ScoreConfidence:
    if not final_scores:
        raise ValueError("final_scores must not be empty")

    if len(final_scores) == 1:
        score = final_scores[0]
        return ScoreConfidence(
            runs=1,
            mean_score=score,
            std_dev=0.0,
            min_score=score,
            max_score=score,
            confidence_level="high",
            unstable_categories=[],
        )

    std_dev = statistics.pstdev(final_scores)
    mean_score = statistics.mean(final_scores)
    if std_dev <= 2:
        level = "high"
    elif std_dev <= 6:
        level = "medium"
    else:
        level = "low"

    return ScoreConfidence(
        runs=len(final_scores),
        mean_score=mean_score,
        std_dev=std_dev,
        min_score=min(final_scores),
        max_score=max(final_scores),
        confidence_level=level,
        unstable_categories=[],
    )


def validate_evaluation(
    evaluation: EvaluationData,
    *,
    confidence: Optional[ScoreConfidence] = None,
) -> ValidatedEvaluation:
    normalized, adjustments = normalize_evaluation(evaluation)
    return ValidatedEvaluation(
        evaluation=normalized,
        category_total=compute_category_total(normalized),
        final_score=compute_final_score(normalized),
        adjustments=adjustments,
        confidence=confidence or heuristic_confidence(normalized, adjustments),
    )
