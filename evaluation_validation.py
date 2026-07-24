"""
Deterministic validation and normalization for LLM evaluation output.

Enforces score policy in code (not prompts only) and grounds bonus claims
against trusted resume / GitHub source text. See issue #273.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from models import EvaluationData, JSONResume

logger = logging.getLogger(__name__)

MAX_BONUS_POINTS = 20
MIN_FINAL_SCORE = -20
MAX_FINAL_SCORE = 120

CATEGORY_CAPS = {
    "open_source": 35,
    "self_projects": 30,
    "production": 25,
    "technical_skills": 10,
}

# production score cannot exceed this when structured resume has no work history
PRODUCTION_CAP_WITHOUT_WORK = 5

# open_source score cannot exceed this without real GitHub enrichment data
OPEN_SOURCE_CAP_WITHOUT_GITHUB = 10

BONUS_CLAIMS = (
    (re.compile(r"google summer of code|\bgsoc\b", re.I), 5, ("google summer of code", "gsoc")),
    (
        re.compile(r"girl\s*script\s*summer\s*of\s*code", re.I),
        3,
        ("girl script summer of code", "girlscript"),
    ),
    (
        re.compile(r"startup\s*(founder|co-?founder)|founder\s*experience", re.I),
        5,
        ("founder", "co-founder", "cofounder"),
    ),
    (re.compile(r"early[- ]stage\s*engineer", re.I), 3, ("early-stage", "early stage")),
    (re.compile(r"portfolio\s*website", re.I), 2, ("portfolio", "github.io")),
    (re.compile(r"linkedin\s*profile", re.I), 1, ("linkedin.com", "linkedin")),
)


def _source_corpus(
    source_text: str,
    resume_data: Optional[JSONResume],
    github_data: Optional[dict],
) -> str:
    parts = [source_text or ""]
    if resume_data:
        from transform import convert_json_resume_to_text

        parts.append(convert_json_resume_to_text(resume_data))
    if github_data:
        from transform import convert_github_data_to_text

        parts.append(convert_github_data_to_text(github_data))
    return "\n".join(parts).lower()


def _has_substantive_work(resume_data: Optional[JSONResume]) -> bool:
    if not resume_data or not resume_data.work:
        return False
    return any(
        (w.name and w.name.strip()) or (w.position and w.position.strip())
        for w in resume_data.work
    )


def _has_github_enrichment(github_data: Optional[dict]) -> bool:
    return bool(
        github_data
        and isinstance(github_data, dict)
        and github_data.get("profile")
        and github_data.get("projects")
    )


def _validate_bonus_points(
    evaluation: EvaluationData, corpus: str
) -> tuple[float, str]:
    breakdown = evaluation.bonus_points.breakdown or ""
    validated_total = 0.0
    notes: list[str] = []

    for pattern, points, source_markers in BONUS_CLAIMS:
        if not pattern.search(breakdown):
            continue
        if any(marker in corpus for marker in source_markers):
            validated_total += points
            notes.append(f"+{points} {pattern.pattern}")
        else:
            notes.append(f"removed unverified bonus ({pattern.pattern})")

    validated_total = min(validated_total, MAX_BONUS_POINTS)
    if validated_total == 0 and breakdown.strip():
        note_text = "; ".join(notes) if notes else "No verified bonus claims in source text"
    else:
        note_text = "; ".join(notes) if notes else breakdown

    return validated_total, note_text


def normalize_evaluation(
    evaluation: EvaluationData,
    *,
    source_text: str = "",
    resume_data: Optional[JSONResume] = None,
    github_data: Optional[dict] = None,
) -> EvaluationData:
    """
    Clamp category scores, validate bonuses, and apply structural caps
    based on trusted resume / GitHub data.
    """
    corpus = _source_corpus(source_text, resume_data, github_data)
    scores = evaluation.scores
    updates = {}

    for field, cap in CATEGORY_CAPS.items():
        category = getattr(scores, field)
        capped_score = min(float(category.score), cap)

        if field == "production" and not _has_substantive_work(resume_data):
            capped_score = min(capped_score, PRODUCTION_CAP_WITHOUT_WORK)

        if field == "open_source" and not _has_github_enrichment(github_data):
            capped_score = min(capped_score, OPEN_SOURCE_CAP_WITHOUT_GITHUB)

        if capped_score < category.score:
            logger.warning(
                "%s score capped from %s to %s",
                field,
                category.score,
                capped_score,
            )

        updates[field] = category.model_copy(
            update={"score": capped_score, "max": cap}
        )

    bonus_total, bonus_breakdown = _validate_bonus_points(evaluation, corpus)

    deductions = min(float(evaluation.deductions.total), MAX_FINAL_SCORE)
    category_sum = sum(getattr(updates[f], "score") for f in CATEGORY_CAPS)
    max_deductions = max(0, category_sum + bonus_total - MIN_FINAL_SCORE)
    deductions = min(deductions, max_deductions)

    return evaluation.model_copy(
        update={
            "scores": scores.model_copy(update=updates),
            "bonus_points": evaluation.bonus_points.model_copy(
                update={"total": bonus_total, "breakdown": bonus_breakdown}
            ),
            "deductions": evaluation.deductions.model_copy(update={"total": deductions}),
        }
    )
