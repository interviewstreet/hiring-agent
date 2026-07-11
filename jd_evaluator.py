"""Role-general, JD-aware fit classification.

A modular addition to this fork: given a job description and a candidate's resume
(plus optional GitHub enrichment), it classifies how well the candidate fits THAT
role and returns the same contract Meritlab's built-in classifier uses, so the two
backends are interchangeable:

    {"tier": "strong_fit" | "possible_fit" | "weak_fit",
     "fit_score": 0-100,
     "evidence": {"met": [...], "unmet": [...], "rationale": "..."}}

It is a contextual LLM judgment against the JD, NOT keyword matching, and it never
uses or infers protected characteristics. It classifies; a human recruiter decides.

This module does not modify the HackerRank core (evaluator.py / score.py). It reuses
the provider seam (llm_utils.initialize_llm_provider, extract_json_from_response) and
the resume / GitHub parsing, importing the heavy pieces lazily so the pure formatting
and parsing can be tested with a stubbed provider and no model, PDF, or network.
"""
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

TIERS = ("strong_fit", "possible_fit", "weak_fit")
_FALLBACK_SCORE = {"strong_fit": 80, "possible_fit": 55, "weak_fit": 30}

SYSTEM_PROMPT = (
    "You are a fair hiring assistant. You classify how well a candidate fits a role "
    "using only job-related evidence in the job description and the candidate's resume "
    "and public work. Never use or infer age, gender, race, religion, national origin, "
    "disability, marital or family status, or any other protected characteristic. You "
    "classify, you never reject: a human recruiter makes every decision. Respond with "
    "JSON only."
)


def _default_model() -> str:
    from prompt import DEFAULT_MODEL

    return DEFAULT_MODEL


def _jd_block(jd: Dict[str, Any]) -> str:
    title = (jd or {}).get("title") or ""
    description = (jd or {}).get("description") or ""
    requirements = (jd or {}).get("requirements") or []
    parts = [f"ROLE: {title}"]
    if description:
        parts.append(f"DESCRIPTION:\n{description}")
    if requirements:
        parts.append("REQUIREMENTS:\n" + "\n".join(f"- {r}" for r in requirements))
    return "\n\n".join(parts)


def _github_block(github_data: Optional[Dict[str, Any]]) -> str:
    if not github_data:
        return ""
    # Keep it compact and job-relevant: languages, notable repos, contribution signal.
    try:
        return "CANDIDATE PUBLIC WORK (GitHub):\n" + json.dumps(github_data, default=str)[:4000]
    except (TypeError, ValueError):
        return ""


def build_prompt(jd: Dict[str, Any], resume_text: str, github_data: Optional[Dict[str, Any]] = None) -> str:
    """Assemble the JD-aware user prompt. Pure, so it is unit-testable."""
    blocks = [
        _jd_block(jd),
        "CANDIDATE RESUME:\n" + (resume_text or "").strip(),
        _github_block(github_data),
        (
            "Classify the candidate's fit for THIS role. Return JSON: "
            '{"tier": "strong_fit"|"possible_fit"|"weak_fit", "fit_score": 0-100, '
            '"evidence": {"met": [requirements clearly met], "unmet": [requirements not shown], '
            '"rationale": "2-3 sentences, job-related only"}}. '
            "strong_fit means the resume clearly evidences the core requirements; "
            "possible_fit means partial or unclear; weak_fit means little evidence of fit. "
            "Use only the information above."
        ),
    ]
    return "\n\n".join(b for b in blocks if b)


def _coerce(raw: str) -> Dict[str, Any]:
    """Parse and normalize the model's JSON into the fit contract."""
    from llm_utils import extract_json_from_response

    data = json.loads(extract_json_from_response(raw or ""))

    tier = data.get("tier")
    if tier not in TIERS:
        tier = "possible_fit"
    try:
        score = int(round(float(data.get("fit_score"))))
    except (TypeError, ValueError):
        score = _FALLBACK_SCORE[tier]
    score = max(0, min(100, score))

    ev = data.get("evidence") or {}
    evidence = {
        "met": [str(x) for x in (ev.get("met") or [])],
        "unmet": [str(x) for x in (ev.get("unmet") or [])],
        "rationale": str(ev.get("rationale") or ""),
    }
    return {"tier": tier, "fit_score": score, "evidence": evidence}


def classify_fit(
    jd: Dict[str, Any],
    resume_text: str,
    github_data: Optional[Dict[str, Any]] = None,
    model_name: Optional[str] = None,
    provider: Optional[Any] = None,
) -> Dict[str, Any]:
    """Classify a candidate's fit for a role. Returns {tier, fit_score, evidence}.

    ``provider`` is injectable so tests can stub the LLM; when omitted the repo's
    provider abstraction (Ollama / Gemini) is initialized.
    """
    model_name = model_name or _default_model()
    if provider is None:
        from llm_utils import initialize_llm_provider

        provider = initialize_llm_provider(model_name)

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_prompt(jd, resume_text, github_data)},
    ]
    response = provider.chat(
        model=model_name,
        messages=messages,
        options={"stream": False, "temperature": 0.2, "top_p": 0.9},
    )
    raw = response["message"]["content"]
    return _coerce(raw)


def extract_resume_text(pdf_path: str) -> Optional[str]:
    """Convenience: parse a resume PDF to text, reusing the fork's PDF handler.

    Imported lazily so callers that already have resume text (and this module's tests)
    do not need PyMuPDF.
    """
    from pdf import PDFHandler

    return PDFHandler().extract_text_from_pdf(pdf_path)


def fetch_github(github_url: str) -> Optional[Dict[str, Any]]:
    """Convenience: fetch public GitHub signal for a candidate, reusing github.py.

    Imported lazily and best-effort; returns None on any failure so classification
    never depends on GitHub being reachable.
    """
    try:
        from github import fetch_and_display_github_info

        return fetch_and_display_github_info(github_url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("GitHub enrichment failed for %s: %s", github_url, exc)
        return None
