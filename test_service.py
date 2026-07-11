"""Standalone test for the FastAPI classification service (run: python test_service.py).

Hermetic: jd_evaluator.classify_fit is stubbed (no model) and the outbound callback
poster is stubbed to capture the request (no network). Uses FastAPI's TestClient,
which runs the background task before the request returns. Asserts auth, the job
lifecycle, and that the callback carries a valid, fresh HMAC signature that a receiver
(Meritlab) can independently verify.
"""
import hashlib
import hmac
import os
import sys
import time

os.environ["INTERNAL_API_KEY"] = "test-internal-key"
os.environ["CALLBACK_SIGNING_SECRET"] = "test-callback-secret"

from fastapi.testclient import TestClient  # noqa: E402

import service  # noqa: E402

CANNED = {
    "tier": "strong_fit",
    "fit_score": 91,
    "evidence": {"met": ["5+ years Python"], "unmet": [], "rationale": "Strong match"},
}
CAPTURED = []


def _fake_classify(jd, resume_text, github_data=None, model_name=None, provider=None):
    return CANNED


def _fake_http_post(url, content, headers):
    CAPTURED.append({"url": url, "content": content, "headers": headers})


def _verify_signature(content: bytes, headers: dict, secret: str) -> bool:
    sig_header = headers.get("X-Meritlab-Signature", "")
    ts = headers.get("X-Meritlab-Timestamp", "")
    if not sig_header.startswith("sha256=") or not ts:
        return False
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + content, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig_header[len("sha256="):], expected)


def main():
    service.jd_evaluator.classify_fit = _fake_classify
    service._http_post = _fake_http_post
    client = TestClient(service.app)

    body = {
        "jd": {"title": "Senior Python Engineer", "description": "APIs", "requirements": ["5+ years Python"]},
        "resume_text": "8 years of Python and Postgres.",
        "callback_url": "https://meritlab.test/callback",
        "reference_id": "app-123",
    }

    # Auth: no key is rejected.
    r = client.post("/classify", json=body)
    assert r.status_code == 401, f"missing key must be 401, got {r.status_code}"
    print("[PASS] POST /classify without X-Internal-Key -> 401")

    # With the key: queued + job_id, and the background task runs (TestClient awaits it).
    r = client.post("/classify", json=body, headers={"X-Internal-Key": "test-internal-key"})
    assert r.status_code == 200, f"classify: {r.status_code} {r.text[:160]}"
    job_id = r.json()["job_id"]
    assert job_id, f"expected a job_id: {r.json()}"
    print("[PASS] POST /classify with the key -> 200 + job_id")

    # Poll fallback returns the stored result.
    r = client.get(f"/classify/{job_id}", headers={"X-Internal-Key": "test-internal-key"})
    assert r.status_code == 200, f"get job: {r.status_code}"
    job = r.json()
    assert job["status"] == "ready", f"job should be ready: {job}"
    assert job["result"] == CANNED, f"job result mismatch: {job['result']}"
    assert job["reference_id"] == "app-123", f"reference_id not carried: {job}"
    print("[PASS] GET /classify/{job_id} -> ready with the fit result and reference_id")

    # The callback fired exactly once, with a valid, fresh signature.
    assert len(CAPTURED) == 1, f"expected one callback, got {len(CAPTURED)}"
    cb = CAPTURED[0]
    assert cb["url"] == "https://meritlab.test/callback", f"callback url: {cb['url']}"
    assert _verify_signature(cb["content"], cb["headers"], "test-callback-secret"), "signature must verify"
    # A wrong secret must NOT verify (proves the signature is real, not a constant).
    assert not _verify_signature(cb["content"], cb["headers"], "wrong-secret"), "wrong secret must not verify"
    skew = abs(time.time() - int(cb["headers"]["X-Meritlab-Timestamp"]))
    assert skew < 60, f"timestamp should be fresh, skew {skew}s"
    print("[PASS] callback carries a valid, fresh HMAC signature; a wrong secret fails")

    # Unknown job -> 404.
    r = client.get("/classify/does-not-exist", headers={"X-Internal-Key": "test-internal-key"})
    assert r.status_code == 404, f"unknown job should be 404, got {r.status_code}"
    print("[PASS] GET /classify/{unknown} -> 404")

    print("RESULT: PASS")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"[FAIL] {exc}")
        print("RESULT: FAIL")
        sys.exit(1)
