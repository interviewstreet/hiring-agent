import os
import sys
import json
import logging
import csv
from pdf import PDFHandler
from github import fetch_and_display_github_info
from models import JSONResume, EvaluationData, JobEvaluationData, ParseabilityResult
from typing import Optional
from evaluator import ResumeEvaluator, JobDescriptionEvaluator
from pathlib import Path
from prompt import DEFAULT_MODEL, MODEL_PARAMETERS
from ats_parseability import scan_pdf_parseability
from weight_profiles import WEIGHT_PROFILES, DEFAULT_PROFILE, suggest_profile
from transform import (
    transform_evaluation_response,
    transform_job_evaluation_response,
    convert_json_resume_to_text,
    convert_github_data_to_text,
    convert_blog_data_to_text,
)
from config import DEVELOPMENT_MODE

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)5s - %(lineno)5d - %(funcName)33s - %(levelname)5s - %(message)s",
)

RESUME_PATH = "resume.pdf"
JOB_DESCRIPTION_PATH = "job_description.txt"


def select_mode() -> int:
    print("\nChoose scoring mode:")
    print("  1. HackerRank Intern (original)")
    print("  2. Custom Job Description")
    while True:
        choice = input("Enter choice (1 or 2): ").strip()
        if choice in ("1", "2"):
            return int(choice)
        print("Invalid choice. Please enter 1 or 2.")


def select_weight_profile() -> str:
    profile_names = list(WEIGHT_PROFILES.keys())
    print("\nChoose a weight profile (affects how category scores are combined):")
    for i, name in enumerate(profile_names, 1):
        default_marker = " (default)" if name == DEFAULT_PROFILE else ""
        print(f"  {i}. {name}{default_marker}")
    choice = input(f"Enter choice (1-{len(profile_names)}, Enter for default): ").strip()
    if not choice:
        return DEFAULT_PROFILE
    try:
        index = int(choice) - 1
        if 0 <= index < len(profile_names):
            return profile_names[index]
    except ValueError:
        pass
    print(f"Invalid choice. Using default profile '{DEFAULT_PROFILE}'.")
    return DEFAULT_PROFILE


def load_job_description() -> str:
    if not os.path.exists(JOB_DESCRIPTION_PATH):
        print(f"Error: '{JOB_DESCRIPTION_PATH}' not found in the project root.")
        sys.exit(1)
    content = Path(JOB_DESCRIPTION_PATH).read_text(encoding="utf-8").strip()
    if not content:
        print(
            f"Error: '{JOB_DESCRIPTION_PATH}' is empty. "
            "Paste a job description into it before running in Custom Job Description mode."
        )
        sys.exit(1)
    return content


def print_evaluation_results(
    evaluation: EvaluationData, candidate_name: str = "Candidate"
):
    print("\n" + "=" * 80)
    print(f"📊 RESUME EVALUATION RESULTS FOR: {candidate_name}")
    print("=" * 80)

    if not evaluation:
        print("❌ No evaluation data available")
        return

    total_score = 0
    max_score = 0

    if hasattr(evaluation, "scores") and evaluation.scores:
        for category_name, category_data in evaluation.scores.model_dump().items():
            category_score = min(category_data["score"], category_data["max"])
            total_score += category_score
            max_score += category_data["max"]

            if category_score < category_data["score"]:
                print(
                    f"⚠️  Warning: {category_name} score capped from {category_data['score']} to {category_score} (max: {category_data['max']})"
                )

    if hasattr(evaluation, "bonus_points") and evaluation.bonus_points:
        total_score += evaluation.bonus_points.total

    if hasattr(evaluation, "deductions") and evaluation.deductions:
        total_score -= evaluation.deductions.total

    max_possible_score = max_score + 20
    if total_score > max_possible_score:
        total_score = max_possible_score
        print(f"⚠️  Warning: Total score capped at maximum possible value")

    print(f"\n🎯 OVERALL SCORE: {total_score:.1f}/{max_score}")

    print("\n📈 DETAILED SCORES:")
    print("-" * 60)

    if hasattr(evaluation, "scores") and evaluation.scores:
        category_maxes = {
            "open_source": 35,
            "self_projects": 30,
            "production": 25,
            "technical_skills": 10,
        }

        if hasattr(evaluation.scores, "open_source") and evaluation.scores.open_source:
            os_score = evaluation.scores.open_source
            capped_score = min(os_score.score, category_maxes["open_source"])
            print(f"🌐 Open Source:          {capped_score}/{os_score.max}")
            print(f"   Evidence: {os_score.evidence}")
            print()

        if (
            hasattr(evaluation.scores, "self_projects")
            and evaluation.scores.self_projects
        ):
            sp_score = evaluation.scores.self_projects
            capped_score = min(sp_score.score, category_maxes["self_projects"])
            print(f"🚀 Self Projects:        {capped_score}/{sp_score.max}")
            print(f"   Evidence: {sp_score.evidence}")
            print()

        if hasattr(evaluation.scores, "production") and evaluation.scores.production:
            prod_score = evaluation.scores.production
            capped_score = min(prod_score.score, category_maxes["production"])
            print(f"🏢 Production Experience: {capped_score}/{prod_score.max}")
            print(f"   Evidence: {prod_score.evidence}")
            print()

        if (
            hasattr(evaluation.scores, "technical_skills")
            and evaluation.scores.technical_skills
        ):
            tech_score = evaluation.scores.technical_skills
            capped_score = min(tech_score.score, category_maxes["technical_skills"])
            print(f"💻 Technical Skills:     {capped_score}/{tech_score.max}")
            print(f"   Evidence: {tech_score.evidence}")
            print()

    if hasattr(evaluation, "bonus_points") and evaluation.bonus_points:
        print(f"\n⭐ BONUS POINTS: {evaluation.bonus_points.total}")
        print("-" * 30)
        print(f"   {evaluation.bonus_points.breakdown}")

    if (
        hasattr(evaluation, "deductions")
        and evaluation.deductions
        and evaluation.deductions.total > 0
    ):
        print(f"\n⚠️  DEDUCTIONS: -{evaluation.deductions.total}")
        print("-" * 30)
        if evaluation.deductions.reasons:
            print(f"   {evaluation.deductions.reasons}")

    if hasattr(evaluation, "key_strengths") and evaluation.key_strengths:
        print(f"\n✅ KEY STRENGTHS:")
        print("-" * 30)
        for i, strength in enumerate(evaluation.key_strengths, 1):
            print(f"  {i}. {strength}")

    if (
        hasattr(evaluation, "areas_for_improvement")
        and evaluation.areas_for_improvement
    ):
        print(f"\n🔧 AREAS FOR IMPROVEMENT:")
        print("-" * 30)
        for i, area in enumerate(evaluation.areas_for_improvement, 1):
            print(f"  {i}. {area}")

    print("\n" + "=" * 80)


def print_job_evaluation_results(
    evaluation: JobEvaluationData, candidate_name: str = "Candidate"
):
    print("\n" + "=" * 80)
    print(f"📊 JOB MATCH EVALUATION FOR: {candidate_name}")
    print(f"   Target Role: {evaluation.job_title}")
    print("=" * 80)

    print(f"\n🎯 OVERALL MATCH: {evaluation.weighted_total}/100")
    if evaluation.keyword_match and evaluation.keyword_match.knockout_failed:
        print("   [CAPPED at 30 — reviewer confirmed a must-have is not met]")
    print(f"   Weight profile: {evaluation.weight_profile}")

    if evaluation.score_summary:
        print("\n💬 WHY THIS SCORE:")
        print("-" * 30)
        print(evaluation.score_summary)

    weights = WEIGHT_PROFILES.get(evaluation.weight_profile, WEIGHT_PROFILES[DEFAULT_PROFILE])

    print("\n📈 CATEGORY BREAKDOWN:")
    print("-" * 60)

    categories = [
        (f"💻 Skills Match       ({weights['skills_match']:.0%})", evaluation.scores.skills_match),
        (f"🏢 Experience Match   ({weights['experience_match']:.0%})", evaluation.scores.experience_match),
        (f"📋 Title Alignment    ({weights['job_title_alignment']:.0%})", evaluation.scores.job_title_alignment),
        (f"🎓 Education          ({weights['education']:.0%})", evaluation.scores.education),
        (f"📝 Resume Quality     ({weights['resume_quality']:.0%})", evaluation.scores.resume_quality),
        (f"⚠️  Missing Critical   ({weights['missing_critical_requirements']:.0%})", evaluation.scores.missing_critical_requirements),
    ]

    for label, category in categories:
        print(f"{label}: {category.score:.0f}/100")
        print(f"   Evidence: {category.evidence}")
        if category is evaluation.scores.job_title_alignment and evaluation.seniority:
            seniority = evaluation.seniority
            print(
                f"   Seniority: target={seniority.target_label}, candidate={seniority.candidate_label} "
                f"(gap {seniority.gap:+d})"
            )
        print()

    print(f"🔍 Semantic Match     ({weights['semantic_match']:.0%}): {evaluation.semantic_match_score:.1f}/100")
    print("   Whole-document embedding similarity (all-MiniLM-L6-v2) — supplementary signal.")
    print()

    if evaluation.keyword_match:
        keyword_match = evaluation.keyword_match
        print("🔑 KEYWORD MATCH:")
        print("-" * 30)
        coverage_line = f"Keyword coverage: {keyword_match.coverage_score:.1f}/100"
        if keyword_match.gated:
            coverage_line += " [CAPPED — a must-have qualification was not found]"
        print(coverage_line)

        total_required = len(keyword_match.matched_required) + len(keyword_match.missing_required)
        print(f"\nRequired skills matched ({len(keyword_match.matched_required)}/{total_required}):")
        print(f"  {', '.join(keyword_match.matched_required) if keyword_match.matched_required else 'None'}")
        print(f"Required skills MISSING:")
        print(f"  {', '.join(keyword_match.missing_required) if keyword_match.missing_required else 'None'}")

        total_preferred = len(keyword_match.matched_preferred) + len(keyword_match.missing_preferred)
        if total_preferred:
            print(f"\nPreferred skills matched ({len(keyword_match.matched_preferred)}/{total_preferred}):")
            print(f"  {', '.join(keyword_match.matched_preferred) if keyword_match.matched_preferred else 'None'}")
            print(f"Preferred skills missing:")
            print(f"  {', '.join(keyword_match.missing_preferred) if keyword_match.missing_preferred else 'None'}")

        if keyword_match.must_have_status:
            print("\nMust-have qualifications:")
            status_labels = {
                "found": "found",
                "not_found": "NOT FOUND",
                "unverifiable": "could not be verified by keyword matching",
            }
            for status in keyword_match.must_have_status:
                if status.resolved is True:
                    label = "confirmed by reviewer"
                elif status.resolved is False:
                    label = "REJECTED by reviewer (knockout)"
                else:
                    label = status_labels[status.status]
                print(f"  - {status.qualification}: {label}")

        if keyword_match.skill_experience:
            print("\nSKILL TENURE (deterministic, from work-history dates):")
            for skill_exp in keyword_match.skill_experience:
                if skill_exp.years > 0:
                    print(f"  - {skill_exp.skill}: {skill_exp.years} yrs")
                else:
                    print(f"  - {skill_exp.skill}: no dated evidence")
            if evaluation.jd_years_of_experience is not None and keyword_match.estimated_total_years is not None:
                print(
                    f"  JD asks for {evaluation.jd_years_of_experience} yrs; candidate total "
                    f"~{keyword_match.estimated_total_years} yrs (from parseable work dates)"
                )

        if evaluation.industry_match:
            industry_match = evaluation.industry_match
            if industry_match.mention_count:
                print(f"\nIndustry ({industry_match.industry}): mentioned in {industry_match.mention_count} work entr" +
                      ("y" if industry_match.mention_count == 1 else "ies"))
            else:
                print(f"\nIndustry ({industry_match.industry}): no literal mentions (LLM judges domain fit within Experience Match)")

        suggested_profile = suggest_profile(
            evaluation.job_title, evaluation.industry_match.industry if evaluation.industry_match else None
        )
        if suggested_profile != evaluation.weight_profile:
            print(
                f"\nNote: this JD looks like a '{suggested_profile}' role; consider rerunning with that "
                "weight profile (no extra LLM cost)."
            )
        print()

    if evaluation.key_strengths:
        print("✅ KEY STRENGTHS:")
        print("-" * 30)
        for i, strength in enumerate(evaluation.key_strengths, 1):
            print(f"  {i}. {strength}")

    if evaluation.areas_for_improvement:
        print(f"\n🔧 AREAS FOR IMPROVEMENT:")
        print("-" * 30)
        for i, area in enumerate(evaluation.areas_for_improvement, 1):
            print(f"  {i}. {area}")

    print("\n" + "=" * 80)


def print_parseability_report(result: Optional[ParseabilityResult]):
    if result is None:
        return

    print("\n📄 ATS PARSEABILITY (based on the original PDF's layout):")
    print("-" * 60)
    print(f"Parseability score: {result.parseability_score:.0f}/100")
    if result.warnings:
        for warning in result.warnings:
            print(f"  ⚠️  {warning}")
    else:
        print("  No layout issues detected — no tables, multi-column sections, or images found.")
    print()


def _evaluate_resume(
    resume_data: JSONResume, github_data: dict = None, blog_data: dict = None
) -> Optional[EvaluationData]:
    model_params = MODEL_PARAMETERS.get(DEFAULT_MODEL)
    evaluator = ResumeEvaluator(model_name=DEFAULT_MODEL, model_params=model_params)

    resume_text = convert_json_resume_to_text(resume_data)

    if github_data:
        github_text = convert_github_data_to_text(github_data)
        resume_text += github_text

    if blog_data:
        blog_text = convert_blog_data_to_text(blog_data)
        resume_text += blog_text

    return evaluator.evaluate_resume(resume_text)


def _knockout_resolver(qualification: str) -> Optional[bool]:
    print(f'\nMust-have could not be auto-verified: "{qualification}"')
    while True:
        answer = input("Does the candidate meet it? [y/n/s=skip]: ").strip().lower()
        if answer == "y":
            return True
        if answer == "n":
            return False
        if answer in ("s", ""):
            return None
        print("Invalid choice. Please enter y, n, or s.")


def _evaluate_with_job_description(
    resume_text: str,
    job_description: str,
    resume_data: Optional[JSONResume] = None,
    weight_profile: str = DEFAULT_PROFILE,
) -> Optional[JobEvaluationData]:
    model_params = MODEL_PARAMETERS.get(DEFAULT_MODEL)
    evaluator = JobDescriptionEvaluator(
        job_description=job_description,
        model_name=DEFAULT_MODEL,
        model_params=model_params,
        weight_profile=weight_profile,
    )
    return evaluator.evaluate(resume_text, resume_data=resume_data, knockout_resolver=_knockout_resolver)


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


def main():
    pdf_path = RESUME_PATH

    if not os.path.exists(pdf_path):
        print(f"Error: '{RESUME_PATH}' not found. Place your resume PDF in the project root.")
        sys.exit(1)

    mode = select_mode()

    job_description = None
    weight_profile = DEFAULT_PROFILE
    if mode == 2:
        job_description = load_job_description()
        weight_profile = select_weight_profile()

    cache_filename = (
        f"cache/resumecache_{os.path.basename(pdf_path).replace('.pdf', '')}.json"
    )
    github_cache_filename = (
        f"cache/githubcache_{os.path.basename(pdf_path).replace('.pdf', '')}.json"
    )

    parseability = scan_pdf_parseability(pdf_path)

    resume_data = None
    cache_loaded = False

    if DEVELOPMENT_MODE and os.path.exists(cache_filename) and os.path.getmtime(cache_filename) >= os.path.getmtime(pdf_path):
        print(f"Loading cached data from {cache_filename}")
        try:
            cached_data = json.loads(Path(cache_filename).read_text(encoding="utf-8"))
            loaded_resume = JSONResume(**cached_data)
            if not is_valid_resume_data(loaded_resume):
                raise ValueError("Cached resume data contains no core content")
            resume_data = loaded_resume
            cache_loaded = True
        except Exception as e:
            print(f"⚠️ Warning: Invalid cache file {cache_filename}: {e}")
            print("Ignoring cache and reprocessing PDF...")
            try:
                os.remove(cache_filename)
            except Exception as delete_err:
                print(f"Failed to delete invalid cache file {cache_filename}: {delete_err}")

    if not cache_loaded:
        logger.debug(
            f"Extracting data from PDF"
            + (" and caching to " + cache_filename if DEVELOPMENT_MODE else "")
        )
        pdf_handler = PDFHandler()
        resume_data = pdf_handler.extract_json_from_pdf(pdf_path)

        if resume_data is None:
            return None

        if DEVELOPMENT_MODE:
            if is_valid_resume_data(resume_data):
                os.makedirs(os.path.dirname(cache_filename), exist_ok=True)
                Path(cache_filename).write_text(
                    json.dumps(resume_data.model_dump(), indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            else:
                logger.warning(
                    "Newly extracted resume data is empty/invalid. Skipping cache write."
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
        except Exception as e:
            print(f"⚠️ Warning: Invalid GitHub cache file {github_cache_filename}: {e}")
            print("Ignoring GitHub cache and refetching...")
            try:
                os.remove(github_cache_filename)
            except Exception as delete_err:
                print(f"Failed to delete invalid GitHub cache file {github_cache_filename}: {delete_err}")

    if not github_cache_loaded:
        profiles = []
        if resume_data and hasattr(resume_data, "basics") and resume_data.basics:
            profiles = resume_data.basics.profiles or []
        github_profile = find_profile(profiles, "Github")

        if github_profile:
            print(
                f"Fetching GitHub data"
                + (
                    " and caching to " + github_cache_filename
                    if DEVELOPMENT_MODE
                    else ""
                )
            )
            github_data = fetch_and_display_github_info(github_profile.url)

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

    candidate_name = os.path.basename(pdf_path).replace(".pdf", "")
    if (
        resume_data
        and hasattr(resume_data, "basics")
        and resume_data.basics
        and resume_data.basics.name
    ):
        candidate_name = resume_data.basics.name

    if mode == 1:
        score = _evaluate_resume(resume_data, github_data)
        print_evaluation_results(score, candidate_name)
        print_parseability_report(parseability)

        if DEVELOPMENT_MODE:
            csv_row = transform_evaluation_response(
                file_name=os.path.basename(pdf_path),
                evaluation=score,
                resume_data=resume_data,
                github_data=github_data,
            )
            csv_path = "resume_evaluations.csv"
            file_exists = os.path.exists(csv_path)
            with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
                fieldnames = list(csv_row.keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(csv_row)

        return score

    else:
        resume_text = convert_json_resume_to_text(resume_data)
        if github_data:
            resume_text += convert_github_data_to_text(github_data)

        job_evaluation = _evaluate_with_job_description(
            resume_text, job_description, resume_data=resume_data, weight_profile=weight_profile
        )
        print_job_evaluation_results(job_evaluation, candidate_name)
        print_parseability_report(parseability)

        if DEVELOPMENT_MODE:
            csv_row = transform_job_evaluation_response(
                file_name=os.path.basename(pdf_path),
                evaluation=job_evaluation,
                resume_data=resume_data,
                parseability=parseability,
            )
            csv_path = "job_evaluations.csv"
            file_exists = os.path.exists(csv_path)
            with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
                fieldnames = list(csv_row.keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(csv_row)

        return job_evaluation


if __name__ == "__main__":
    main()
