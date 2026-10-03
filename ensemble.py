"""Ensemble scoring: run evaluation multiple times and aggregate for stability."""

import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from collections import Counter


@dataclass
class CategoryStats:
    """Statistical summary for a single scoring category across N runs."""

    scores: List[float]
    max_score: int
    evidence_samples: List[str]

    @property
    def median(self) -> float:
        return statistics.median(self.scores)

    @property
    def mean(self) -> float:
        return statistics.mean(self.scores)

    @property
    def stdev(self) -> float:
        return statistics.stdev(self.scores) if len(self.scores) > 1 else 0.0

    @property
    def min(self) -> float:
        return min(self.scores)

    @property
    def max_val(self) -> float:
        return max(self.scores)

    @property
    def range(self) -> float:
        return self.max_val - self.min

    @property
    def coefficient_of_variation(self) -> float:
        """CV as a percentage. Higher = less stable."""
        if self.mean == 0:
            return 0.0
        return (self.stdev / self.mean) * 100

    @property
    def is_stable(self) -> bool:
        """A category is stable if its range is <= 20% of max_score."""
        return self.range <= (self.max_score * 0.2)


@dataclass
class EnsembleResult:
    """Aggregated result from N evaluation runs."""

    num_runs: int
    category_stats: Dict[str, CategoryStats]
    bonus_scores: List[float]
    deduction_scores: List[float]
    total_scores: List[float]
    all_strengths: List[List[str]]
    all_improvements: List[List[str]]
    individual_evaluations: List[Any]  # Raw evaluation objects

    @property
    def median_total(self) -> float:
        return statistics.median(self.total_scores)

    @property
    def total_stdev(self) -> float:
        return statistics.stdev(self.total_scores) if len(self.total_scores) > 1 else 0.0

    @property
    def total_range(self) -> float:
        return max(self.total_scores) - min(self.total_scores)

    @property
    def is_high_confidence(self) -> bool:
        """High confidence if total score range is <= 15% of max possible."""
        max_possible = max(
            sum(cs.max_score for cs in self.category_stats.values()), 1
        )
        return self.total_range <= (max_possible * 0.15)

    @property
    def confidence_label(self) -> str:
        max_possible = max(
            sum(cs.max_score for cs in self.category_stats.values()), 1
        )
        pct = (self.total_range / max_possible) * 100
        if pct <= 5:
            return "Very High"
        elif pct <= 10:
            return "High"
        elif pct <= 20:
            return "Moderate"
        elif pct <= 30:
            return "Low"
        else:
            return "Very Low"

    @property
    def most_frequent_strengths(self) -> List[str]:
        """Return strengths that appear in majority of runs."""
        all_s = [s for run in self.all_strengths for s in run]
        threshold = self.num_runs / 2
        return [
            s for s, count in Counter(all_s).most_common() if count >= threshold
        ][:5]

    @property
    def most_frequent_improvements(self) -> List[str]:
        """Return improvements that appear in majority of runs."""
        all_i = [i for run in self.all_improvements for i in run]
        threshold = self.num_runs / 2
        return [
            i for i, count in Counter(all_i).most_common() if count >= threshold
        ][:5]


def aggregate_evaluations(evaluations: List[Any], role) -> EnsembleResult:
    """Aggregate N evaluation results into a single EnsembleResult.

    Args:
        evaluations: List of EvaluationData pydantic model instances
        role: Role object with .categories list

    Returns:
        EnsembleResult with statistical summaries
    """
    category_stats = {}
    for category in role.categories:
        scores = []
        evidences = []
        for ev in evaluations:
            cat_score = getattr(ev.scores, category.key, None)
            if cat_score:
                scores.append(min(cat_score.score, category.max))
                evidences.append(cat_score.evidence)
        category_stats[category.key] = CategoryStats(
            scores=scores,
            max_score=category.max,
            evidence_samples=evidences,
        )

    bonus_scores = [ev.bonus_points.total for ev in evaluations]
    deduction_scores = [ev.deductions.total for ev in evaluations]

    total_scores = []
    for ev in evaluations:
        total = 0
        for category in role.categories:
            cat_score = getattr(ev.scores, category.key, None)
            if cat_score:
                total += min(cat_score.score, category.max)
        total += ev.bonus_points.total
        total -= ev.deductions.total
        total_scores.append(total)

    all_strengths = [list(ev.key_strengths) for ev in evaluations]
    all_improvements = [list(ev.areas_for_improvement) for ev in evaluations]

    return EnsembleResult(
        num_runs=len(evaluations),
        category_stats=category_stats,
        bonus_scores=bonus_scores,
        deduction_scores=deduction_scores,
        total_scores=total_scores,
        all_strengths=all_strengths,
        all_improvements=all_improvements,
        individual_evaluations=evaluations,
    )
