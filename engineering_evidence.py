"""Source validation and formatting helpers for engineering evidence reports."""

import re
from typing import Iterable

from models import (
    EngineeringEvidenceExtraction,
    EngineeringEvidenceObservation,
    EngineeringEvidenceReport,
)


def needs_engineering_evidence_extraction(report) -> bool:
    """Retry missing, failed, or wholly ungrounded reports from cached data."""
    return (
        report is None
        or report.status == "extraction_error"
        or report.rejected_observations > 0
    )


def build_source_passages(source_text: str) -> list[dict]:
    """Split extracted resume text into numbered, exact source lines."""
    passages = []
    offset = 0
    for line_number, line in enumerate(source_text.splitlines(keepends=True), 1):
        content = line.rstrip("\r\n")
        leading = len(content) - len(content.lstrip())
        end_trimmed = len(content.rstrip())
        if leading < end_trimmed:
            start = offset + leading
            end = offset + end_trimmed
            passages.append(
                {
                    "id": len(passages) + 1,
                    "text": source_text[start:end],
                    "start": start,
                    "end": end,
                    "line": line_number,
                }
            )
        offset += len(line)
    return passages


def listed_resume_skills(resume_data) -> list[str]:
    """Return unique skill names explicitly listed in the parsed resume."""
    skills = []
    seen = set()
    for skill in resume_data.skills or []:
        values = [skill.name, *(skill.keywords or [])]
        for value in values:
            if value and value.strip() and value.casefold() not in seen:
                skills.append(value.strip())
                seen.add(value.casefold())
    return skills


def _contains_phrase(text: str, phrase: str) -> bool:
    """Match a phrase without treating short skills as substrings of other words."""
    escaped = re.escape(phrase.strip())
    return bool(re.search(rf"(?<!\w){escaped}(?!\w)", text, flags=re.IGNORECASE))


def validate_engineering_evidence(
    extraction: EngineeringEvidenceExtraction,
    source_text: str,
    declared_skills: Iterable[str],
    source_passages: list[dict] | None = None,
) -> EngineeringEvidenceReport:
    """Resolve source IDs to exact text and keep only listed, grounded skill links."""
    if not source_text.strip():
        return EngineeringEvidenceReport(
            status="extraction_error", error="Resume source text is empty."
        )

    passages = source_passages or build_source_passages(source_text)
    passages_by_id = {passage["id"]: passage for passage in passages}
    skills = list(declared_skills)
    verified = []
    rejected_observations = 0
    rejected_skill_links = 0
    used_source_ids = set()

    for candidate in extraction.observations:
        passage = passages_by_id.get(candidate.source_id)
        if passage is None:
            rejected_observations += 1
            continue
        if candidate.source_id in used_source_ids:
            continue
        used_source_ids.add(candidate.source_id)

        quote = passage["text"]

        accepted_skills = []
        for skill in candidate.skills:
            listed = next(
                (item for item in skills if item.casefold() == skill.casefold()), None
            )
            if listed and _contains_phrase(quote, listed):
                if listed.casefold() not in {
                    value.casefold() for value in accepted_skills
                }:
                    accepted_skills.append(listed)
            else:
                rejected_skill_links += 1

        ownership_phrase = candidate.ownership_phrase
        ownership = candidate.ownership
        if not ownership_phrase or ownership_phrase not in quote:
            ownership = "unspecified"
            ownership_phrase = None

        verified.append(
            EngineeringEvidenceObservation(
                source_quote=quote,
                source_section=candidate.source_section,
                problem=candidate.problem,
                contribution=candidate.contribution,
                technical_approach=candidate.technical_approach,
                verification=candidate.verification,
                outcome=candidate.outcome,
                skills=accepted_skills,
                ownership=ownership,
                ownership_phrase=ownership_phrase,
                source_start=passage["start"],
                source_end=passage["end"],
                line_start=passage["line"],
                line_end=passage["line"],
            )
        )

    supported = {
        skill.casefold() for observation in verified for skill in observation.skills
    }
    skills_with_evidence = [skill for skill in skills if skill.casefold() in supported]
    skills_without_examples = [
        skill for skill in skills if skill.casefold() not in supported
    ]

    return EngineeringEvidenceReport(
        status="complete",
        observations=verified,
        skills_with_evidence=skills_with_evidence,
        skills_without_examples=skills_without_examples,
        rejected_observations=rejected_observations,
        rejected_skill_links=rejected_skill_links,
    )


def format_engineering_evidence_report(report: EngineeringEvidenceReport) -> str:
    """Render a concise, source-grounded report for the CLI."""
    lines = ["\nENGINEERING EVIDENCE", "-" * 36]
    if report.status == "extraction_error":
        lines.append(f"Extraction unavailable: {report.error or 'unknown error'}")
        return "\n".join(lines)

    if not report.observations:
        lines.append(
            "No concrete engineering evidence was found in the extracted text."
        )

    for index, item in enumerate(report.observations, 1):
        lines.append(f"{index}. [{item.source_section}] {item.source_quote}")
        lines.append(f"   Ownership: {item.ownership}")
        if item.problem:
            lines.append(f"   Problem: {item.problem}")
        if item.contribution:
            lines.append(f"   Contribution: {item.contribution}")
        if item.technical_approach:
            lines.append(f"   Approach: {item.technical_approach}")
        if item.verification:
            lines.append(f"   Verification: {item.verification}")
        if item.outcome:
            lines.append(f"   Outcome: {item.outcome}")
        if item.skills:
            lines.append(f"   Listed skills evidenced: {', '.join(item.skills)}")
        lines.append(
            f"   Source: extracted text lines {item.line_start}-{item.line_end}"
        )

    if report.skills_with_evidence:
        lines.append(
            "Skills with described application: "
            + ", ".join(report.skills_with_evidence)
        )
    if report.skills_without_examples:
        lines.append(
            "Listed without a supporting example: "
            + ", ".join(report.skills_without_examples)
        )
    if report.rejected_observations or report.rejected_skill_links:
        lines.append(
            "Review warning: rejected "
            f"{report.rejected_observations} unverified quote(s) and "
            f"{report.rejected_skill_links} unsupported skill link(s)."
        )
    lines.append("Source-linked observations are included as evaluation context.")
    return "\n".join(lines)


def format_engineering_evidence_for_evaluation(
    report: EngineeringEvidenceReport,
) -> str:
    """Provide verified evidence records as supplemental evaluation context."""
    lines = [
        "\n=== SUPPLEMENTAL ENGINEERING EVIDENCE ===",
        "Derived from resume statements; claims are not independently verified.",
    ]
    if report.status == "extraction_error":
        lines.append(
            "Evidence extraction failed; no supplemental records are available."
        )
        return "\n".join(lines)

    if not report.observations:
        lines.append(
            "No observations were extracted. Treat this as insufficient information, "
            "not as evidence that the candidate lacks engineering ability."
        )

    for index, item in enumerate(report.observations, 1):
        lines.append(
            f"Observation {index} [{item.source_section}]: {item.source_quote}"
        )
        lines.append(
            f"Source location: extracted-text lines {item.line_start}-{item.line_end}"
        )
        lines.append(f"Ownership: {item.ownership}")
        for label, value in (
            ("Problem", item.problem),
            ("Contribution", item.contribution),
            ("Technical approach", item.technical_approach),
            ("Verification", item.verification),
            ("Outcome", item.outcome),
        ):
            if value:
                lines.append(f"{label}: {value}")
        if item.skills:
            lines.append(
                f"Listed skills connected to this quote: {', '.join(item.skills)}"
            )

    if report.skills_without_examples:
        lines.append(
            "Listed skills without a matching example in the extracted text: "
            + ", ".join(report.skills_without_examples)
        )
    return "\n".join(lines)
