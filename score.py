import os
import sys
import json
import logging
import csv

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

from pdf import PDFHandler
from github import fetch_and_display_github_info
from models import JSONResume, EvaluationData
from typing import List, Optional, Dict
from evaluator import ResumeEvaluator
from pathlib import Path
from prompt import DEFAULT_MODEL, MODEL_PARAMETERS
from transform import (
    transform_evaluation_response,
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


def print_evaluation_results(
    evaluation: EvaluationData, candidate_name: str = "Candidate"
):
    """Print evaluation results in a readable format."""
    print("\n" + "=" * 80)
    print(f"📊 RESUME EVALUATION RESULTS FOR: {candidate_name}")
    print("=" * 80)

    if not evaluation:
        print("❌ No evaluation data available")
        return

    # Calculate overall score
    total_score = 0
    max_score = 0

    if hasattr(evaluation, "scores") and evaluation.scores:
        for category_name, category_data in evaluation.scores.model_dump().items():
            category_score = min(category_data["score"], category_data["max"])
            total_score += category_score
            max_score += category_data["max"]

            # Log warning if score was capped
            if category_score < category_data["score"]:
                print(
                    f"⚠️  Warning: {category_name} score capped from {category_data['score']} to {category_score} (max: {category_data['max']})"
                )

    # Add bonus points
    if hasattr(evaluation, "bonus_points") and evaluation.bonus_points:
        total_score += evaluation.bonus_points.total

    # Subtract deductions
    if hasattr(evaluation, "deductions") and evaluation.deductions:
        total_score -= evaluation.deductions.total

    # Ensure total score doesn't exceed maximum possible score
    max_possible_score = max_score + 20  # 120 (100 categories + 20 bonus)
    if total_score > max_possible_score:
        total_score = max_possible_score
        print(f"⚠️  Warning: Total score capped at maximum possible value")

    # Overall Score
    print(f"\n🎯 OVERALL SCORE: {total_score:.1f}/{max_score}")

    # Detailed Scores
    print("\n📈 DETAILED SCORES:")
    print("-" * 60)

    if hasattr(evaluation, "scores") and evaluation.scores:
        # Define category maximums
        category_maxes = {
            "open_source": 35,
            "self_projects": 30,
            "production": 25,
            "technical_skills": 10,
        }

        # Open Source
        if hasattr(evaluation.scores, "open_source") and evaluation.scores.open_source:
            os_score = evaluation.scores.open_source
            capped_score = min(os_score.score, category_maxes["open_source"])
            print(f"🌐 Open Source:          {capped_score}/{os_score.max}")
            print(f"   Evidence: {os_score.evidence}")
            print()

        # Self Projects
        if (
            hasattr(evaluation.scores, "self_projects")
            and evaluation.scores.self_projects
        ):
            sp_score = evaluation.scores.self_projects
            capped_score = min(sp_score.score, category_maxes["self_projects"])
            print(f"🚀 Self Projects:        {capped_score}/{sp_score.max}")
            print(f"   Evidence: {sp_score.evidence}")
            print()

        # Production Experience
        if hasattr(evaluation.scores, "production") and evaluation.scores.production:
            prod_score = evaluation.scores.production
            capped_score = min(prod_score.score, category_maxes["production"])
            print(f"🏢 Production Experience: {capped_score}/{prod_score.max}")
            print(f"   Evidence: {prod_score.evidence}")
            print()

        # Technical Skills
        if (
            hasattr(evaluation.scores, "technical_skills")
            and evaluation.scores.technical_skills
        ):
            tech_score = evaluation.scores.technical_skills
            capped_score = min(tech_score.score, category_maxes["technical_skills"])
            print(f"💻 Technical Skills:     {capped_score}/{tech_score.max}")
            print(f"   Evidence: {tech_score.evidence}")
            print()

    # Bonus Points
    if hasattr(evaluation, "bonus_points") and evaluation.bonus_points:
        print(f"\n⭐ BONUS POINTS: {evaluation.bonus_points.total}")
        print("-" * 30)
        print(f"   {evaluation.bonus_points.breakdown}")

    # Deductions
    if (
        hasattr(evaluation, "deductions")
        and evaluation.deductions
        and evaluation.deductions.total > 0
    ):
        print(f"\n⚠️  DEDUCTIONS: -{evaluation.deductions.total}")
        print("-" * 30)
        if evaluation.deductions.reasons:
            print(f"   {evaluation.deductions.reasons}")

    # Key Strengths
    if hasattr(evaluation, "key_strengths") and evaluation.key_strengths:
        print(f"\n✅ KEY STRENGTHS:")
        print("-" * 30)
        for i, strength in enumerate(evaluation.key_strengths, 1):
            print(f"  {i}. {strength}")

    # Areas for Improvement
    if (
        hasattr(evaluation, "areas_for_improvement")
        and evaluation.areas_for_improvement
    ):
        print(f"\n🔧 AREAS FOR IMPROVEMENT:")
        print("-" * 30)
        for i, area in enumerate(evaluation.areas_for_improvement, 1):
            print(f"  {i}. {area}")

    if getattr(evaluation, "bullet_point_analysis", None):
        bullets = evaluation.bullet_point_analysis
        strong_bullets = [b for b in bullets if b.assessment == "strong"]
        weak_bullets = [b for b in bullets if b.assessment == "weak"]

        print(f"\n📝 BULLET POINT ANALYSIS:")
        print("-" * 30)
        print(f"   {len(strong_bullets)} strong, {len(weak_bullets)} weak")

        if strong_bullets:
            print(f"\n  💪 Strong bullets:")
            for i, bullet in enumerate(strong_bullets, 1):
                print(f"    {i}. {bullet.text}")

        if weak_bullets:
            print(f"\n  ⚠️  Weak bullets:")
            for i, bullet in enumerate(weak_bullets, 1):
                flag = " 🚩 authenticity concern" if bullet.authenticity_concern else ""
                print(f"    {i}. {bullet.text}{flag}")
                if bullet.issues:
                    print(f"       Issues: {', '.join(bullet.issues)}")
                if bullet.suggested_rewrite:
                    print(f"       Rewrite: {bullet.suggested_rewrite}")

    print("\n" + "=" * 80)


def _evaluate_resume(
    resume_data: JSONResume, github_data: dict = None, blog_data: dict = None
) -> Optional[EvaluationData]:
    """Evaluate the resume using AI and display results."""

    model_params = MODEL_PARAMETERS.get(DEFAULT_MODEL)
    evaluator = ResumeEvaluator(model_name=DEFAULT_MODEL, model_params=model_params)

    # Convert JSON resume data to text
    resume_text = convert_json_resume_to_text(resume_data)

    # Add GitHub data if available
    if github_data:
        github_text = convert_github_data_to_text(github_data)
        resume_text += github_text

    # Add blog data if available
    if blog_data:
        blog_text = convert_blog_data_to_text(blog_data)
        resume_text += blog_text

    # Evaluate the enhanced resume
    evaluation_result = evaluator.evaluate_resume(resume_text)

    # print(evaluation_result)

    return evaluation_result


def is_valid_resume_data(resume_data: JSONResume) -> bool:
    """Check if the resume data has at least some extracted core content."""
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


def main(pdf_path):
    # Create cache filename based on PDF path
    cache_filename = (
        f"cache/resumecache_{os.path.basename(pdf_path).replace('.pdf', '')}.json"
    )
    github_cache_filename = (
        f"cache/githubcache_{os.path.basename(pdf_path).replace('.pdf', '')}.json"
    )

    resume_data = None
    cache_loaded = False

    # Check if cache exists and we're in development mode
    if DEVELOPMENT_MODE and os.path.exists(cache_filename):
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
                print(
                    f"Failed to delete invalid cache file {cache_filename}: {delete_err}"
                )

    if not cache_loaded:
        logger.debug(
            f"Extracting data from PDF"
            + (" and caching to " + cache_filename if DEVELOPMENT_MODE else "")
        )
        pdf_handler = PDFHandler()
        resume_data = pdf_handler.extract_json_from_pdf(pdf_path)

        if resume_data == None:
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

    # Check if cache exists and we're in development mode
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
                print(
                    f"Failed to delete invalid GitHub cache file {github_cache_filename}: {delete_err}"
                )

    if not github_cache_loaded:
        # Add validation to handle None values
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

    score = _evaluate_resume(resume_data, github_data)

    # Get candidate name for display
    candidate_name = os.path.basename(pdf_path).replace(".pdf", "")
    if (
        resume_data
        and hasattr(resume_data, "basics")
        and resume_data.basics
        and resume_data.basics.name
    ):
        candidate_name = resume_data.basics.name

    # Print evaluation results in readable format
    print_evaluation_results(score, candidate_name)

    if DEVELOPMENT_MODE:
        csv_row = transform_evaluation_response(
            file_name=os.path.basename(pdf_path),
            evaluation=score,
            resume_data=resume_data,
            github_data=github_data,
        )

        # Write CSV row to file
        csv_path = "resume_evaluations.csv"
        file_exists = os.path.exists(csv_path)

        with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
            fieldnames = list(csv_row.keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write headers if file doesn't exist
            if not file_exists:
                writer.writeheader()

            # Write the row
            writer.writerow(csv_row)

    return score


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python score.py <pdf_path>")
        exit(1)
    pdf_path = sys.argv[1]

    if not os.path.exists(pdf_path):
        print(f"Error: File '{pdf_path}' does not exist.")
        exit(1)

    main(pdf_path)
