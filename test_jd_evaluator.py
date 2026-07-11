"""Standalone test for the JD-aware fit classifier (run: python test_jd_evaluator.py).

Hermetic: the LLM provider is stubbed (its .chat returns canned JSON), so no model,
PDF, or network is touched. Asserts a strong resume classifies strong_fit with met
evidence, a weak resume classifies weak_fit with unmet evidence, the prompt is
JD-aware, and the parser is robust to fenced JSON, a bad tier, and an out-of-range
score.
"""
import sys

import jd_evaluator as J

JD = {
    "title": "Senior Python Engineer",
    "description": "Build and scale our API platform.",
    "requirements": ["5+ years Python", "Postgres", "Distributed systems"],
}
STRONG_RESUME = "8 years building Python services on Postgres and distributed systems at scale."
WEAK_RESUME = "Recent graduate, some HTML and a class project in Java."


class StubProvider:
    """A provider whose chat() returns whatever JSON text it was constructed with,
    and records the messages it was called with so the prompt can be inspected."""

    def __init__(self, content):
        self.content = content
        self.last_messages = None

    def chat(self, model, messages, options=None, **kwargs):
        self.last_messages = messages
        return {"message": {"role": "assistant", "content": self.content}}


def _content(tier, score, met, unmet, rationale="ok"):
    import json

    return json.dumps({"tier": tier, "fit_score": score, "evidence": {"met": met, "unmet": unmet, "rationale": rationale}})


def main():
    # Strong candidate.
    p = StubProvider(_content("strong_fit", 88, ["5+ years Python"], []))
    r = J.classify_fit(JD, STRONG_RESUME, provider=p)
    user_prompt = p.last_messages[1]["content"]
    assert "Senior Python Engineer" in user_prompt, "prompt must be JD-aware (role present)"
    assert "5+ years Python" in user_prompt, "prompt must include the requirements"
    assert STRONG_RESUME in user_prompt, "prompt must include the resume text"
    assert r["tier"] == "strong_fit" and r["fit_score"] == 88, f"strong: {r}"
    assert "5+ years Python" in r["evidence"]["met"], f"strong evidence: {r['evidence']}"
    assert p.last_messages[0]["role"] == "system", "a system message forbids protected characteristics"
    print("[PASS] strong resume -> strong_fit with met evidence, prompt is JD-aware")

    # Weak candidate.
    p = StubProvider(_content("weak_fit", 22, [], ["5+ years Python", "Distributed systems"]))
    r = J.classify_fit(JD, WEAK_RESUME, provider=p)
    assert r["tier"] == "weak_fit" and r["fit_score"] == 22, f"weak: {r}"
    assert "5+ years Python" in r["evidence"]["unmet"], f"weak evidence: {r['evidence']}"
    print("[PASS] weak resume -> weak_fit with unmet requirements")

    # GitHub enrichment reaches the prompt.
    p = StubProvider(_content("possible_fit", 60, [], []))
    J.classify_fit(JD, STRONG_RESUME, github_data={"languages": ["Python", "Go"]}, provider=p)
    assert "GitHub" in p.last_messages[1]["content"], "github_data should reach the prompt"
    print("[PASS] GitHub enrichment is included in the prompt when provided")

    # Robust parse: fenced JSON, bad tier defaults, score clamps, evidence normalized.
    p = StubProvider('```json\n{"tier": "bogus", "fit_score": 150, "evidence": {}}\n```')
    r = J.classify_fit(JD, STRONG_RESUME, provider=p)
    assert r["tier"] == "possible_fit", f"bad tier should default: {r}"
    assert r["fit_score"] == 100, f"score should clamp to 100: {r}"
    assert r["evidence"] == {"met": [], "unmet": [], "rationale": ""}, f"evidence normalized: {r['evidence']}"
    print("[PASS] robust parse: fenced JSON, bad tier defaults, score clamped, evidence normalized")

    print("RESULT: PASS")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"[FAIL] {exc}")
        print("RESULT: FAIL")
        sys.exit(1)
