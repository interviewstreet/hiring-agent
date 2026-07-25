import os
import sys
import json
import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Fix for Windows Console Unicode errors
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Fix for Python 3.14 Protobuf TypeError
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

from pdf import PDFHandler
from github import fetch_and_display_github_info
from blog import discover_blog_urls, fetch_blog_metadata
from pdf_integrity import scan_pdf_integrity
from writing_quality import analyze_writing_quality
from models import JSONResume, PdfIntegrityReport, WritingQualityReport
from evaluator import ResumeEvaluator
from score_validation import ValidatedEvaluation, BASE_CATEGORY_MAX
from prompt import DEFAULT_MODEL, MODEL_PARAMETERS
from transform import (
    transform_evaluation_response,
    convert_json_resume_to_text,
    convert_github_data_to_text,
    convert_blog_data_to_text,
)
from config import (
    DEVELOPMENT_MODE,
    ENABLE_PDF_INTEGRITY,
    BLOCK_ON_PDF_INTEGRITY_FAIL,
    ENSEMBLE_RUNS,
    ENABLE_WRITING_QUALITY,
    WRITING_QUALITY_USE_LLM,
    ENABLE_BLOG_ENRICHMENT,
    ENABLE_BLOG_LLM_SCORING,
    ENABLE_WEB_REPORT,
)
from web_report import generate_web_report

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)5s - %(lineno)5d - %(funcName)33s - %(levelname)5s - %(message)s",
)


@dataclass
class ScoreResult:
    pdf_path: str
    resume_data: JSONResume
    github_data: dict
    blog_data: dict
    validated: ValidatedEvaluation
    pdf_integrity: Optional[PdfIntegrityReport] = None
    writing_quality: Optional[WritingQualityReport] = None


def print_pdf_integrity_report(report: PdfIntegrityReport):
    print("\n🔒 PDF INTEGRITY CHECK")
    print("-" * 60)
    if not report.issues:
        print("No suspicious content detected.")
        return

    for issue in report.issues:
        print(
            f"  [{issue.severity}] {issue.issue_type} (page {issue.page}): {issue.snippet}"
        )
    print(
        f"Raw chars: {report.raw_char_count}, visible chars: {report.visible_char_count}"
    )
    if not report.passed:
        print("⚠️  Critical integrity issues detected.")


def print_writing_quality_results(report: WritingQualityReport):
    print("\n📝 WRITING QUALITY REVIEW")
    print("-" * 60)

    if report.spelling_issues:
        print(f"Spelling ({len(report.spelling_issues)} issues):")
        for index, issue in enumerate(report.spelling_issues, 1):
            suggestion = issue.suggestion or "?"
            print(f"  {index}. \"{issue.word}\" → \"{suggestion}\"  (in: {issue.context})")
    else:
        print("Spelling: no issues detected.")

    if report.grammar_issues:
        print("\nGrammar (LLM):")
        for index, issue in enumerate(report.grammar_issues, 1):
            print(f"  {index}. {issue}")

    if report.clarity_suggestions:
        print("\nClarity:")
        for index, suggestion in enumerate(report.clarity_suggestions, 1):
            print(f"  {index}. {suggestion}")


def print_evaluation_results(
    validated: ValidatedEvaluation, candidate_name: str = "Candidate"
):
    evaluation = validated.evaluation
    print("\n" + "=" * 80)
    print(f"📊 RESUME EVALUATION RESULTS FOR: {candidate_name}")
    print("=" * 80)

    if not evaluation:
        print("❌ No evaluation data available")
        return

    if validated.adjustments:
        print("\n⚙️  SCORE ADJUSTMENTS:")
        for adjustment in validated.adjustments:
            print(f"  - {adjustment}")

    print(
        f"\n🎯 CATEGORY TOTAL: {validated.category_total:.1f}/{BASE_CATEGORY_MAX}"
    )
    print(f"🎯 FINAL SCORE: {validated.final_score:.1f}/{BASE_CATEGORY_MAX}")

    if validated.confidence:
        confidence = validated.confidence
        if confidence.runs > 1:
            print(
                f"📊 CONFIDENCE: {confidence.mean_score:.1f} ± {confidence.std_dev:.1f} "
                f"({confidence.confidence_level})"
            )
        else:
            print(f"📊 CONFIDENCE: {confidence.confidence_level}")
        if confidence.unstable_categories:
            print(
                f"   Unstable categories: {', '.join(confidence.unstable_categories)}"
            )

    print("\n📈 DETAILED SCORES:")
    print("-" * 60)

    category_labels = {
        "open_source": "🌐 Open Source",
        "self_projects": "🚀 Self Projects",
        "production": "🏢 Production Experience",
        "technical_skills": "💻 Technical Skills",
    }
    for key, label in category_labels.items():
        category = getattr(evaluation.scores, key)
        capped = min(category.score, category.max)
        print(f"{label:24} {capped}/{category.max}")
        print(f"   Evidence: {category.evidence}")
        print()

    if evaluation.bonus_points:
        print(f"⭐ BONUS POINTS: {evaluation.bonus_points.total}")
        print("-" * 30)
        print(f"   {evaluation.bonus_points.breakdown}")

    if evaluation.deductions and evaluation.deductions.total > 0:
        print(f"\n⚠️  DEDUCTIONS: -{evaluation.deductions.total}")
        print("-" * 30)
        print(f"   {evaluation.deductions.reasons}")

    if evaluation.key_strengths:
        print("\n✅ KEY STRENGTHS:")
        print("-" * 30)
        for index, strength in enumerate(evaluation.key_strengths, 1):
            print(f"  {index}. {strength}")

    if evaluation.areas_for_improvement:
        print("\n🔧 AREAS FOR IMPROVEMENT:")
        print("-" * 30)
        for index, area in enumerate(evaluation.areas_for_improvement, 1):
            print(f"  {index}. {area}")

    print("\n" + "=" * 80)


def is_valid_resume_data(resume_data: JSONResume) -> bool:
    if not resume_data:
        return False
    core_sections = [
        resume_data.basics,
        resume_data.work,
        resume_data.education,
        resume_data.skills,
        resume_data.projects,
    ]
    return any(section is not None for section in core_sections)


def find_profile(profiles, network):
    if not profiles:
        return None
    return next(
        (p for p in profiles if p.network and p.network.lower() == network.lower()),
        None,
    )


def _cache_path(prefix: str, pdf_path: str) -> str:
    basename = os.path.basename(pdf_path).replace(".pdf", "")
    return f"cache/{prefix}_{basename}.json"


def _evaluate_resume(
    resume_data: JSONResume,
    github_data: dict | None = None,
    blog_data: dict | None = None,
) -> ValidatedEvaluation:
    model_params = MODEL_PARAMETERS.get(DEFAULT_MODEL)
    evaluator = ResumeEvaluator(model_name=DEFAULT_MODEL, model_params=model_params)

    resume_text = convert_json_resume_to_text(resume_data)
    if github_data:
        resume_text += convert_github_data_to_text(github_data)
    if blog_data:
        resume_text += convert_blog_data_to_text(blog_data)

    return evaluator.evaluate_resume_validated(resume_text, ensemble_runs=ENSEMBLE_RUNS)


def score_resume(pdf_path: str, *, write_csv: bool | None = None) -> Optional[ScoreResult]:
    """Run the full scoring pipeline for a single PDF."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"File '{pdf_path}' does not exist.")

    pdf_integrity = None
    if ENABLE_PDF_INTEGRITY:
        pdf_integrity = scan_pdf_integrity(pdf_path)
        print_pdf_integrity_report(pdf_integrity)
        if BLOCK_ON_PDF_INTEGRITY_FAIL and pdf_integrity and not pdf_integrity.passed:
            print("❌ Aborting: PDF integrity check failed (BLOCK_ON_PDF_INTEGRITY_FAIL=true).")
            return None

    cache_filename = _cache_path("resumecache", pdf_path)
    github_cache_filename = _cache_path("githubcache", pdf_path)
    blog_cache_filename = _cache_path("blogcache", pdf_path)

    resume_data = None
    cache_loaded = False
    pdf_handler = PDFHandler()

    if DEVELOPMENT_MODE and os.path.exists(cache_filename):
        print(f"Loading cached data from {cache_filename}")
        try:
            cached_data = json.loads(Path(cache_filename).read_text(encoding="utf-8"))
            loaded_resume = JSONResume(**cached_data)
            if not is_valid_resume_data(loaded_resume):
                raise ValueError("Cached resume data contains no core content")
            resume_data = loaded_resume
            cache_loaded = True
        except Exception as exc:
            print(f"⚠️ Warning: Invalid cache file {cache_filename}: {exc}")
            print("Ignoring cache and reprocessing PDF...")
            try:
                os.remove(cache_filename)
            except OSError as delete_err:
                print(f"Failed to delete invalid cache file {cache_filename}: {delete_err}")

    raw_text = pdf_handler.extract_text_from_pdf(pdf_path)

    writing_quality = None
    if ENABLE_WRITING_QUALITY and raw_text:
        if not cache_loaded:
            resume_data = pdf_handler.extract_json_from_pdf(pdf_path)
            if resume_data is None:
                return None
        writing_quality = analyze_writing_quality(
            raw_text,
            resume_data,
            use_llm=WRITING_QUALITY_USE_LLM,
        )
        print_writing_quality_results(writing_quality)

    if not cache_loaded:
        if resume_data is None:
            resume_data = pdf_handler.extract_json_from_pdf(pdf_path)
        if resume_data is None:
            return None

        if DEVELOPMENT_MODE and is_valid_resume_data(resume_data):
            os.makedirs(os.path.dirname(cache_filename), exist_ok=True)
            Path(cache_filename).write_text(
                json.dumps(resume_data.model_dump(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    github_data = {}
    github_cache_loaded = False
    if DEVELOPMENT_MODE and os.path.exists(github_cache_filename):
        print(f"Loading cached data from {github_cache_filename}")
        try:
            loaded_github = json.loads(
                Path(github_cache_filename).read_text(encoding="utf-8")
            )
            if (
                not isinstance(loaded_github, dict)
                or not loaded_github
                or "profile" not in loaded_github
            ):
                raise ValueError("Cached GitHub data is invalid or empty")
            github_data = loaded_github
            github_cache_loaded = True
        except Exception as exc:
            print(f"⚠️ Warning: Invalid GitHub cache file {github_cache_filename}: {exc}")
            try:
                os.remove(github_cache_filename)
            except OSError:
                pass

    if not github_cache_loaded:
        profiles = []
        if resume_data and resume_data.basics:
            profiles = resume_data.basics.profiles or []
        github_profile = find_profile(profiles, "Github")

        if github_profile:
            print(
                "Fetching GitHub data"
                + (f" and caching to {github_cache_filename}" if DEVELOPMENT_MODE else "")
            )
            github_data = fetch_and_display_github_info(github_profile.url) or {}
            if (
                DEVELOPMENT_MODE
                and github_data
                and isinstance(github_data, dict)
                and "profile" in github_data
            ):
                os.makedirs(os.path.dirname(github_cache_filename), exist_ok=True)
                Path(github_cache_filename).write_text(
                    json.dumps(github_data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

    blog_data = {}
    if ENABLE_BLOG_ENRICHMENT:
        if DEVELOPMENT_MODE and os.path.exists(blog_cache_filename):
            try:
                blog_data = json.loads(
                    Path(blog_cache_filename).read_text(encoding="utf-8")
                )
            except Exception:
                blog_data = {}

        if not blog_data:
            blog_urls = discover_blog_urls(resume_data, github_data)
            if blog_urls:
                print(f"Fetching blog metadata for {len(blog_urls)} URL(s)")
            blog_data = fetch_blog_metadata(
                blog_urls,
                use_llm_scoring=ENABLE_BLOG_LLM_SCORING,
            )
            if DEVELOPMENT_MODE and blog_data:
                os.makedirs(os.path.dirname(blog_cache_filename), exist_ok=True)
                Path(blog_cache_filename).write_text(
                    json.dumps(blog_data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

    validated = _evaluate_resume(resume_data, github_data, blog_data or None)

    candidate_name = os.path.basename(pdf_path).replace(".pdf", "")
    if resume_data.basics and resume_data.basics.name:
        candidate_name = resume_data.basics.name

    print_evaluation_results(validated, candidate_name)

    result = ScoreResult(
        pdf_path=pdf_path,
        resume_data=resume_data,
        github_data=github_data,
        blog_data=blog_data,
        validated=validated,
        pdf_integrity=pdf_integrity,
        writing_quality=writing_quality,
    )

    should_write_csv = DEVELOPMENT_MODE if write_csv is None else write_csv
    if should_write_csv:
        csv_row = transform_evaluation_response(
            file_name=os.path.basename(pdf_path),
            evaluation=validated.evaluation,
            validated=validated,
            resume_data=resume_data,
            github_data=github_data,
            writing_quality=writing_quality,
            blog_data=blog_data or None,
            pdf_integrity=pdf_integrity,
        )
        csv_path = "resume_evaluations.csv"
        file_exists = os.path.exists(csv_path)
        with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=list(csv_row.keys()))
            if not file_exists:
                writer.writeheader()
            writer.writerow(csv_row)

    if ENABLE_WEB_REPORT:
        report_path = generate_web_report(result)
        print(f"\n📄 Web report saved: {report_path.resolve()}")
        print(f"   Open in browser: file:///{report_path.resolve().as_posix()}")

    return result


def main(pdf_path: str) -> Optional[ScoreResult]:
    return score_resume(pdf_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python score.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"Error: File '{pdf_path}' does not exist.")
        sys.exit(1)

    main(pdf_path)
