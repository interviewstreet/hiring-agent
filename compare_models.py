"""
Compare Candidate Resume Evaluation Scores across Different LLM Models
"""

import sys
import os
import json
import csv
from pathlib import Path
from typing import List, Dict
import pandas as pd

from score import _evaluate_resume, is_valid_resume_data, find_profile
from models import JSONResume, EvaluationData
from transform import transform_evaluation_response
from config import DEVELOPMENT_MODE

# Candidate Resumes available in cache
CANDIDATE_RESUMES = [
    "MadalaPranavsai_reume (3).pdf",
    "CHMadhu_Resume.pdf",
    "EchoMind_DevGlance_3.pdf",
    "resume_spyne.pdf",
]

# Models to compare
MODELS_TO_COMPARE = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
]

def load_cached_resume(pdf_path: str):
    cache_filename = f"cache/resumecache_{os.path.basename(pdf_path).replace('.pdf', '')}.json"
    github_cache_filename = f"cache/githubcache_{os.path.basename(pdf_path).replace('.pdf', '')}.json"

    resume_data = None
    if os.path.exists(cache_filename):
        try:
            cached_data = json.loads(Path(cache_filename).read_text(encoding="utf-8"))
            resume_data = JSONResume(**cached_data)
        except Exception as e:
            print(f"Error loading resume cache for {pdf_path}: {e}")

    if not resume_data and os.path.exists(pdf_path):
        print(f"Extracting resume data from PDF: {pdf_path}...")
        from pdf import PDFHandler
        pdf_handler = PDFHandler()
        resume_data = pdf_handler.extract_json_from_pdf(pdf_path)
        if resume_data and DEVELOPMENT_MODE:
            os.makedirs("cache", exist_ok=True)
            Path(cache_filename).write_text(
                json.dumps(resume_data.model_dump(), indent=2, ensure_ascii=False),
                encoding="utf-8"
            )

    github_data = {}
    if os.path.exists(github_cache_filename):
        try:
            github_data = json.loads(Path(github_cache_filename).read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Error loading github cache for {pdf_path}: {e}")
    elif resume_data and resume_data.basics and resume_data.basics.profiles:
        from github import fetch_and_display_github_info
        github_profile = find_profile(resume_data.basics.profiles, "Github")
        if github_profile:
            print(f"Fetching GitHub data for profile {github_profile.url}...")
            github_data = fetch_and_display_github_info(github_profile.url)
            if github_data and DEVELOPMENT_MODE:
                os.makedirs("cache", exist_ok=True)
                Path(github_cache_filename).write_text(
                    json.dumps(github_data, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )

    return resume_data, github_data

def run_model_comparison(pdf_path: str, models: List[str]):
    print("\n" + "=" * 90)
    print(f"🔍 MODEL EVALUATION COMPARISON FOR: {pdf_path}")
    print("=" * 90)

    from roles import load_role, DEFAULT_ROLE
    from models import build_evaluation_model

    role = DEFAULT_ROLE
    evaluation_model = build_evaluation_model(role)

    import json
    resume_data, github_data = load_cached_resume(pdf_path)
    if not resume_data:
        print(f"❌ Could not load cached resume data for {pdf_path}")
        return

    candidate_name = pdf_path.replace(".pdf", "")
    if resume_data.basics and resume_data.basics.name:
        candidate_name = resume_data.basics.name

    results = []

    for model in models:
        print(f"\n🔄 Running evaluation with model: {model} ...")
        try:
            score = _evaluate_resume(
                resume_data,
                role,
                evaluation_model,
                github_data,
                model_name=model,
            )
            if not score:
                print(f"❌ Failed to get evaluation for {model}")
                continue

            scores_dict = score.scores.model_dump() if hasattr(score, "scores") else {}
            os_score = scores_dict.get("open_source", {}).get("score", 0)
            sp_score = scores_dict.get("self_projects", {}).get("score", 0)
            prod_score = scores_dict.get("production", {}).get("score", 0)
            tech_score = scores_dict.get("technical_skills", {}).get("score", 0)
            
            bonus = score.bonus_points.total if hasattr(score, "bonus_points") and score.bonus_points else 0
            deductions = score.deductions.total if hasattr(score, "deductions") and score.deductions else 0
            
            total_raw = os_score + sp_score + prod_score + tech_score + bonus - deductions
            total_score = max(0.0, min(120.0, total_raw))

            res_dict = {
                "Candidate": candidate_name,
                "Model": model,
                "Open Source": os_score,
                "Self Projects": sp_score,
                "Production": prod_score,
                "Tech Skills": tech_score,
                "Bonus": bonus,
                "Deductions": deductions,
                "Total Score": round(total_score, 1),
            }
            results.append(res_dict)

            # Log to CSV
            csv_row = transform_evaluation_response(
                file_name=os.path.basename(pdf_path),
                evaluation=score,
                resume_data=resume_data,
                github_data=github_data,
                role=role,
            )
            csv_row["model_name"] = model
            
            csv_path = "resume_evaluations.csv"
            file_exists = os.path.exists(csv_path)
            with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=list(csv_row.keys()))
                if not file_exists:
                    writer.writeheader()
                writer.writerow(csv_row)

        except Exception as e:
            print(f"⚠️ Error with model {model}: {e}")

    df = pd.DataFrame(results)
    print("\n" + "=" * 90)
    print(f"📊 COMPARISON SUMMARY TABLE FOR {candidate_name.upper()}")
    print("=" * 90)
    print(df.to_string(index=False))
    print("=" * 90 + "\n")
    return df

if __name__ == "__main__":
    pdf_input = sys.argv[1] if len(sys.argv) > 1 else CANDIDATE_RESUMES[0]
    run_model_comparison(pdf_input, MODELS_TO_COMPARE)
