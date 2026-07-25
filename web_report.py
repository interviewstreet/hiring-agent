"""Build a self-contained HTML evaluation report from scoring results."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from config import ENABLE_REPORT_LLM, WEB_REPORT_OUTPUT_DIR
from llm_utils import extract_json_from_response, initialize_llm_provider
from models import JSONResume, ReportCommentary, ReportPointComment
from prompt import DEFAULT_MODEL, MODEL_PARAMETERS
from score_validation import BASE_CATEGORY_MAX, ValidatedEvaluation

logger = logging.getLogger(__name__)

CATEGORY_META = {
    "open_source": {
        "label": "Open Source",
        "icon": "🌐",
        "resume_section": "GitHub & Open Source",
    },
    "self_projects": {
        "label": "Self Projects",
        "icon": "🚀",
        "resume_section": "Projects",
    },
    "production": {
        "label": "Production Experience",
        "icon": "🏢",
        "resume_section": "Work Experience",
    },
    "technical_skills": {
        "label": "Technical Skills",
        "icon": "💻",
        "resume_section": "Skills",
    },
}

GRADE_THRESHOLDS = [
    (90, "A+", "excellent"),
    (80, "A", "excellent"),
    (70, "B+", "good"),
    (60, "B", "good"),
    (50, "C+", "fair"),
    (40, "C", "fair"),
    (30, "D", "needs-work"),
    (0, "F", "needs-work"),
]

METRIC_GLOSSARY = {
    "overall": [
        {
            "name": "Category Total",
            "range": "0–100",
            "formula": "Open Source + Self Projects + Production + Technical Skills",
            "description": "Sum of the four core rubric categories before bonus or deductions.",
        },
        {
            "name": "Final Score",
            "range": "−20 to 120 (displayed vs /100 base)",
            "formula": "Category Total + Bonus − Deductions (capped)",
            "description": "The headline score used for ranking. Bonus can add up to 20 points; deductions subtract from the total.",
        },
        {
            "name": "Letter Grade",
            "range": "A+ through F",
            "formula": "Based on final score as % of 100",
            "description": "A+ ≥90%, A ≥80%, B+ ≥70%, B ≥60%, C+ ≥50%, C ≥40%, D ≥30%, F below 30%.",
        },
        {
            "name": "Confidence",
            "range": "high · medium · low",
            "formula": "Heuristic, or mean ± std dev with ensemble runs",
            "description": "Indicates score stability. Medium/low often means open-source or project judgments varied, or caps were applied. Set ENSEMBLE_RUNS=3 for a numeric band.",
        },
    ],
    "categories": [
        {
            "name": "Open Source",
            "range": "0–35",
            "icon": "🌐",
            "description": "Contributions to other people's projects — not personal repos alone. GSoC, substantial PRs to popular repos score highest. All self-project GitHub activity typically caps at ≤10.",
        },
        {
            "name": "Self Projects",
            "range": "0–30",
            "icon": "🚀",
            "description": "Complexity and impact of personal projects. Tutorial apps (todo, calculator, CRUD) score low; advanced architecture, benchmarks, and real users score high. Missing/broken links reduce score.",
        },
        {
            "name": "Production Experience",
            "range": "0–25",
            "icon": "🏢",
            "description": "Internships and work from the resume work/volunteer sections. Startup founder or early engineer roles get extra weight. Quantified business impact strengthens the score.",
        },
        {
            "name": "Technical Skills",
            "range": "0–10",
            "icon": "💻",
            "description": "Breadth and depth of languages, frameworks, and tools evidenced across skills, projects, and work.",
        },
    ],
    "adjustments": [
        {
            "name": "Bonus Points",
            "range": "0–20 max",
            "description": "Extra credit for GSoC (+5), Girl Script Summer of Code (+3), startup founder (+3–5), early-stage engineer (+2–3), portfolio site (+2), LinkedIn (+1), quality technical blogs (+1–3). Total bonus cannot exceed 20.",
        },
        {
            "name": "Deductions",
            "range": "0+ subtracted",
            "description": "Penalties for tutorial-only project portfolios, broken/missing project links, Hacktoberfest-only OSS, or missing GitHub/portfolio when expected.",
        },
    ],
    "report_sections": [
        {
            "name": "Per-bullet letter grade",
            "range": "A+ – F",
            "description": "In default mode, each resume bullet inherits the letter grade of its rubric section (e.g. all Work bullets use the Production grade). It does not mean that bullet alone scored an A.",
        },
        {
            "name": "Per-bullet X/10 score",
            "range": "0–10",
            "description": "Only shown when ENABLE_REPORT_LLM=true. The LLM assigns an individual 0–10 quality score per bullet. Without LLM commentary, no per-bullet numeric score is shown.",
        },
        {
            "name": "Writing Quality",
            "range": "Advisory only",
            "description": "Spell-check and optional grammar/clarity feedback. Does not change the hiring rubric score.",
        },
        {
            "name": "PDF Integrity",
            "range": "Pass / warnings",
            "description": "Flags hidden or off-page text that could inflate scores. Advisory unless blocking is enabled.",
        },
    ],
    "fairness": [
        "Scores never use name, gender, school, GPA, or location.",
        "Education appears in the report for context but is not a scored category.",
        "GitHub enrichment distinguishes open_source (multi-contributor) vs self_project repos.",
    ],
}


def letter_grade(score: float, max_score: float) -> Dict[str, str]:
    if max_score <= 0:
        return {"grade": "N/A", "tier": "fair"}
    pct = 100 * score / max_score
    for threshold, grade, tier in GRADE_THRESHOLDS:
        if pct >= threshold:
            return {"grade": grade, "tier": tier}
    return {"grade": "F", "tier": "needs-work"}


def _pct(score: float, max_score: float) -> float:
    return round(100 * score / max_score, 1) if max_score else 0.0


def _safe_list(value: Optional[List[str]]) -> List[str]:
    return [item for item in (value or []) if item and item.strip()]


def _match_comment(text: str, llm_comments: List[ReportPointComment]) -> Optional[ReportPointComment]:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    for comment in llm_comments:
        point = re.sub(r"\s+", " ", comment.point_text.strip().lower())
        if point and (point in normalized or normalized in point):
            return comment
        if comment.item_title and comment.item_title.lower() in normalized:
            return comment
    return None


def _fallback_point_comment(
    section_key: str,
    point_text: str,
    evaluation,
    strengths: List[str],
    improvements: List[str],
) -> Dict[str, Any]:
    category = getattr(evaluation.scores, section_key)
    meta = CATEGORY_META[section_key]
    grade_info = letter_grade(category.score, category.max)
    note = category.evidence

    for strength in strengths:
        if any(token in strength.lower() for token in point_text.lower().split()[:3] if len(token) > 4):
            note = strength
            break

    for improvement in improvements:
        if any(token in improvement.lower() for token in point_text.lower().split()[:3] if len(token) > 4):
            note = improvement
            break

    return {
        "point_text": point_text,
        "grade": grade_info["grade"],
        "tier": grade_info["tier"],
        "score": 0,
        "max_score": 0,
        "comment": note,
        "rubric": meta["label"],
    }


def _build_category_cards(validated: ValidatedEvaluation) -> List[Dict[str, Any]]:
    evaluation = validated.evaluation
    cards = []
    for key, meta in CATEGORY_META.items():
        category = getattr(evaluation.scores, key)
        grade_info = letter_grade(category.score, category.max)
        cards.append(
            {
                "key": key,
                "label": meta["label"],
                "icon": meta["icon"],
                "score": min(category.score, category.max),
                "max": category.max,
                "pct": _pct(category.score, category.max),
                "grade": grade_info["grade"],
                "tier": grade_info["tier"],
                "evidence": category.evidence,
            }
        )
    return cards


def _build_resume_sections(
    resume_data: JSONResume,
    validated: ValidatedEvaluation,
    llm_comments: List[ReportPointComment],
) -> List[Dict[str, Any]]:
    evaluation = validated.evaluation
    strengths = evaluation.key_strengths or []
    improvements = evaluation.areas_for_improvement or []
    sections: List[Dict[str, Any]] = []

    if resume_data.work:
        category = evaluation.scores.production
        grade_info = letter_grade(category.score, category.max)
        items = []
        for job in resume_data.work:
            points = _safe_list(job.highlights)
            if job.summary and not points:
                points = [job.summary]
            point_rows = []
            for point in points:
                matched = _match_comment(point, llm_comments)
                if matched:
                    grade = letter_grade(matched.score, matched.max_score)
                    point_rows.append(
                        {
                            "point_text": point,
                            "grade": matched.grade or grade["grade"],
                            "tier": grade["tier"],
                            "score": matched.score,
                            "max_score": matched.max_score,
                            "comment": matched.comment,
                            "rubric": CATEGORY_META["production"]["label"],
                        }
                    )
                else:
                    point_rows.append(
                        _fallback_point_comment(
                            "production", point, evaluation, strengths, improvements
                        )
                    )
            items.append(
                {
                    "title": job.name or "Company",
                    "subtitle": job.position or "",
                    "dates": " – ".join(filter(None, [job.startDate, job.endDate])),
                    "points": point_rows,
                }
            )
        sections.append(
            {
                "title": "Work Experience",
                "category_key": "production",
                "overall_score": min(category.score, category.max),
                "overall_max": category.max,
                "overall_grade": grade_info["grade"],
                "overall_tier": grade_info["tier"],
                "section_comment": category.evidence,
                "entries": items,
            }
        )

    if resume_data.projects:
        category = evaluation.scores.self_projects
        grade_info = letter_grade(category.score, category.max)
        items = []
        for project in resume_data.projects:
            points = _safe_list(project.highlights)
            if project.description:
                points = points or [project.description]
            point_rows = []
            for point in points:
                matched = _match_comment(point, llm_comments)
                if matched:
                    grade = letter_grade(matched.score, matched.max_score)
                    point_rows.append(
                        {
                            "point_text": point,
                            "grade": matched.grade or grade["grade"],
                            "tier": grade["tier"],
                            "score": matched.score,
                            "max_score": matched.max_score,
                            "comment": matched.comment,
                            "rubric": CATEGORY_META["self_projects"]["label"],
                        }
                    )
                else:
                    point_rows.append(
                        _fallback_point_comment(
                            "self_projects", point, evaluation, strengths, improvements
                        )
                    )
            items.append(
                {
                    "title": project.name or "Project",
                    "subtitle": ", ".join(project.technologies or []) or project.url or "",
                    "dates": " – ".join(filter(None, [project.startDate, project.endDate])),
                    "points": point_rows,
                }
            )
        sections.append(
            {
                "title": "Projects",
                "category_key": "self_projects",
                "overall_score": min(category.score, category.max),
                "overall_max": category.max,
                "overall_grade": grade_info["grade"],
                "overall_tier": grade_info["tier"],
                "section_comment": category.evidence,
                "entries": items,
            }
        )

    if resume_data.skills:
        category = evaluation.scores.technical_skills
        grade_info = letter_grade(category.score, category.max)
        items = []
        for skill_group in resume_data.skills:
            keywords = _safe_list(skill_group.keywords)
            if not keywords:
                continue
            chunk_size = 8
            for index in range(0, len(keywords), chunk_size):
                chunk = keywords[index : index + chunk_size]
                point_text = ", ".join(chunk)
                matched = _match_comment(point_text, llm_comments)
                if matched:
                    grade = letter_grade(matched.score, matched.max_score)
                    point_rows = [
                        {
                            "point_text": point_text,
                            "grade": matched.grade or grade["grade"],
                            "tier": grade["tier"],
                            "score": matched.score,
                            "max_score": matched.max_score,
                            "comment": matched.comment,
                            "rubric": CATEGORY_META["technical_skills"]["label"],
                        }
                    ]
                else:
                    point_rows = [
                        _fallback_point_comment(
                            "technical_skills",
                            point_text,
                            evaluation,
                            strengths,
                            improvements,
                        )
                    ]
                items.append(
                    {
                        "title": skill_group.name or "Skills",
                        "subtitle": skill_group.level or "",
                        "dates": "",
                        "points": point_rows,
                    }
                )
        if items:
            sections.append(
                {
                    "title": "Technical Skills",
                    "category_key": "technical_skills",
                    "overall_score": min(category.score, category.max),
                    "overall_max": category.max,
                    "overall_grade": grade_info["grade"],
                    "overall_tier": grade_info["tier"],
                    "section_comment": category.evidence,
                    "entries": items,
                }
            )

    if resume_data.education:
        items = []
        for edu in resume_data.education:
            point_text = " | ".join(
                filter(
                    None,
                    [
                        edu.studyType,
                        edu.area,
                        f"GPA/score: {edu.score}" if edu.score else None,
                    ],
                )
            ) or "Education entry"
            items.append(
                {
                    "title": edu.institution or "Institution",
                    "subtitle": edu.studyType or "",
                    "dates": " – ".join(filter(None, [edu.startDate, edu.endDate])),
                    "points": [
                        {
                            "point_text": point_text,
                            "grade": "—",
                            "tier": "fair",
                            "score": 0,
                            "max_score": 10,
                            "comment": "Education is extracted for context but excluded from scoring per fairness rules.",
                            "rubric": "Informational",
                        }
                    ],
                }
            )
        sections.append(
            {
                "title": "Education",
                "category_key": "education",
                "overall_score": 0,
                "overall_max": 0,
                "overall_grade": "—",
                "overall_tier": "fair",
                "section_comment": "School name and GPA are not used in the hiring rubric.",
                "entries": items,
            }
        )

    if resume_data.awards:
        items = []
        for award in resume_data.awards:
            point_text = award.summary or award.title or "Award"
            items.append(
                {
                    "title": award.title or "Award",
                    "subtitle": award.awarder or "",
                    "dates": award.date or "",
                    "points": [
                        {
                            "point_text": point_text,
                            "grade": "—",
                            "tier": "good",
                            "score": 0,
                            "max_score": 10,
                            "comment": "Awards may support bonus-point reasoning but are not a separate scored category.",
                            "rubric": "Bonus context",
                        }
                    ],
                }
            )
        sections.append(
            {
                "title": "Awards",
                "category_key": "awards",
                "overall_score": validated.evaluation.bonus_points.total,
                "overall_max": 20,
                "overall_grade": letter_grade(
                    validated.evaluation.bonus_points.total, 20
                )["grade"],
                "overall_tier": letter_grade(
                    validated.evaluation.bonus_points.total, 20
                )["tier"],
                "section_comment": validated.evaluation.bonus_points.breakdown,
                "entries": items,
            }
        )

    github_section = _build_github_section(validated, llm_comments, strengths, improvements)
    if github_section:
        sections.insert(0, github_section)

    return sections


def _build_github_section(
    validated: ValidatedEvaluation,
    llm_comments: List[ReportPointComment],
    strengths: List[str],
    improvements: List[str],
) -> Optional[Dict[str, Any]]:
    category = validated.evaluation.scores.open_source
    grade_info = letter_grade(category.score, category.max)
    return {
        "title": "GitHub & Open Source",
        "category_key": "open_source",
        "overall_score": min(category.score, category.max),
        "overall_max": category.max,
        "overall_grade": grade_info["grade"],
        "overall_tier": grade_info["tier"],
        "section_comment": category.evidence,
                "entries": [
            {
                "title": "Open source profile assessment",
                "subtitle": "Based on GitHub enrichment + resume profiles",
                "dates": "",
                "points": [
                    _fallback_point_comment(
                        "open_source",
                        category.evidence,
                        validated.evaluation,
                        strengths,
                        improvements,
                    )
                ],
            }
        ],
    }


def _fetch_llm_commentary(
    resume_data: JSONResume,
    validated: ValidatedEvaluation,
    github_data: dict,
) -> ReportCommentary:
    from prompts.template_manager import TemplateManager

    template_manager = TemplateManager()
    resume_summary = _resume_summary_for_llm(resume_data)
    evaluation_json = validated.evaluation.model_dump_json(indent=2)
    github_summary = json.dumps(github_data or {}, indent=2)[:8000]

    prompt = template_manager.render_template(
        "report_commentary",
        resume_summary=resume_summary,
        evaluation_json=evaluation_json,
        github_summary=github_summary,
    )
    if not prompt:
        return ReportCommentary(summary="", points=[])

    provider = initialize_llm_provider(DEFAULT_MODEL)
    model_params = MODEL_PARAMETERS.get(DEFAULT_MODEL, {"temperature": 0.1, "top_p": 0.9})
    response = provider.chat(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={
            "stream": False,
            "temperature": model_params.get("temperature", 0.1),
            "top_p": model_params.get("top_p", 0.9),
        },
        format=ReportCommentary.model_json_schema(),
    )
    content = extract_json_from_response(response["message"]["content"])
    return ReportCommentary(**json.loads(content))


def _resume_summary_for_llm(resume_data: JSONResume) -> str:
    lines: List[str] = []
    if resume_data.basics and resume_data.basics.name:
        lines.append(f"Name: {resume_data.basics.name}")

    for job in resume_data.work or []:
        lines.append(f"WORK: {job.name} | {job.position}")
        for highlight in _safe_list(job.highlights):
            lines.append(f"  - {highlight}")

    for project in resume_data.projects or []:
        lines.append(f"PROJECT: {project.name}")
        if project.description:
            lines.append(f"  - {project.description}")
        for highlight in _safe_list(project.highlights):
            lines.append(f"  - {highlight}")

    for skill_group in resume_data.skills or []:
        keywords = ", ".join(_safe_list(skill_group.keywords))
        if keywords:
            lines.append(f"SKILLS ({skill_group.name}): {keywords}")

    return "\n".join(lines)[:12000]


def build_report_context(result: Any) -> Dict[str, Any]:
    validated: ValidatedEvaluation = result.validated
    evaluation = validated.evaluation
    final_grade = letter_grade(validated.final_score, BASE_CATEGORY_MAX)

    llm_comments: List[ReportPointComment] = []
    narrative_summary = ""
    if ENABLE_REPORT_LLM:
        try:
            commentary = _fetch_llm_commentary(
                result.resume_data, validated, result.github_data
            )
            llm_comments = commentary.points
            narrative_summary = commentary.summary
        except Exception as exc:
            logger.warning("Report LLM commentary failed: %s", exc)

    confidence = validated.confidence
    writing = result.writing_quality
    integrity = result.pdf_integrity
    blog = result.blog_data or {}

    return {
        "candidate_name": (
            result.resume_data.basics.name
            if result.resume_data.basics and result.resume_data.basics.name
            else Path(result.pdf_path).stem
        ),
        "source_file": Path(result.pdf_path).name,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "final_score": validated.final_score,
        "category_total": validated.category_total,
        "base_max": BASE_CATEGORY_MAX,
        "final_grade": final_grade["grade"],
        "final_tier": final_grade["tier"],
        "confidence": confidence.model_dump() if confidence else None,
        "adjustments": validated.adjustments,
        "categories": _build_category_cards(validated),
        "bonus": {
            "total": evaluation.bonus_points.total,
            "breakdown": evaluation.bonus_points.breakdown,
            "grade": letter_grade(evaluation.bonus_points.total, 20)["grade"],
        },
        "deductions": {
            "total": evaluation.deductions.total,
            "reasons": evaluation.deductions.reasons,
        },
        "strengths": evaluation.key_strengths,
        "improvements": evaluation.areas_for_improvement,
        "resume_sections": _build_resume_sections(
            result.resume_data, validated, llm_comments
        ),
        "writing_quality": {
            "spelling_issues": [
                issue.model_dump() for issue in (writing.spelling_issues if writing else [])
            ],
            "grammar_issues": writing.grammar_issues if writing else [],
            "clarity_suggestions": writing.clarity_suggestions if writing else [],
        },
        "pdf_integrity": integrity.model_dump() if integrity else None,
        "github_summary": {
            "repos": (result.github_data or {}).get("profile", {}).get("public_repos", 0),
            "followers": (result.github_data or {}).get("profile", {}).get("followers", 0),
            "project_count": len((result.github_data or {}).get("projects", [])),
        },
        "blog_summary": {
            "count": blog.get("total_blogs", 0),
            "score": blog.get("blog_score", 0),
            "details": blog.get("blog_details", ""),
        },
        "llm_commentary_enabled": ENABLE_REPORT_LLM,
        "narrative_summary": narrative_summary,
        "metric_glossary": METRIC_GLOSSARY,
    }


def render_report_html(context: Dict[str, Any]) -> str:
    env = Environment(
        loader=FileSystemLoader("prompts/templates"),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("resume_report.html.jinja")
    return template.render(**context)


def generate_web_report(result: Any, output_dir: Optional[str] = None) -> Path:
    """Generate a standalone HTML report and return its path."""
    context = build_report_context(result)
    html = render_report_html(context)

    out_dir = Path(output_dir or WEB_REPORT_OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    slug = re.sub(r"[^\w\-]+", "_", context["candidate_name"]).strip("_") or "resume"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = out_dir / f"{slug}_{timestamp}_report.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path
