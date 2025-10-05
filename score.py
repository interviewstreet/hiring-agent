import os
import sys
import json
import logging
import csv
from pdf import PDFHandler
from github import fetch_and_display_github_info
from models import JSONResume, EvaluationData
from typing import Optional
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
import fitz  # PyMuPDF for PDF validation

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)5s - %(lineno)5d - %(funcName)33s - %(levelname)5s - %(message)s",
)

# -----------------------------------------------------------------------------
# PDF Validation
# -----------------------------------------------------------------------------
def is_pdf_valid(pdf_path: str) -> bool:
    """Check if the PDF file is valid and non-corrupted."""
    try:
        doc = fitz.open(pdf_path)
        if doc.page_count < 1:
            logger.error("PDF file has no pages.")
            return False
        return True
    except Exception as e:
        logger.error(f"Invalid PDF file detected: {e}")
        return False

# -----------------------------------------------------------------------------
# Print Results
# -----------------------------------------------------------------------------
def print_evaluation_results(evaluation: EvaluationData, candidate_name: str = "Candidate"):
    """Print evaluation results in a readable format."""
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
                    f"⚠️ Warning: {category_name} score capped from {category_data['score']} to {category_score} (max: {category_data['max']})"
                )

    if hasattr(evaluation, "bonus_points") and evaluation.bonus_points:
        total_score += evaluation.bonus_points.total

    if hasattr(evaluation, "deductions") and evaluation.deductions:
        total_score -= evaluation.deductions.total

    max_possible_score = max_score + 20
    if total_score > max_possible_score:
        total_score = max_possible_score
        print(f"⚠️ Warning: Total score capped at maximum possible value")

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
            print(f"🌐 Open Source:          {min(os_score.score, category_maxes['open_source'])}/{os_score.max}")
            print(f"   Evidence: {os_score.evidence}\n")

        if hasattr(evaluation.scores, "self_projects") and evaluation.scores.self_projects:
            sp_score = evaluation.scores.self_projects
            print(f"🚀 Self Projects:        {min(sp_score.score, category_maxes['self_projects'])}/{sp_score.max}")
            print(f"   Evidence: {sp_score.evidence}\n")

        if hasattr(evaluation.scores, "production") and evaluation.scores.production:
            prod_score = evaluation.scores.production
            print(f"🏢 Production Experience: {min(prod_score.score, category_maxes['production'])}/{prod_score.max}")
            print(f"   Evidence: {prod_score.evidence}\n")

        if hasattr(evaluation.scores, "technical_skills") and evaluation.scores.technical_skills:
            tech_score = evaluation.scores.technical_skills
            print(f"💻 Technical Skills:     {min(tech_score.score, category_maxes['technical_skills'])}/{tech_score.max}")
            print(f"   Evidence: {tech_score.evidence}\n")

    if hasattr(evaluation, "bonus_points") and evaluation.bonus_points:
        print(f"\n⭐ BONUS POINTS: {evaluation.bonus_points.total}")
        print("-" * 30)
        print(f"   {evaluation.bonus_points.breakdown}")

    if hasattr(evaluation, "deductions") and evaluation.deductions and evaluation.deductions.total > 0:
        print(f"\n⚠️ DEDUCTIONS: -{evaluation.deductions.total}")
        print("-" * 30)
        if evaluation.deductions.reasons:
            print(f"   {evaluation.deductions.reasons}")

    if hasattr(evaluation, "key_strengths") and evaluation.key_strengths:
        print(f"\n✅ KEY STRENGTHS:")
        print("-" * 30)
        for i, strength in enumerate(evaluation.key_strengths, 1):
            print(f"  {i}. {strength}")

    if hasattr(evaluation, "areas_for_improvement") and evaluation.areas_for_improvement:
        print(f"\n🔧 AREAS FOR IMPROVEMENT:")
        print("-" * 30)
        for i, area in enumerate(evaluation.areas_for_improvement, 1):
            print(f"  {i}. {area}")

    print("\n" + "=" * 80)

# -----------------------------------------------------------------------------
# Resume Validation
# -----------------------------------------------------------------------------
def is_valid_resume(resume_data) -> bool:
    """Check if the extracted JSON contains meaningful resume data."""
    if not resume_data:
        return False
    if not hasattr(resume_data, "basics") or not resume_data.basics:
        return False
    if not getattr(resume_data.basics, "name", None) and not getattr(resume_data.basics, "email", None):
        return False
    return True

def is_resume_content_valid(resume_data: JSONResume) -> bool:
    """Check if the resume contains essential sections like experience, projects, skills."""
    if not resume_data:
        return False

    has_work = bool(getattr(resume_data, "work", []))
    has_projects = bool(getattr(resume_data, "projects", []))
    has_skills = bool(getattr(resume_data, "skills", []))

    return has_work or has_projects or has_skills

# -----------------------------------------------------------------------------
# Evaluation Logic (LLM call happens here)
# -----------------------------------------------------------------------------
def _evaluate_resume(
    resume_data: JSONResume, github_data: dict = None, blog_data: dict = None
) -> Optional[EvaluationData]:
    """Evaluate the resume using AI and display results."""

    # 🛑 Step 1: Sanity checks before invoking LLM
    if not resume_data:
        print("❌ Skipping evaluation: Resume data could not be extracted.")
        return None

    if not is_valid_resume(resume_data):
        print("❌ Skipping evaluation: Resume missing basic info (name/email).")
        return None

    if not is_resume_content_valid(resume_data):
        print("🚫 The uploaded PDF doesn’t look like a resume — missing sections such as Experience, Projects, or Skills.")
        return None

    # 🧩 Step 2: Prepare model
    model_params = MODEL_PARAMETERS.get(DEFAULT_MODEL)
    evaluator = ResumeEvaluator(model_name=DEFAULT_MODEL, model_params=model_params)

    # 🧠 Step 3: Convert JSON to text for model
    resume_text = convert_json_resume_to_text(resume_data)
    if github_data:
        resume_text += convert_github_data_to_text(github_data)
    if blog_data:
        resume_text += convert_blog_data_to_text(blog_data)

    # 🚀 Step 4: Call the LLM
    evaluation_result = evaluator.evaluate_resume(resume_text)
    return evaluation_result

# -----------------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------------
def find_profile(profiles, network):
    if not profiles:
        return None
    return next(
        (p for p in profiles if p.network and p.network.lower() == network.lower()),
        None,
    )

# -----------------------------------------------------------------------------
# Main Function
# -----------------------------------------------------------------------------
def main(pdf_path):
    if not is_pdf_valid(pdf_path):
        print(f"❌ Skipping '{pdf_path}': Invalid or corrupted PDF.")
        return

    cache_filename = f"cache/resumecache_{os.path.basename(pdf_path).replace('.pdf', '')}.json"
    github_cache_filename = f"cache/githubcache_{os.path.basename(pdf_path).replace('.pdf', '')}.json"

    if DEVELOPMENT_MODE and os.path.exists(cache_filename):
        print(f"Loading cached data from {cache_filename}")
        cached_data = json.loads(Path(cache_filename).read_text())
        resume_data = JSONResume(**cached_data)
    else:
        logger.debug("Extracting data from PDF...")
        pdf_handler = PDFHandler()
        resume_data = pdf_handler.extract_json_from_pdf(pdf_path)

        if resume_data is None:
            print(f"❌ No data could be extracted from {pdf_path}")
            return
        if not is_valid_resume(resume_data):
            print(f"❌ Skipping '{pdf_path}': Not a valid resume file.")
            return
        if not is_resume_content_valid(resume_data):
            print(f"🚫 Skipping '{pdf_path}': Missing essential sections like Experience, Projects, or Skills.")
            return

        if DEVELOPMENT_MODE:
            os.makedirs(os.path.dirname(cache_filename), exist_ok=True)
            Path(cache_filename).write_text(
                json.dumps(resume_data.model_dump(), indent=2, ensure_ascii=False)
            )

    github_data = {}
    if DEVELOPMENT_MODE and os.path.exists(github_cache_filename):
        print(f"Loading cached data from {github_cache_filename}")
        github_data = json.loads(Path(github_cache_filename).read_text())
    else:
        print(f"Fetching GitHub data and caching to {github_cache_filename}")
        profiles = getattr(resume_data.basics, "profiles", []) if resume_data and resume_data.basics else []
        github_profile = find_profile(profiles, "Github")

        if github_profile:
            github_data = fetch_and_display_github_info(github_profile.url)
        if DEVELOPMENT_MODE:
            os.makedirs(os.path.dirname(github_cache_filename), exist_ok=True)
            Path(github_cache_filename).write_text(json.dumps(github_data, indent=2, ensure_ascii=False))

    score = _evaluate_resume(resume_data, github_data)

    candidate_name = os.path.basename(pdf_path).replace(".pdf", "")
    if resume_data and hasattr(resume_data, "basics") and resume_data.basics and resume_data.basics.name:
        candidate_name = resume_data.basics.name

    print_evaluation_results(score, candidate_name)

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

# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python score.py <pdf_path>")
        exit(1)
    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"Error: File '{pdf_path}' does not exist.")
        exit(1)
    main(pdf_path)
