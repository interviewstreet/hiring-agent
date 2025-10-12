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

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)5s - %(lineno)5d - %(funcName)33s - %(levelname)5s - %(message)s",
)


def print_evaluation_results(
    evaluation: EvaluationData, candidate_name: str = "Candidate", quiet_mode: bool = False
):
    """Print evaluation results in a readable format."""
    if not evaluation:
        if quiet_mode:
            print(f"❌ {candidate_name}: No evaluation data available")
        else:
            print("\n" + "=" * 80)
            print(f"📊 RESUME EVALUATION RESULTS FOR: {candidate_name}")
            print("=" * 80)
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
            if category_score < category_data["score"] and not quiet_mode:
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
        if not quiet_mode:
            print(f"⚠️  Warning: Total score capped at maximum possible value")

    if quiet_mode:
        print(f"✓ {candidate_name}: Score {total_score:.1f}/{max_score}")
        return

    # Overall Score
    print("\n" + "=" * 80)
    print(f"📊 RESUME EVALUATION RESULTS FOR: {candidate_name}")
    print("=" * 80)
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
    resume_data: JSONResume, github_data: dict = None, blog_data: dict = None, provider=None
) -> Optional[EvaluationData]:
    """Evaluate the resume using AI and display results."""

    model_params = MODEL_PARAMETERS.get(DEFAULT_MODEL)
    evaluator = ResumeEvaluator(model_name=DEFAULT_MODEL, model_params=model_params, provider=provider)

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


def find_pdf_files(folder_path: str, recursive: bool = False) -> List[str]:
    """
    Find all PDF files in the given folder path.
    
    Args:
        folder_path: Path to the folder to search
        recursive: If True, search recursively in all subfolders
    
    Returns:
        Sorted list of absolute paths to PDF files
    """
    pdf_files = []
    
    if recursive:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.abspath(os.path.join(root, file)))
    else:
        try:
            for file in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file)
                if os.path.isfile(file_path) and file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.abspath(file_path))
        except OSError as e:
            logger.error(f"Error reading folder {folder_path}: {e}")
            return []
    
    return sorted(pdf_files)


def process_folder(folder_path: str, recursive: bool = False) -> None:
    """
    Process all PDF files in a folder.
    
    Args:
        folder_path: Path to the folder containing PDF files
        recursive: If True, search recursively in all subfolders
    """
    pdf_files = find_pdf_files(folder_path, recursive)
    
    if not pdf_files:
        print(f"No PDF files found in {folder_path}")
        return
    
    from llm_utils import initialize_llm_provider
    print("Initializing LLM provider...")
    provider = initialize_llm_provider(DEFAULT_MODEL)
    
    print(f"\n📁 Found {len(pdf_files)} PDF file(s) in '{folder_path}'")
    if recursive:
        print("   (searching recursively)")
    print("=" * 80)
    
    successful = 0
    failed = 0
    failed_files = []
    
    for idx, pdf_path in enumerate(pdf_files, 1):
        filename = os.path.basename(pdf_path)
        print(f"\n[{idx}/{len(pdf_files)}] Processing {filename}...")
        
        try:
            result = main(pdf_path, quiet_mode=True, provider=provider)
            if result is not None:
                successful += 1
            else:
                failed += 1
                failed_files.append(filename)
        except Exception as e:
            failed += 1
            failed_files.append(filename)
            logger.error(f"Error processing {filename}: {e}")
            print(f"❌ {filename}: Failed - {str(e)}")
    
    print("\n" + "=" * 80)
    print("📊 BATCH PROCESSING SUMMARY")
    print("=" * 80)
    print(f"Total files: {len(pdf_files)}")
    print(f"✓ Successfully processed: {successful}")
    print(f"❌ Failed: {failed}")
    
    if failed_files:
        print(f"\nFailed files:")
        for filename in failed_files:
            print(f"  - {filename}")
    
    if DEVELOPMENT_MODE:
        print(f"\nResults saved to: resume_evaluations.csv")
    
    print("=" * 80)


def main(pdf_path, quiet_mode: bool = False, provider=None):
    # Create cache filename based on PDF path
    cache_filename = (
        f"cache/resumecache_{os.path.basename(pdf_path).replace('.pdf', '')}.json"
    )
    github_cache_filename = (
        f"cache/githubcache_{os.path.basename(pdf_path).replace('.pdf', '')}.json"
    )

    # Check if cache exists and we're in development mode
    if DEVELOPMENT_MODE and os.path.exists(cache_filename):
        print(f"Loading cached data from {cache_filename}")
        cached_data = json.loads(Path(cache_filename).read_text())
        resume_data = JSONResume(**cached_data)
    else:
        logger.debug(
            f"Extracting data from PDF"
            + (" and caching to " + cache_filename if DEVELOPMENT_MODE else "")
        )
        pdf_handler = PDFHandler(provider)
        resume_data = pdf_handler.extract_json_from_pdf(pdf_path)

        if resume_data == None:
            return None

        if DEVELOPMENT_MODE:
            os.makedirs(os.path.dirname(cache_filename), exist_ok=True)
            Path(cache_filename).write_text(
                json.dumps(resume_data.model_dump(), indent=2, ensure_ascii=False)
            )

    # Check if cache exists and we're in development mode
    github_data = {}
    if DEVELOPMENT_MODE and os.path.exists(github_cache_filename):
        print(f"Loading cached data from {github_cache_filename}")
        github_data = json.loads(Path(github_cache_filename).read_text())
    else:
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
            github_data = fetch_and_display_github_info(github_profile.url, provider)
        if DEVELOPMENT_MODE:
            os.makedirs(os.path.dirname(github_cache_filename), exist_ok=True)
            Path(github_cache_filename).write_text(
                json.dumps(github_data, indent=2, ensure_ascii=False)
            )

    score = _evaluate_resume(resume_data, github_data, provider=provider)

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
    print_evaluation_results(score, candidate_name, quiet_mode)

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
    parser = argparse.ArgumentParser(
        description="Resume scoring tool - evaluate single resume or batch process a folder of resumes"
    )
    parser.add_argument(
        "path",
        help="Path to a PDF file or folder containing PDF files"
    )
    parser.add_argument(
        "-f", "--folder",
        action="store_true",
        help="Process all PDF files in the specified folder"
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="When using --folder, recursively search subfolders for PDFs"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.path):
        print(f"Error: Path '{args.path}' does not exist.")
        exit(1)
    
    if args.folder:
        if not os.path.isdir(args.path):
            print(f"Error: Path '{args.path}' is not a folder. Use -f/--folder only with folders.")
            exit(1)
        process_folder(args.path, args.recursive)
    else:
        if os.path.isdir(args.path):
            print(f"Error: Path '{args.path}' is a folder. Use -f/--folder to process folders.")
            exit(1)
        if not args.path.lower().endswith('.pdf'):
            print(f"Error: File '{args.path}' is not a PDF file.")
            exit(1)
        main(args.path)
