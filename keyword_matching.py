"""
Deterministic keyword matching between a job description's extracted
requirements and a candidate's resume. No LLM calls, no external
dependencies beyond the standard library.
"""

import re
import unicodedata
from typing import Callable, Dict, List, Optional

from models import JSONResume, JobDescriptionData, KeywordMatchResult, MustHaveStatus, IndustryMatch

MUST_HAVE_VERIFIABLE_MAX_WORDS = 5
GATE_CAP = 60.0
KNOCKOUT_CAP = 30.0
REQUIRED_WEIGHT = 0.8
PREFERRED_WEIGHT = 0.2

_INDUSTRY_SPLIT = re.compile(r"[,/&]|\band\b", re.IGNORECASE)

_PUNCTUATION_TO_STRIP = re.compile(r"[,;:()\[\]{}'\"!?]")
_SEPARATORS_TO_SPACE = re.compile(r"[-_/]")
_WHITESPACE_RUN = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = _SEPARATORS_TO_SPACE.sub(" ", normalized)
    normalized = _PUNCTUATION_TO_STRIP.sub(" ", normalized)
    normalized = _WHITESPACE_RUN.sub(" ", normalized).strip()
    return normalized


def keyword_found(keyword: str, normalized_corpus: str) -> bool:
    normalized_keyword = normalize_text(keyword)
    if not normalized_keyword:
        return False
    pattern = rf"(?<![a-z0-9+#]){re.escape(normalized_keyword)}(?![a-z0-9+#])"
    return re.search(pattern, normalized_corpus) is not None


def build_match_corpus(resume_text: str, resume_data: Optional[JSONResume] = None) -> str:
    parts = [resume_text]

    if resume_data is not None:
        if resume_data.skills:
            for skill in resume_data.skills:
                if skill.name:
                    parts.append(skill.name)
                if skill.keywords:
                    parts.extend(skill.keywords)

        if resume_data.projects:
            for project in resume_data.projects:
                if project.technologies:
                    parts.extend(project.technologies)
                if project.skills:
                    parts.extend(project.skills)

        if resume_data.work:
            for work_item in resume_data.work:
                if work_item.position:
                    parts.append(work_item.position)

        if resume_data.certificates:
            for certificate in resume_data.certificates:
                if certificate.name:
                    parts.append(certificate.name)

    return normalize_text("\n".join(parts))


def _dedupe_keywords(keywords: List[str]) -> List[str]:
    seen = set()
    deduped = []
    for keyword in keywords:
        normalized = normalize_text(keyword)
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(keyword)
    return deduped


def _must_have_status(qualification: str, normalized_corpus: str) -> MustHaveStatus:
    word_count = len(normalize_text(qualification).split())
    if word_count > MUST_HAVE_VERIFIABLE_MAX_WORDS:
        return MustHaveStatus(qualification=qualification, status="unverifiable")
    status = "found" if keyword_found(qualification, normalized_corpus) else "not_found"
    return MustHaveStatus(qualification=qualification, status=status)


def compute_keyword_match(
    job_data: JobDescriptionData,
    resume_text: str,
    resume_data: Optional[JSONResume] = None,
) -> KeywordMatchResult:
    # Deferred import: skill_experience.py imports keyword_found/normalize_text
    # from this module, so importing it at module scope would be circular.
    from skill_experience import compute_skill_experience, compute_total_experience_years

    normalized_corpus = build_match_corpus(resume_text, resume_data)

    required_skills = _dedupe_keywords(job_data.required_skills or [])
    preferred_skills = _dedupe_keywords(job_data.preferred_skills or [])

    matched_required = [skill for skill in required_skills if keyword_found(skill, normalized_corpus)]
    missing_required = [skill for skill in required_skills if skill not in matched_required]
    matched_preferred = [skill for skill in preferred_skills if keyword_found(skill, normalized_corpus)]
    missing_preferred = [skill for skill in preferred_skills if skill not in matched_preferred]

    must_have_status = [
        _must_have_status(qualification, normalized_corpus)
        for qualification in (job_data.must_have_qualifications or [])
    ]

    if required_skills and preferred_skills:
        required_ratio = len(matched_required) / len(required_skills)
        preferred_ratio = len(matched_preferred) / len(preferred_skills)
        coverage = 100 * (REQUIRED_WEIGHT * required_ratio + PREFERRED_WEIGHT * preferred_ratio)
    elif required_skills:
        coverage = 100 * (len(matched_required) / len(required_skills))
    elif preferred_skills:
        coverage = 100 * (len(matched_preferred) / len(preferred_skills))
    else:
        coverage = 50.0

    gated = any(status.status == "not_found" for status in must_have_status)
    if gated:
        coverage = min(coverage, GATE_CAP)

    work = resume_data.work if resume_data is not None else None

    return KeywordMatchResult(
        matched_required=matched_required,
        missing_required=missing_required,
        matched_preferred=matched_preferred,
        missing_preferred=missing_preferred,
        must_have_status=must_have_status,
        coverage_score=round(coverage, 1),
        gated=gated,
        skill_experience=compute_skill_experience(required_skills, work),
        estimated_total_years=compute_total_experience_years(work),
    )


def apply_knockout_resolutions(
    result: KeywordMatchResult, resolver: Optional[Callable[[str], Optional[bool]]]
) -> KeywordMatchResult:
    if resolver is None:
        return result

    updated_status = []
    knockout_failed = False
    for status in result.must_have_status:
        if status.status != "unverifiable":
            updated_status.append(status)
            continue

        answer = resolver(status.qualification)
        if answer is None:
            updated_status.append(status)
            continue

        updated_status.append(
            MustHaveStatus(qualification=status.qualification, status=status.status, resolved=answer)
        )
        if answer is False:
            knockout_failed = True

    coverage_score = result.coverage_score
    gated = result.gated
    if knockout_failed:
        gated = True
        coverage_score = min(coverage_score, GATE_CAP)

    return result.model_copy(update={
        "must_have_status": updated_status,
        "gated": gated,
        "coverage_score": coverage_score,
        "knockout_failed": knockout_failed,
    })


def build_skills_evidence(result: KeywordMatchResult) -> str:
    total_required = len(result.matched_required) + len(result.missing_required)
    total_preferred = len(result.matched_preferred) + len(result.missing_preferred)

    parts = [
        f"Matched {len(result.matched_required)}/{total_required} required skills"
        + (f" ({', '.join(result.matched_required)})" if result.matched_required else "")
        + "."
    ]
    if result.missing_required:
        parts.append(f"Missing required: {', '.join(result.missing_required)}.")
    if total_preferred:
        parts.append(
            f"Matched {len(result.matched_preferred)}/{total_preferred} preferred skills"
            + (f" ({', '.join(result.matched_preferred)})" if result.matched_preferred else "")
            + "."
        )
    if result.gated:
        parts.append(
            f"Score capped at {GATE_CAP:.0f} because a must-have qualification was not found in the resume."
        )

    return " ".join(parts)


def _work_entry_industry_corpus(work_item) -> str:
    parts = [work_item.name, work_item.summary]
    if work_item.highlights:
        parts.extend(work_item.highlights)
    return normalize_text("\n".join(part for part in parts if part))


def compute_industry_mentions(
    industry: Optional[str], resume_data: Optional[JSONResume]
) -> Optional[IndustryMatch]:
    if not industry or not industry.strip():
        return None

    tokens = [token.strip() for token in _INDUSTRY_SPLIT.split(industry) if token.strip()]
    if not tokens:
        tokens = [industry.strip()]

    if resume_data is None or not resume_data.work:
        return IndustryMatch(industry=industry, mention_count=0, matched_entries=[])

    matched_entries = []
    for work_item in resume_data.work:
        corpus = _work_entry_industry_corpus(work_item)
        if any(keyword_found(token, corpus) for token in tokens):
            label = f"{work_item.name or 'Unknown company'} — {work_item.position or 'Unknown role'}"
            matched_entries.append(label)

    return IndustryMatch(industry=industry, mention_count=len(matched_entries), matched_entries=matched_entries)
