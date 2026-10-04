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
import statistics

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
from ensemble import aggregate_evaluations, EnsembleResult

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


def print_ensemble_results(
    ensemble: EnsembleResult, role: Role, candidate_name: str = "Candidate"
):
    """Print ensemble evaluation results with statistical confidence metrics."""
    print("\n" + "=" * 80)
    print(f"📊 ENSEMBLE RESUME EVALUATION RESULTS FOR: {candidate_name}")
    print(f"   Based on {ensemble.num_runs} independent evaluation runs")
    print("=" * 80)

    # Calculate max possible score
    max_score = sum(cs.max_score for cs in ensemble.category_stats.values())

    # Overall Score (median)
    print(
        f"\n🎯 MEDIAN SCORE: {ensemble.median_total:.1f}/{max_score} "
        f"(range: {min(ensemble.total_scores):.1f}-{max(ensemble.total_scores):.1f})"
    )
    print(f"   Confidence: {ensemble.confidence_label}")
    if ensemble.num_runs > 1:
        print(
            f"   Standard Deviation: {ensemble.total_stdev:.2f} "
            f"({(ensemble.total_stdev / max_score * 100):.1f}% of max)"
        )

    if not ensemble.is_high_confidence:
        print(
            f"\n⚠️  LOW CONFIDENCE: Score varied by {ensemble.total_range:.1f} points "
            f"({(ensemble.total_range / max_score * 100):.1f}% of max possible). "
            "This indicates non-deterministic LLM scoring."
        )

    # Detailed Scores by Category
    print("\n📈 DETAILED SCORES (Median ± StdDev):")
    print("-" * 70)

    for category in role.categories:
        stats = ensemble.category_stats.get(category.key)
        if not stats or not stats.scores:
            continue

        stability_icon = "✓" if stats.is_stable else "⚠"
        print(
            f"{stability_icon} {category.icon} {category.label}: "
            f"{stats.median:.1f} ± {stats.stdev:.2f}/{stats.max_score} "
            f"(range: {stats.min:.1f}-{stats.max_val:.1f})"
        )

        # Show most representative evidence (from median run)
        median_idx = sorted(
            range(len(stats.scores)), key=lambda i: abs(stats.scores[i] - stats.median)
        )[0]
        print(f"   Evidence: {stats.evidence_samples[median_idx]}")
        print()

    # Bonus and Deductions
    if ensemble.bonus_scores:
        median_bonus = statistics.median(ensemble.bonus_scores)
        print(f"\n⭐ BONUS POINTS (Median): {median_bonus:.1f}")
        if ensemble.num_runs > 1:
            print(
                f"   Range: {min(ensemble.bonus_scores):.1f}-{max(ensemble.bonus_scores):.1f}"
            )

    if ensemble.deduction_scores and any(d > 0 for d in ensemble.deduction_scores):
        median_deduction = statistics.median(ensemble.deduction_scores)
        print(f"\n⚠️  DEDUCTIONS (Median): -{median_deduction:.1f}")
        if ensemble.num_runs > 1:
            print(
                f"   Range: {min(ensemble.deduction_scores):.1f}-{max(ensemble.deduction_scores):.1f}"
            )

    # Key Strengths (appearing in majority of runs)
    frequent_strengths = ensemble.most_frequent_strengths
    if frequent_strengths:
        print(f"\n✅ KEY STRENGTHS (consistent across runs):")
        print("-" * 40)
        for i, strength in enumerate(frequent_strengths, 1):
            print(f"  {i}. {strength}")

    # Areas for Improvement (appearing in majority of runs)
    frequent_improvements = ensemble.most_frequent_improvements
    if frequent_improvements:
        print(f"\n🔧 AREAS FOR IMPROVEMENT (consistent across runs):")
        print("-" * 40)
        for i, area in enumerate(frequent_improvements, 1):
            print(f"  {i}. {area}")

    print("\n" + "=" * 80)


def _evaluate_resume(
    resume_data: JSONResume,
    role: Role,
    evaluation_model,
    github_data: dict = None,
    blog_data: dict = None,
):
    """Evaluate the resume using AI and display results."""

    model_params = MODEL_PARAMETERS.get(DEFAULT_MODEL)
    evaluator = ResumeEvaluator(
        role=role,
        evaluation_model=evaluation_model,
        model_name=DEFAULT_MODEL,
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


def main(pdf_path, role: Role, ensemble_runs: int = 1):
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

    # Get candidate name for display
    candidate_name = os.path.basename(pdf_path).replace(".pdf", "")
    if (
        resume_data
        and hasattr(resume_data, "basics")
        and resume_data.basics
        and resume_data.basics.name
    ):
        candidate_name = resume_data.basics.name

    # Ensemble mode: run evaluation multiple times
    if ensemble_runs > 1:
        print(f"\n🔄 Running {ensemble_runs} independent evaluations for ensemble scoring...")
        evaluations = []
        for run_num in range(1, ensemble_runs + 1):
            print(f"   Run {run_num}/{ensemble_runs}...", end=" ", flush=True)
            evaluation = _evaluate_resume(resume_data, role, evaluation_model, github_data)
            evaluations.append(evaluation)
            print("✓")

        # Aggregate results
        ensemble_result = aggregate_evaluations(evaluations, role)
        print_ensemble_results(ensemble_result, role, candidate_name)

        if DEVELOPMENT_MODE:
            # For ensemble mode, use median evaluation for CSV export
            median_idx = sorted(
                range(len(ensemble_result.total_scores)),
                key=lambda i: abs(
                    ensemble_result.total_scores[i] - ensemble_result.median_total
                ),
            )[0]
            median_evaluation = ensemble_result.individual_evaluations[median_idx]

            csv_row = transform_evaluation_response(
                file_name=os.path.basename(pdf_path),
                evaluation=median_evaluation,
                resume_data=resume_data,
                github_data=github_data,
                role=role,
            )
            # Add ensemble metadata
            csv_row["ensemble_runs"] = ensemble_runs
            csv_row["ensemble_median_score"] = ensemble_result.median_total
            csv_row["ensemble_score_range"] = ensemble_result.total_range
            csv_row["ensemble_confidence"] = ensemble_result.confidence_label

            csv_path = f"resume_evaluations_{role.name}.csv"
            file_exists = os.path.exists(csv_path)

            with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
                fieldnames = list(csv_row.keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                if not file_exists:
                    writer.writeheader()

                writer.writerow(csv_row)

        return ensemble_result

    # Single run mode (default)
    else:
        score = _evaluate_resume(resume_data, role, evaluation_model, github_data)
        print_evaluation_results(score, role, candidate_name)

        if DEVELOPMENT_MODE:
            csv_row = transform_evaluation_response(
                file_name=os.path.basename(pdf_path),
                evaluation=score,
                resume_data=resume_data,
                github_data=github_data,
                role=role,
            )

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
        "--init-role",
        metavar="NAME",
        help="Scaffold a new role directory under roles/ with basic template "
        "files, then exit (does not score a resume).",
    )
    parser.add_argument(
        "--ensemble",
        type=int,
        default=1,
        metavar="N",
        help="Run evaluation N times and aggregate results for statistical confidence. "
        "Default: 1 (single run). Recommended: 3-5 for production use to mitigate "
        "LLM non-determinism.",
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

    # Validate ensemble runs
    if args.ensemble < 1:
        parser.error("--ensemble must be at least 1")
    if args.ensemble > 10:
        print(
            f"⚠️  Warning: Running {args.ensemble} evaluations will take significant time "
            "and API costs. Recommended: 3-5 for most use cases."
        )

    try:
        role = load_role(args.role)
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)

    main(args.pdf_path, role, ensemble_runs=args.ensemble)
