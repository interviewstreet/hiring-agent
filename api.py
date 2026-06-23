"""
FastAPI wrapper for the Hiring Agent CLI.

Exposes the resume evaluation pipeline as a REST API.
Accepts a PDF file upload and returns structured evaluation results.
"""

import os
import tempfile
import logging

from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from pdf import PDFHandler
from github import fetch_and_display_github_info
from models import EvaluationData
from score import _evaluate_resume, is_valid_resume_data, find_profile
from prompt import DEFAULT_MODEL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)5s - %(lineno)5d - %(funcName)33s - %(levelname)5s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Hiring Agent API",
    description="Resume evaluation pipeline exposed as a REST API.",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class CategoryScoreResponse(BaseModel):
    score: float
    max: int
    evidence: str


class ScoresResponse(BaseModel):
    open_source: CategoryScoreResponse
    self_projects: CategoryScoreResponse
    production: CategoryScoreResponse
    technical_skills: CategoryScoreResponse


class BonusPointsResponse(BaseModel):
    total: float
    breakdown: str


class DeductionsResponse(BaseModel):
    total: float
    reasons: str


class EvaluationResponse(BaseModel):
    candidate_name: str
    evaluation: Dict[str, Any]
    resume_data: Optional[Dict[str, Any]] = None
    github_data: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@app.post(
    "/api/v1/evaluate",
    response_model=EvaluationResponse,
    summary="Evaluate a resume PDF",
    description="Upload a resume PDF to receive a structured evaluation with scores, evidence, strengths, and areas for improvement.",
)
async def evaluate_resume(file: UploadFile = File(..., description="Resume PDF file")):
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # Read file bytes and write to temp file (PyMuPDF requires a path)
    try:
        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        with tempfile.NamedTemporaryFile(
            suffix=".pdf", delete=False, dir=tempfile.gettempdir()
        ) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to process uploaded file.")

    try:
        # --- Step 1: Parse PDF into structured JSON Resume ---
        pdf_handler = PDFHandler()
        resume_data = pdf_handler.extract_json_from_pdf(tmp_path)

        if resume_data is None:
            raise HTTPException(
                status_code=422,
                detail="Failed to extract resume data from the uploaded PDF.",
            )

        if not is_valid_resume_data(resume_data):
            raise HTTPException(
                status_code=422,
                detail="Extracted resume data contains no usable content.",
            )

        # --- Step 2: GitHub enrichment (if a GitHub profile is in the resume) ---
        github_data: Dict[str, Any] = {}
        profiles = (
            resume_data.basics.profiles if resume_data and resume_data.basics else []
        ) or []
        github_profile = find_profile(profiles, "Github")

        if github_profile:
            logger.info(f"Fetching GitHub data for {github_profile.url}")
            github_data = fetch_and_display_github_info(github_profile.url) or {}

        # --- Step 3: Evaluate the resume ---
        evaluation = _evaluate_resume(resume_data, github_data)

        if evaluation is None:
            raise HTTPException(
                status_code=500,
                detail="Evaluation failed. The LLM provider may be unavailable.",
            )

        # --- Step 4: Build response ---
        candidate_name = "Candidate"
        if (
            resume_data
            and hasattr(resume_data, "basics")
            and resume_data.basics
            and resume_data.basics.name
        ):
            candidate_name = resume_data.basics.name

        # Calculate overall score (mirrors score.py logic)
        total_score = 0.0
        max_score = 0
        if evaluation and evaluation.scores:
            for cat_name, cat_data in evaluation.scores.model_dump().items():
                capped = min(cat_data["score"], cat_data["max"])
                total_score += capped
                max_score += cat_data["max"]
        if evaluation and evaluation.bonus_points:
            total_score += evaluation.bonus_points.total
        if evaluation and evaluation.deductions:
            total_score -= evaluation.deductions.total
        max_possible = max_score + 20
        if total_score > max_possible:
            total_score = float(max_possible)

        evaluation_dict = {
            "overall_score": round(total_score, 1),
            "max_score": max_score,
            "scores": evaluation.scores.model_dump() if evaluation.scores else {},
            "bonus_points": (
                evaluation.bonus_points.model_dump()
                if evaluation.bonus_points
                else {}
            ),
            "deductions": (
                evaluation.deductions.model_dump() if evaluation.deductions else {}
            ),
            "key_strengths": evaluation.key_strengths or [],
            "areas_for_improvement": evaluation.areas_for_improvement or [],
        }

        return EvaluationResponse(
            candidate_name=candidate_name,
            evaluation=evaluation_dict,
            resume_data=resume_data.model_dump() if resume_data else None,
            github_data=github_data if github_data else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Evaluation pipeline failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation pipeline failed: {str(e)}",
        )
    finally:
        # Clean up temp file
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except Exception:
            pass


@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/v1/models")
async def list_models():
    from prompt import MODEL_PROVIDER_MAPPING, MODEL_PARAMETERS

    return {
        "default_model": DEFAULT_MODEL,
        "available_models": list(MODEL_PARAMETERS.keys()),
        "provider_mapping": {
            k: v.value for k, v in MODEL_PROVIDER_MAPPING.items()
        },
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")
    uvicorn.run("api:app", host=host, port=port, reload=True)
