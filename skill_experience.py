"""
Deterministic years-of-experience-per-skill estimation, derived from work
history date ranges. Stdlib only (datetime/re) -- no new dependencies.
Purely informational: the underlying date strings are LLM-extracted free
text of uncertain accuracy, so these figures never influence coverage_score
or the skills_match gate.
"""

import logging
from datetime import date
from typing import List, Optional, Tuple

from keyword_matching import keyword_found, normalize_text
from models import SkillExperience, Work

logger = logging.getLogger(__name__)

ONGOING_KEYWORDS = {"present", "current", "now", "ongoing", "till date", "to date"}

_MONTH_FORMATS = ["%Y-%m-%d", "%Y-%m", "%Y", "%b %Y", "%B %Y"]


def parse_resume_date(value: Optional[str], *, is_end: bool = False) -> Optional[date]:
    from datetime import datetime

    if value is None or not value.strip():
        return date.today() if is_end else None

    normalized = value.strip().casefold()
    if normalized in ONGOING_KEYWORDS:
        return date.today() if is_end else None

    for fmt in _MONTH_FORMATS:
        try:
            parsed = datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue

        if fmt == "%Y":
            return date(parsed.year, 12, 31) if is_end else date(parsed.year, 1, 1)
        if fmt == "%Y-%m-%d":
            return date(parsed.year, parsed.month, parsed.day)
        return date(parsed.year, parsed.month, 1)

    return None


def merge_intervals(intervals: List[Tuple[date, date]]) -> List[Tuple[date, date]]:
    if not intervals:
        return []

    sorted_intervals = sorted(intervals, key=lambda interval: interval[0])
    merged = [sorted_intervals[0]]
    for start, end in sorted_intervals[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def _work_interval(work_item: Work) -> Optional[Tuple[date, date]]:
    start = parse_resume_date(work_item.startDate, is_end=False)
    end = parse_resume_date(work_item.endDate, is_end=True)
    if start is None or end is None:
        return None
    end = min(end, date.today())
    if end < start:
        return None
    return start, end


def _work_corpus(work_item: Work) -> str:
    parts = [work_item.position, work_item.summary]
    if work_item.highlights:
        parts.extend(work_item.highlights)
    return normalize_text("\n".join(part for part in parts if part))


def _years_between(start: date, end: date) -> float:
    return round((end - start).days / 365.25, 1)


def compute_skill_experience(required_skills: List[str], work: Optional[List[Work]]) -> List[SkillExperience]:
    if not work:
        return [SkillExperience(skill=skill, years=0.0, evidence=[]) for skill in required_skills]

    results = []
    for skill in required_skills:
        intervals = []
        evidence = []
        for work_item in work:
            if not keyword_found(skill, _work_corpus(work_item)):
                continue
            interval = _work_interval(work_item)
            if interval is None:
                continue
            intervals.append(interval)
            evidence.append(f"{work_item.position or 'Unknown role'} ({work_item.startDate} - {work_item.endDate})")

        merged = merge_intervals(intervals)
        years = round(sum(_years_between(start, end) for start, end in merged), 1)
        results.append(SkillExperience(skill=skill, years=years, evidence=evidence))

    return results


def compute_total_experience_years(work: Optional[List[Work]]) -> Optional[float]:
    if not work:
        return None

    intervals = [interval for interval in (_work_interval(work_item) for work_item in work) if interval is not None]
    if not intervals:
        return None

    merged = merge_intervals(intervals)
    return round(sum(_years_between(start, end) for start, end in merged), 1)
