import os
import sys
import json

# Fix for Windows Console Unicode errors
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Fix for Python 3.14 Protobuf TypeError
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import logging
import csv

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

import argparse

from pdf import PDFHandler
from github import fetch_and_display_github_info
from models import JSONResume, build_evaluation_model
from typing import List, Optional, Dict
from evaluator import ResumeEvaluator
from roles import Role, load_role, list_available_roles, scaffold_role
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
    evaluation, role: Role, candidate_name: str = "Candidate"
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
    max_possible_score = max_score + role.bonus_max
    if total_score > max_possible_score:
        total_score = max_possible_score
        print(f"⚠️  Warning: Total score capped at maximum possible value")

    # Overall Score
    print(f"\n🎯 OVERALL SCORE: {total_score:.1f}/{max_score}")

    # Detailed Scores
    print("\n📈 DETAILED SCORES:")
    print("-" * 60)

    if hasattr(evaluation, "scores") and evaluation.scores:
        for category in role.categories:
            cat_score = getattr(evaluation.scores, category.key, None)
            if not cat_score:
                continue
            capped_score = min(cat_score.score, category.max)
            print(f"{category.icon} {category.label}: {capped_score}/{cat_score.max}")
            print(f"   Evidence: {cat_score.evidence}")
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

    print("\n" + "=" * 80)


def _evaluate_resume(
    resume_data: JSONResume,
    role: Role,
    evaluation_model,
    github_data: dict = None,
    blog_data: dict = None,
    model_name: str = DEFAULT_MODEL,
):
    """Evaluate the resume using AI and display results."""

    model_params = MODEL_PARAMETERS.get(
        model_name, {"temperature": 0.1, "top_p": 0.9}
    )
    evaluator = ResumeEvaluator(
        role=role,
        evaluation_model=evaluation_model,
        model_name=model_name,
        model_params=model_params,
    )

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


def main(pdf_path, role: Role, model_name: str = DEFAULT_MODEL):
    evaluation_model = build_evaluation_model(role)
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
            github_data = fetch_and_display_github_info(
                github_profile.url, position_title=role.position_title
            )

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

    score = _evaluate_resume(
        resume_data,
        role,
        evaluation_model,
        github_data,
        model_name=model_name,
    )

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
    print(f"\n[Model Used: {model_name}]")
    print_evaluation_results(score, role, candidate_name)

    if DEVELOPMENT_MODE:
        csv_row = transform_evaluation_response(
            file_name=os.path.basename(pdf_path),
            evaluation=score,
            resume_data=resume_data,
            github_data=github_data,
            role=role,
        )
        csv_row["model_name"] = model_name

        # Write CSV row to a role-specific file, since each role's columns differ.
        csv_path = f"resume_evaluations_{role.name}.csv"
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
    available_roles = list_available_roles()
    parser = argparse.ArgumentParser(
        description="Score a resume against a role's rubric."
    )
    parser.add_argument(
        "pdf_path", nargs="?", help="Path to the resume PDF to evaluate"
    )
    parser.add_argument(
        "--role",
        help="Role to score against (a directory name under roles/). "
        + (f"Available: {', '.join(available_roles)}" if available_roles else ""),
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model to use for evaluation (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--init-role",
        metavar="NAME",
        help="Scaffold a new role directory under roles/ with basic template "
        "files, then exit (does not score a resume).",
    )
    args = parser.parse_args()

    # Scaffold mode: create a new role and exit.
    if args.init_role:
        try:
            role_dir = scaffold_role(args.init_role)
        except ValueError as e:
            print(f"Error: {e}")
            exit(1)
        print(f"✅ Created role '{args.init_role}' at {role_dir}")
        print("   Edit role.json, criteria.jinja and system_message.jinja, then run:")
        print(f"   python score.py <pdf_path> --role {args.init_role}")
        exit(0)

    # Scoring mode: both pdf_path and --role are required.
    if not args.pdf_path or not args.role:
        parser.error("pdf_path and --role are required (or use --init-role NAME)")

    if not os.path.exists(args.pdf_path):
        print(f"Error: File '{args.pdf_path}' does not exist.")
        exit(1)

    try:
        role = load_role(args.role)
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)

    main(args.pdf_path, role, model_name=args.model)
