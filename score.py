import os
import sys
import json
import logging
import csv
import argparse
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
from prompts.template_manager import TemplateManager
import hashlib

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


def find_profile(profiles, network):
    if not profiles:
        return None
    return next(
        (p for p in profiles if p.network and p.network.lower() == network.lower()),
        None,
    )


def _is_empty_resume(resume_data: JSONResume) -> bool:
    if not resume_data:
        return True
    key_sections = [
        "basics",
        "work",
        "education",
        "skills",
        "projects",
        "awards",
    ]
    for sec in key_sections:
        val = getattr(resume_data, sec, None)
        if val:
            # If any section has content (dict/list/object), treat as non-empty
            try:
                if isinstance(val, (list, dict)) and len(val) > 0:
                    return False
                # Basics is a pydantic model. If it has at least one non-null attribute -> non-empty
                fields = getattr(val.__class__, "model_fields", None)
                if fields:
                    for field_name in fields.keys():
                        if getattr(val, field_name, None):
                            return False
            except Exception:
                pass
            # Non-container truthy object
            return False
    return True


def main(pdf_path, force: bool = False, no_github: bool = False, max_workers: int = 3):
    # Create cache filename based on PDF path
    cache_filename = (
        f"cache/resumecache_{os.path.basename(pdf_path).replace('.pdf', '')}.json"
    )
    github_cache_filename = (
        f"cache/githubcache_{os.path.basename(pdf_path).replace('.pdf', '')}.json"
    )

    # Check if cache exists and we're in development mode
    if not force and DEVELOPMENT_MODE and os.path.exists(cache_filename):
        print(f"Loading cached data from {cache_filename}")
        cached_raw = json.loads(Path(cache_filename).read_text())

        # Validate cache metadata if present
        use_cache = True
        cache_meta = cached_raw.get("_cache_meta")
        if cache_meta:
            # Verify file hash
            try:
                with open(pdf_path, "rb") as f:
                    data = f.read()
                file_hash = hashlib.md5(data).hexdigest()
                if cache_meta.get("file_hash") != file_hash:
                    print("⚠️ Resume file changed since cache was written. Ignoring cached resume.")
                    use_cache = False
                # Verify model/template
                if cache_meta.get("model") != DEFAULT_MODEL:
                    print("⚠️ Model changed since cache was written. Ignoring cached resume.")
                    use_cache = False
            except Exception:
                use_cache = False

        if use_cache:
            cached_data = cached_raw.get("data", cached_raw)
            resume_data = JSONResume(**cached_data)
        else:
            resume_data = None
    else:
        logger.debug(
            f"Extracting data from PDF"
            + (" and caching to " + cache_filename if DEVELOPMENT_MODE else "")
        )
        pdf_handler = PDFHandler(max_workers=max_workers)
        resume_data = pdf_handler.extract_json_from_pdf(pdf_path)

        if resume_data == None:
            return None

        if DEVELOPMENT_MODE:
            os.makedirs(os.path.dirname(cache_filename), exist_ok=True)
            # Write cache with metadata to allow validation later
            tm = TemplateManager()
            template_sources = tm.get_all_template_sources()
            template_hashes = {name: hashlib.sha256(src.encode("utf-8")).hexdigest() for name, src in template_sources.items()}
            with open(cache_filename, "w", encoding="utf-8") as fh:
                wrapper = {
                    "_cache_meta": {
                        "file_hash": hashlib.md5(open(pdf_path, "rb").read()).hexdigest(),
                        "model": DEFAULT_MODEL,
                        "template_hashes": template_hashes,
                    },
                    "data": resume_data.model_dump(),
                }
                fh.write(json.dumps(wrapper, indent=2, ensure_ascii=False))

    # Check if cache exists and we're in development mode
    github_data = {}
    gh_cache_exists = os.path.exists(github_cache_filename)
    use_gh_cache = (not force) and DEVELOPMENT_MODE and gh_cache_exists
    if no_github:
        print("Skipping GitHub fetch due to --no-github flag")
        github_data = {}
    elif use_gh_cache:
        print(f"Loading cached data from {github_cache_filename}")
        try:
            cached_raw = json.loads(Path(github_cache_filename).read_text())
        except Exception as e:
            print(f"⚠️ Failed to read GitHub cache: {e}. Will refetch.")
            cached_raw = None

        cache_valid = False
        if cached_raw:
            cache_meta = cached_raw.get("_cache_meta")
            if cache_meta and cache_meta.get("model") != DEFAULT_MODEL:
                print("⚠️ GitHub cache model mismatch. Ignoring cached GitHub data.")
            else:
                candidate = cached_raw.get("data", cached_raw)
                # Consider cache invalid if empty or missing profile/projects
                if candidate and isinstance(candidate, dict):
                    total_projects = candidate.get("total_projects")
                    profile = candidate.get("profile")
                    has_username = bool(profile and profile.get("username"))
                    has_projects = isinstance(candidate.get("projects"), list) and len(candidate.get("projects")) > 0
                    if has_username and (has_projects or (isinstance(total_projects, int) and total_projects > 0)):
                        github_data = candidate
                        cache_valid = True
        if not cache_valid:
            print("⚠️ GitHub cache is empty or invalid. Fetching fresh data...")
    if (not no_github) and (not use_gh_cache or (use_gh_cache and not cache_valid)):
        print(
            f"Fetching GitHub data"
            + (" and caching to " + github_cache_filename if DEVELOPMENT_MODE else "")
        )

        # Add validation to handle None values
        profiles = []
        if resume_data and hasattr(resume_data, "basics") and resume_data.basics:
            profiles = resume_data.basics.profiles or []
        github_profile = find_profile(profiles, "Github")

        if github_profile:
            github_data = fetch_and_display_github_info(github_profile.url)
        if DEVELOPMENT_MODE:
            os.makedirs(os.path.dirname(github_cache_filename), exist_ok=True)
            with open(github_cache_filename, "w", encoding="utf-8") as fh:
                wrapper = {
                    "_cache_meta": {
                        "model": DEFAULT_MODEL,
                    },
                    "data": github_data,
                }
                fh.write(json.dumps(wrapper, indent=2, ensure_ascii=False))

    # If cached resume is empty, attempt a fresh extraction
    if (force or _is_empty_resume(resume_data)):
        if _is_empty_resume(resume_data):
            print("⚠️ Cached resume appears empty. Attempting re-extraction...")
        pdf_handler = PDFHandler(max_workers=max_workers)
        fresh_resume = pdf_handler.extract_json_from_pdf(pdf_path)
        if fresh_resume and not _is_empty_resume(fresh_resume):
            resume_data = fresh_resume
            if DEVELOPMENT_MODE:
                try:
                    tm = TemplateManager()
                    template_sources = tm.get_all_template_sources()
                    template_hashes = {name: hashlib.sha256(src.encode("utf-8")).hexdigest() for name, src in template_sources.items()}
                    with open(cache_filename, "w", encoding="utf-8") as fh:
                        wrapper = {
                            "_cache_meta": {
                                "file_hash": hashlib.md5(open(pdf_path, "rb").read()).hexdigest(),
                                "model": DEFAULT_MODEL,
                                "template_hashes": template_hashes,
                            },
                            "data": resume_data.model_dump(),
                        }
                        fh.write(json.dumps(wrapper, indent=2, ensure_ascii=False))
                    print("✅ Re-extracted resume and updated cache.")
                except Exception as e:
                    print(f"⚠️ Failed to update cache after re-extraction: {e}")
        else:
            print("❌ Re-extraction failed or still empty; proceeding with existing data.")

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
    parser = argparse.ArgumentParser(description="Evaluate a resume PDF and output scores.")
    parser.add_argument("pdf_path", help="Path to the resume PDF file")
    parser.add_argument("--force", action="store_true", help="Bypass caches and re-extract")
    parser.add_argument("--no-github", action="store_true", help="Skip GitHub fetch and enrichment")
    parser.add_argument("--max-workers", type=int, default=3, help="Max parallel section extractions (default: 3)")
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"Error: File '{args.pdf_path}' does not exist.")
        exit(1)

    main(args.pdf_path, force=args.force, no_github=args.no_github, max_workers=args.max_workers)
