"""FastAPI classification service for Meritlab.

Wraps the JD-aware evaluator (jd_evaluator.classify_fit) in an async HTTP service so
Meritlab can request a richer, GitHub-aware fit classification without blocking. This
is a SEPARATE deployment: it is never added to Meritlab's docker-compose and it does
not modify the HackerRank core (evaluator.py / score.py).

Flow: Meritlab POSTs /classify (authenticated with X-Internal-Key). We return a
job_id immediately and run the classification in the background. When it finishes we
POST the result to the caller's callback_url with a signed header, and we also keep
it for GET /classify/{job_id} as a poll fallback.

Signed callback (Meritlab mirrors this to verify):
  X-Meritlab-Timestamp: <unix seconds>
  X-Meritlab-Signature: sha256=<hexdigest>
where hexdigest = HMAC-SHA256(CALLBACK_SIGNING_SECRET, f"{timestamp}.".encode() + raw_body).
The timestamp is signed too, so a receiver can reject a stale callback (> 5 minutes).

The job store is in-memory, which is fine for a single instance. A multi-instance
deployment should back JOBS with a shared store (e.g. Redis); that is left as a seam.
"""
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

import httpx
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from pydantic import BaseModel

import jd_evaluator

logger = logging.getLogger(__name__)

app = FastAPI(title="Meritlab classification service", version="1.0.0")

# job_id -> {status: queued|ready|failed, result?, error?, reference_id?}
JOBS: Dict[str, Dict[str, Any]] = {}

CALLBACK_TIMEOUT_SECONDS = 10


class JobDescription(BaseModel):
    title: str = ""
    description: str = ""
    requirements: List[str] = []


class ClassifyRequest(BaseModel):
    jd: JobDescription
    resume_text: Optional[str] = None
    resume_pdf_path: Optional[str] = None
    github_url: Optional[str] = None
    callback_url: Optional[str] = None
    reference_id: Optional[str] = None


def _require_internal_key(x_internal_key: Optional[str]) -> None:
    """Reject any request whose X-Internal-Key does not match the configured key.

    Read at request time (not import) so config/tests can set it. Fails closed: with
    no key configured, every request is rejected.
    """
    expected = os.environ.get("INTERNAL_API_KEY", "")
    if not expected or not x_internal_key or not hmac.compare_digest(x_internal_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing internal key")


def sign_payload(body: bytes, timestamp: str, secret: str) -> str:
    """HMAC-SHA256 over ``f"{timestamp}." + body``. Shared by the service and Meritlab."""
    message = f"{timestamp}.".encode() + body
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def _http_post(url: str, content: bytes, headers: Dict[str, str]) -> None:
    """Send the signed callback. Isolated so tests can stub the network."""
    with httpx.Client(timeout=CALLBACK_TIMEOUT_SECONDS) as client:
        client.post(url, content=content, headers=headers)


def _post_callback(url: str, payload: Dict[str, Any]) -> None:
    """Sign and POST a completed job to the caller. Best-effort; never raises out."""
    secret = os.environ.get("CALLBACK_SIGNING_SECRET", "")
    body = json.dumps(payload, default=str).encode()
    timestamp = str(int(time.time()))
    signature = sign_payload(body, timestamp, secret)
    headers = {
        "Content-Type": "application/json",
        "X-Meritlab-Timestamp": timestamp,
        "X-Meritlab-Signature": f"sha256={signature}",
    }
    _http_post(url, body, headers)


def _run_job(job_id: str, req: ClassifyRequest) -> None:
    """Classify one application, store the result, and fire the signed callback."""
    try:
        resume_text = req.resume_text
        if not resume_text and req.resume_pdf_path:
            resume_text = jd_evaluator.extract_resume_text(req.resume_pdf_path)
        github_data = jd_evaluator.fetch_github(req.github_url) if req.github_url else None
        result = jd_evaluator.classify_fit(req.jd.model_dump(), resume_text or "", github_data)
        JOBS[job_id] = {"status": "ready", "result": result, "reference_id": req.reference_id}
    except Exception as exc:  # noqa: BLE001
        logger.error("Classification job %s failed: %s", job_id, exc, exc_info=True)
        JOBS[job_id] = {"status": "failed", "error": str(exc), "reference_id": req.reference_id}

    if req.callback_url:
        try:
            _post_callback(req.callback_url, {"job_id": job_id, **JOBS[job_id]})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Callback to %s for job %s failed: %s", req.callback_url, job_id, exc)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/classify")
def classify(
    req: ClassifyRequest,
    background: BackgroundTasks,
    x_internal_key: Optional[str] = Header(default=None),
) -> Dict[str, str]:
    _require_internal_key(x_internal_key)
    job_id = uuid.uuid4().hex
    JOBS[job_id] = {"status": "queued", "reference_id": req.reference_id}
    background.add_task(_run_job, job_id, req)
    return {"job_id": job_id, "status": "queued"}


@app.get("/classify/{job_id}")
def get_job(job_id: str, x_internal_key: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    _require_internal_key(x_internal_key)
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return {"job_id": job_id, **job}
