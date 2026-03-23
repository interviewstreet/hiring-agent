import os
import tempfile
import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from app.middleware.auth import verify_token
from score import main as evaluate_resume
from transform import transform_evaluation_response
from pdf import PDFHandler
from github import fetch_and_display_github_info
from leetcode import fetch_and_display_leetcode_info
from codeforces import fetch_and_display_codeforces_info
from score import (
    _evaluate_resume,
    find_profile,
    find_leetcode_profile,
    print_evaluation_results,
)
from config import DEVELOPMENT_MODE

import csv

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Resume Evaluation"])


@router.post("/evaluate-resume")
async def evaluate_resume_endpoint(
    file: UploadFile = File(...),
    _token: str = Depends(verify_token),
):
    """
    Upload a resume PDF for evaluation.

    Returns the analysis text along with all CSV parameters.
    Requires a valid Bearer token in the Authorization header.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # Save uploaded file to a temp location
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".pdf", prefix="resume_"
        ) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file.")

    try:
        # --- Run the full evaluation pipeline (mirrors score.py main) ---

        # 1. Extract JSON from PDF
        pdf_handler = PDFHandler()
        resume_data = pdf_handler.extract_json_from_pdf(tmp_path)

        if resume_data is None:
            raise HTTPException(
                status_code=422,
                detail="Failed to parse the resume PDF. Please ensure it is a valid resume.",
            )

        # 2. Fetch GitHub data
        github_data = {}
        profiles = []
        if resume_data and hasattr(resume_data, "basics") and resume_data.basics:
            profiles = resume_data.basics.profiles or []

        github_profile = find_profile(profiles, "Github")
        if github_profile:
            try:
                github_data = fetch_and_display_github_info(github_profile.url)
            except Exception as e:
                logger.warning(f"Failed to fetch GitHub data: {e}")

        # 3. Fetch LeetCode data
        leetcode_data = {}
        leetcode_profile = find_leetcode_profile(profiles, "Leetcode")
        if leetcode_profile:
            try:
                leetcode_data = fetch_and_display_leetcode_info(leetcode_profile)
                if not leetcode_data or "contest_rating" not in leetcode_data:
                    leetcode_data = None
            except Exception as e:
                logger.warning(f"Failed to fetch LeetCode data: {e}")
                leetcode_data = None
        else:
            leetcode_data = {"score": 0.0}

        # 4. Fetch Codeforces data
        codeforces_data = {}
        codeforces_profile = find_profile(profiles, "Codeforces")
        if codeforces_profile:
            try:
                codeforces_data = fetch_and_display_codeforces_info(
                    codeforces_profile.url
                )
            except Exception as e:
                logger.warning(f"Failed to fetch Codeforces data: {e}")
                codeforces_data = None

        # 5. Evaluate
        evaluation = _evaluate_resume(
            resume_data, github_data, None, leetcode_data, codeforces_data
        )

        if evaluation is None:
            raise HTTPException(
                status_code=500, detail="Evaluation failed. Please try again."
            )

        # 6. Build CSV row (includes UUID id)
        csv_row = transform_evaluation_response(
            file_name=file.filename,
            evaluation=evaluation,
            resume_data=resume_data,
            github_data=github_data,
            codeforces_data=codeforces_data,
        )

        # 7. Append to CSV file
        csv_path = "resume_evaluations.csv"
        file_exists = os.path.exists(csv_path)

        with open(csv_path, "a", newline="", encoding="utf-8") as csvfile:
            fieldnames = list(csv_row.keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(csv_row)

        # 8. Build the analysis text
        candidate_name = file.filename.replace(".pdf", "")
        if (
            resume_data
            and hasattr(resume_data, "basics")
            and resume_data.basics
            and resume_data.basics.name
        ):
            candidate_name = resume_data.basics.name

        analysis_lines = []
        analysis_lines.append(f"Resume Evaluation Results for: {candidate_name}")

        # Scores
        if hasattr(evaluation, "scores") and evaluation.scores:
            scores = evaluation.scores
            total_score = 0
            total_max = 0
            for cat_name, cat_data in scores.model_dump().items():
                capped = min(cat_data["score"], cat_data["max"])
                total_score += capped
                total_max += cat_data["max"]

            if hasattr(evaluation, "bonus_points") and evaluation.bonus_points:
                total_score += evaluation.bonus_points.total
            if hasattr(evaluation, "deductions") and evaluation.deductions:
                total_score -= evaluation.deductions.total

            analysis_lines.append(f"Overall Score: {total_score:.1f}/{total_max}")

        # Key strengths
        if hasattr(evaluation, "key_strengths") and evaluation.key_strengths:
            analysis_lines.append("Key Strengths: " + "; ".join(evaluation.key_strengths))

        # Areas for improvement
        if hasattr(evaluation, "areas_for_improvement") and evaluation.areas_for_improvement:
            analysis_lines.append(
                "Areas for Improvement: " + "; ".join(evaluation.areas_for_improvement)
            )

        analysis_text = "\n".join(analysis_lines)

        # 9. Return response
        return {
            "id": csv_row.get("id"),
            "analysis": analysis_text,
            "csv_data": csv_row,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during resume evaluation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"An error occurred during evaluation: {str(e)}"
        )
    finally:
        # Cleanup temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
