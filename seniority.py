"""
Deterministic seniority-level detection for job titles. Reuses the
boundary-guarded keyword matcher from keyword_matching.py so tier keywords
like "sr" cannot match inside unrelated tokens.
"""

from typing import List, Optional, Tuple

from keyword_matching import keyword_found, normalize_text
from models import JSONResume, SeniorityAssessment

# Checked highest tier first — first match wins, so "Senior Engineering
# Manager" resolves to the leadership tier, not "senior".
SENIORITY_TIERS: List[Tuple[int, str, List[str]]] = [
    (5, "Lead/Management", ["lead", "manager", "head", "director", "vp", "vice president", "chief", "cto", "ceo", "founder"]),
    (4, "Staff/Principal", ["staff", "principal", "architect", "distinguished", "fellow"]),
    (3, "Senior", ["senior", "sr"]),
    (1, "Junior/Associate", ["junior", "jr", "associate", "entry level", "graduate", "trainee"]),
    (0, "Intern", ["intern", "internship", "co op", "apprentice"]),
]
DEFAULT_TIER: Tuple[int, str] = (2, "Mid (unmarked)")


def detect_seniority(title: Optional[str]) -> Tuple[int, str]:
    if not title or not title.strip():
        return DEFAULT_TIER

    normalized_title = normalize_text(title)
    for level, label, keywords in SENIORITY_TIERS:
        if any(keyword_found(keyword, normalized_title) for keyword in keywords):
            return level, label

    return DEFAULT_TIER


def assess_seniority(job_title: str, resume_data: Optional[JSONResume]) -> Optional[SeniorityAssessment]:
    if resume_data is None or not resume_data.work:
        return None

    positions = [work_item.position for work_item in resume_data.work if work_item.position]
    if not positions:
        return None

    target_level, target_label = detect_seniority(job_title)
    candidate_level, candidate_label = detect_seniority(positions[0])

    levels = [detect_seniority(position) for position in positions]
    highest_level, highest_label = max(levels, key=lambda pair: pair[0])

    return SeniorityAssessment(
        target_level=target_level,
        target_label=target_label,
        candidate_level=candidate_level,
        candidate_label=candidate_label,
        highest_level=highest_level,
        highest_label=highest_label,
        gap=candidate_level - target_level,
    )
