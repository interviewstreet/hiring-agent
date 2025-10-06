"""
FastAPI HTTP API for Hiring Agent scoring (PDF only)

Endpoints:
 - POST /score/pdf  -> multipart form upload: file field named 'file'
 - GET /health -> simple health check

Example curl (PDF upload):

curl -X POST http://localhost:8000/score/pdf \
  -F "file=@/path/to/resume.pdf" \
  -H "Accept: application/json"

Run locally with uvicorn:
  uvicorn api:app --host 0.0.0.0 --port 8000 --reload

"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import os
import logging

from pdf import PDFHandler
from models import JSONResume
from github import fetch_and_display_github_info
from score import _evaluate_resume
from config import DEVELOPMENT_MODE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Hiring Agent Scoring API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/score/pdf")
async def score_pdf(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="empty filename")

    # Save to a temporary location
    tmpdir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmpdir, file.filename)
    try:
        with open(tmp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        pdf_handler = PDFHandler()
        resume_data = pdf_handler.extract_json_from_pdf(tmp_path)

        if resume_data is None:
            raise HTTPException(status_code=500, detail="failed to extract resume from PDF")

        # Attempt to fetch GitHub data if present
        github_data = {}
        try:
            profiles = []
            if resume_data and getattr(resume_data, "basics", None):
                profiles = resume_data.basics.profiles or []

            github_profile = None
            for p in profiles:
                if p.network and p.network.lower() == "github":
                    github_profile = p
                    break

            if github_profile:
                github_data = fetch_and_display_github_info(github_profile.url)
        except Exception:
            logger.exception("Error fetching GitHub data")

        evaluation = _evaluate_resume(resume_data, github_data)

        if evaluation is None:
            raise HTTPException(status_code=500, detail="evaluation failed")

        return JSONResponse(content=evaluation.model_dump())

    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            os.rmdir(tmpdir)
        except Exception:
            pass
