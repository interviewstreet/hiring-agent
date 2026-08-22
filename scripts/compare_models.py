"""Compare scoring models on the same resume: level, spread, latency, cost.

Answers "which model should I score with?" with measurements rather than spec
sheets. The published critiques of this project found a 66-99 range across 100
runs of one unchanged resume, so a single run per model would be meaningless.

Runs only the scoring call (stage 6), reusing the cached resume + GitHub payload,
so each iteration is exactly one LLM call against identical input. That isolates
the scorer's own stochasticity from extraction jitter.

Usage:
    python scripts/compare_models.py <pdf_path> --role <role> [--runs N] [--models a,b]
"""

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import MODEL_PARAMETERS  # noqa: E402
from evaluator import ResumeEvaluator  # noqa: E402
from models import JSONResume, build_evaluation_model  # noqa: E402
from roles import load_role  # noqa: E402
from transform import (  # noqa: E402
    convert_github_data_to_text,
    convert_json_resume_to_text,
)

# Per-1M-token USD, us-east-1 on-demand. Used only for a relative cost estimate;
# override with BEDROCK_PRICING_JSON if these drift.
PRICING = {
    "us.anthropic.claude-opus-5": (15.00, 75.00),
    "us.anthropic.claude-opus-4-8": (15.00, 75.00),
    "us.anthropic.claude-sonnet-5": (3.00, 15.00),
    "us.anthropic.claude-sonnet-4-6": (3.00, 15.00),
    "us.anthropic.claude-sonnet-4-5-20250929-v1:0": (3.00, 15.00),
    "us.anthropic.claude-haiku-4-5-20251001-v1:0": (1.00, 5.00),
    "amazon.nova-pro-v1:0": (0.80, 3.20),
}


def load_cached_inputs(pdf_path):
    """Rebuild the exact resume_text the scorer would receive, from cache."""
    base = os.path.basename(pdf_path).replace(".pdf", "")
    resume_cache = Path("cache") / f"resumecache_{base}.json"
    github_cache = Path("cache") / f"githubcache_{base}.json"
    if not resume_cache.exists():
        sys.exit(
            f"No resume cache at {resume_cache}. Run score.py on this PDF once "
            f"first so the extraction is cached."
        )
    resume_data = JSONResume(**json.loads(resume_cache.read_text()))
    text = convert_json_resume_to_text(resume_data)
    if github_cache.exists():
        text += convert_github_data_to_text(json.loads(github_cache.read_text()))
    return text


def score_once(model, role, evaluation_model, resume_text):
    """One scoring call. Returns (breakdown, elapsed_s, usage) or raises."""
    evaluator = ResumeEvaluator(
        role=role,
        evaluation_model=evaluation_model,
        model_name=model,
        model_params=MODEL_PARAMETERS.get(model),
    )
    start = time.time()
    result = evaluator.evaluate_resume(resume_text)
    elapsed = time.time() - start

    per_cat = {}
    for cat in role.categories:
        cs = getattr(result.scores, cat.key)
        # Cap against the ROLE's max, not the model's self-reported max, which is
        # unbounded in the shipped schema (models.py CategoryScore.max = gt=0).
        per_cat[cat.key] = min(cs.score, cat.max)
    total = sum(per_cat.values()) + result.bonus_points.total - result.deductions.total
    per_cat["_bonus"] = result.bonus_points.total
    per_cat["_deductions"] = result.deductions.total
    per_cat["_total"] = total
    return per_cat, elapsed


def summarize(values):
    if not values:
        return "-"
    if len(values) == 1:
        return f"{values[0]:.0f}"
    lo, hi = min(values), max(values)
    med = statistics.median(values)
    spread = hi - lo
    return f"{med:.0f} [{lo:.0f}-{hi:.0f}] ±{spread:.0f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pdf_path")
    ap.add_argument("--role", required=True)
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument(
        "--models",
        default=",".join(m for m in PRICING if m.startswith("us.anthropic")),
        help="Comma-separated model ids (must exist in providers.json).",
    )
    args = ap.parse_args()

    role = load_role(args.role)
    evaluation_model = build_evaluation_model(role)
    resume_text = load_cached_inputs(args.pdf_path)
    models = [m.strip() for m in args.models.split(",") if m.strip()]

    print(
        f"\nresume_text: {len(resume_text)} chars | role: {role.name} | runs: {args.runs}"
    )
    print(f"categories: " + ", ".join(f"{c.key}(max {c.max})" for c in role.categories))

    results = {}
    for model in models:
        print(f"\n── {model}")
        print(f"   params sent: {MODEL_PARAMETERS.get(model)}")
        runs, times, failures = [], [], 0
        for i in range(args.runs):
            try:
                per_cat, elapsed = score_once(
                    model, role, evaluation_model, resume_text
                )
                runs.append(per_cat)
                times.append(elapsed)
                print(
                    f"   run {i+1}: total={per_cat['_total']:.0f}  "
                    + "  ".join(
                        f"{c.key.split('_')[0]}={per_cat[c.key]:.0f}"
                        for c in role.categories
                    )
                    + f"  bonus={per_cat['_bonus']:.0f}  ({elapsed:.1f}s)"
                )
            except Exception as exc:
                failures += 1
                print(f"   run {i+1}: FAILED {type(exc).__name__}: {str(exc)[:110]}")
        if runs:
            results[model] = {"runs": runs, "times": times, "failures": failures}

    if not results:
        sys.exit("\nNo model produced a result.")

    keys = [c.key for c in role.categories] + ["_bonus", "_total"]
    print("\n" + "=" * 100)
    print("MEDIAN [min-max] ±spread   —   lower spread = more usable for ranking")
    print("=" * 100)
    header = f"{'model':46s}" + "".join(f"{k.replace('_',''):>17s}" for k in keys)
    print(header)
    print("-" * len(header))
    for model, data in results.items():
        row = f"{model:46s}"
        for k in keys:
            row += f"{summarize([r[k] for r in data['runs']]):>17s}"
        print(row)

    print("\n" + "=" * 100)
    print(f"{'model':46s}{'ok/att':>10s}{'med latency':>14s}{'total spread':>15s}")
    print("-" * 85)
    for model, data in results.items():
        totals = [r["_total"] for r in data["runs"]]
        spread = (max(totals) - min(totals)) if len(totals) > 1 else 0
        print(
            f"{model:46s}"
            f"{len(data['runs'])}/{len(data['runs'])+data['failures']:>9}"
            f"{statistics.median(data['times']):>13.1f}s"
            f"{spread:>14.0f}"
        )

    print(
        "\nNote: totals are computed against the ROLE's category maxima, not the "
        "model's\nself-reported `max` field, which the shipped scorer trusts "
        "(score.py:68,70)."
    )


if __name__ == "__main__":
    main()
