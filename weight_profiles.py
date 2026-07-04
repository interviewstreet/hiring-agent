"""
Named weight profiles for job-description scoring, selectable per job
family instead of a single hardcoded set of weights.
"""

import logging
from typing import Dict, Optional

from keyword_matching import keyword_found, normalize_text

logger = logging.getLogger(__name__)

WEIGHT_PROFILES: Dict[str, Dict[str, float]] = {
    "engineering": {
        "skills_match": 0.30,
        "experience_match": 0.20,
        "semantic_match": 0.15,
        "job_title_alignment": 0.10,
        "education": 0.10,
        "resume_quality": 0.10,
        "missing_critical_requirements": 0.05,
    },
    "sales": {
        "skills_match": 0.15,
        "experience_match": 0.30,
        "semantic_match": 0.15,
        "job_title_alignment": 0.15,
        "education": 0.05,
        "resume_quality": 0.15,
        "missing_critical_requirements": 0.05,
    },
    "design": {
        "skills_match": 0.25,
        "experience_match": 0.20,
        "semantic_match": 0.15,
        "job_title_alignment": 0.10,
        "education": 0.05,
        "resume_quality": 0.20,
        "missing_critical_requirements": 0.05,
    },
}
DEFAULT_PROFILE = "engineering"

for _profile_name, _weights in WEIGHT_PROFILES.items():
    assert abs(sum(_weights.values()) - 1.0) < 1e-6, f"Weight profile '{_profile_name}' does not sum to 1.0"

_SALES_TITLE_KEYWORDS = ["sales", "account executive", "account manager", "business development", "sdr", "bdr"]
_DESIGN_TITLE_KEYWORDS = ["designer", "design", "ux", "ui", "product design"]
_SALES_INDUSTRY_KEYWORDS = ["sales", "retail"]
_DESIGN_INDUSTRY_KEYWORDS = ["design", "creative", "advertising"]


def get_profile(name: str) -> Dict[str, float]:
    if name not in WEIGHT_PROFILES:
        logger.warning(f"Unknown weight profile '{name}'. Falling back to '{DEFAULT_PROFILE}'.")
        return WEIGHT_PROFILES[DEFAULT_PROFILE]
    return WEIGHT_PROFILES[name]


def suggest_profile(job_title: str, industry: Optional[str] = None) -> str:
    normalized_title = normalize_text(job_title) if job_title else ""

    if any(keyword_found(keyword, normalized_title) for keyword in _SALES_TITLE_KEYWORDS):
        return "sales"
    if any(keyword_found(keyword, normalized_title) for keyword in _DESIGN_TITLE_KEYWORDS):
        return "design"

    if industry:
        normalized_industry = normalize_text(industry)
        if any(keyword_found(keyword, normalized_industry) for keyword in _SALES_INDUSTRY_KEYWORDS):
            return "sales"
        if any(keyword_found(keyword, normalized_industry) for keyword in _DESIGN_INDUSTRY_KEYWORDS):
            return "design"

    return DEFAULT_PROFILE
