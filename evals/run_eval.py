"""Run the hiring agent over the golden dataset and report agreement metrics.

Usage (from the repo root):

    python -m evals.run_eval                        # run the seed dataset
    python -m evals.run_eval --repeat 3 --out report.json
    python -m evals.run_eval --filter strong_oss_heavy
    LLM_PROVIDER=gemini DEFAULT_MODEL=gemini-2.0-flash python -m evals.run_eval

The evaluator backend is whatever LLM_PROVIDER / DEFAULT_MODEL select, so
comparing models is just an environment change.
"""

import argparse
import glob
import json
import os
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

# Allow running as a plain script (python evals/run_eval.py) by putting the
# repo root on the path.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from pydantic import BaseModel

from models import JSONResume, EvaluationData
from score_utils import aggregate_scores
from evals import metrics

DEFAULT_GOLDEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden")

# evaluate_fn(resume, github) -> EvaluationData
EvaluateFn = Callable[[JSONResume, Optional[dict]], EvaluationData]


# --------------------------------------------------------------------------- #
# Golden case schema
# --------------------------------------------------------------------------- #


class CategoryRange(BaseModel):
    min: float
    max: float


class GoldenLabels(BaseModel):
    overall_band: str  # "strong" | "medium" | "weak"
    categories: Dict[str, CategoryRange]
    rationale: Optional[str] = None


class GoldenCase(BaseModel):
    id: str
    description: Optional[str] = None
    resume: dict
    github: Optional[dict] = None
    labels: GoldenLabels


def load_cases(golden_dir: str = DEFAULT_GOLDEN_DIR) -> List[GoldenCase]:
    """Load and validate every ``*.json`` golden case in a directory."""
    cases: List[GoldenCase] = []
    for path in sorted(glob.glob(os.path.join(golden_dir, "*.json"))):
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        try:
            cases.append(GoldenCase(**raw))
        except Exception as e:  # noqa: BLE001 - surface which file is malformed
            raise ValueError(f"Invalid golden case in {path}: {e}") from e
    return cases


# --------------------------------------------------------------------------- #
# Default evaluator (lazily imports the heavy pipeline)
# --------------------------------------------------------------------------- #


def _default_evaluate_fn(resume: JSONResume, github: Optional[dict]) -> EvaluationData:
    # Imported lazily so tests (which inject a fake) never pull PyMuPDF/ollama.
    from score import _evaluate_resume

    return _evaluate_resume(resume, github or {})


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #


@dataclass
class _CaseRun:
    totals: List[float]
    per_category_runs: List[Dict[str, float]]


def _evaluate_case(case: GoldenCase, evaluate_fn: EvaluateFn, repeat: int) -> _CaseRun:
    resume = JSONResume(**case.resume)
    totals: List[float] = []
    per_category_runs: List[Dict[str, float]] = []
    for _ in range(repeat):
        evaluation = evaluate_fn(resume, case.github)
        agg = aggregate_scores(evaluation)
        totals.append(agg.total)
        per_category_runs.append(agg.per_category)
    return _CaseRun(totals=totals, per_category_runs=per_category_runs)


def _mean_categories(runs: List[Dict[str, float]]) -> Dict[str, float]:
    keys = runs[0].keys()
    return {k: statistics.fmean(r[k] for r in runs) for k in keys}


def run(
    cases: List[GoldenCase],
    evaluate_fn: EvaluateFn = _default_evaluate_fn,
    repeat: int = 1,
    thresholds: Optional[Dict[str, float]] = None,
) -> dict:
    """Score every case, then compute per-case and summary metrics."""
    case_reports: List[dict] = []
    summarize_input: List[dict] = []
    stdevs: List[float] = []

    for case in cases:
        run_result = _evaluate_case(case, evaluate_fn, repeat)
        mean_total = statistics.fmean(run_result.totals)
        mean_categories = _mean_categories(run_result.per_category_runs)
        total_stdev = (
            statistics.stdev(run_result.totals) if len(run_result.totals) > 1 else 0.0
        )
        stdevs.append(total_stdev)

        gold_categories = {
            cat: {"min": rng.min, "max": rng.max}
            for cat, rng in case.labels.categories.items()
        }
        predicted_band = metrics.score_to_band(mean_total, thresholds)

        per_cat_detail = {}
        all_within = True
        for cat, rng in gold_categories.items():
            score = mean_categories.get(cat)
            if score is None:
                continue
            m = metrics.category_range_metrics(score, rng["min"], rng["max"])
            per_cat_detail[cat] = {"score": score, **m}
            all_within = all_within and m["within"]

        case_reports.append(
            {
                "id": case.id,
                "gold_band": case.labels.overall_band,
                "predicted_band": predicted_band,
                "band_correct": predicted_band == case.labels.overall_band,
                "agent_total": mean_total,
                "total_stdev": total_stdev,
                "agent_categories": mean_categories,
                "categories": per_cat_detail,
                "all_within_range": all_within,
            }
        )
        summarize_input.append(
            {
                "id": case.id,
                "gold_band": case.labels.overall_band,
                "gold_categories": gold_categories,
                "agent_total": mean_total,
                "agent_categories": mean_categories,
            }
        )

    summary = metrics.summarize(summarize_input, thresholds)
    summary["stability"] = {
        "mean_total_stdev": statistics.fmean(stdevs) if stdevs else 0.0,
        "max_total_stdev": max(stdevs) if stdevs else 0.0,
    }

    return {
        "metadata": {
            "provider": os.getenv("LLM_PROVIDER", "ollama"),
            "model": os.getenv("DEFAULT_MODEL", "gemma3:4b"),
            "n_cases": len(cases),
            "repeat": repeat,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "summary": summary,
        "cases": case_reports,
    }


def write_report(report: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _print_report(report: dict) -> None:
    meta = report["metadata"]
    summary = report["summary"]
    print("\n" + "=" * 78)
    print("GOLDEN DATASET EVALUATION")
    print("=" * 78)
    print(f"Provider/Model : {meta['provider']} / {meta['model']}")
    print(f"Cases          : {meta['n_cases']}   Repeats/case: {meta['repeat']}")
    print("-" * 78)
    print(f"{'id':<28}{'gold':<8}{'pred':<8}{'total':>8}  within-range")
    print("-" * 78)
    for c in report["cases"]:
        mark = "ok" if c["band_correct"] else "MISS"
        within = "yes" if c["all_within_range"] else "no"
        print(
            f"{c['id']:<28}{c['gold_band']:<8}{c['predicted_band']:<8}"
            f"{c['agent_total']:>8.1f}  {within} [{mark}]"
        )
    print("-" * 78)
    band = summary["band"]
    print(f"Band exact accuracy   : {band['exact_accuracy']:.2%}")
    print(f"Band within-one rate  : {band['within_one_rate']:.2%}")
    print(f"Overall within-range  : {summary['overall_within_range_rate']:.2%}")
    rho = summary["rank_correlation_spearman"]
    print(f"Rank corr (Spearman)  : {'n/a' if rho is None else f'{rho:.3f}'}")
    if meta["repeat"] > 1:
        print(f"Mean total stdev      : {summary['stability']['mean_total_stdev']:.2f}")
    print("\nPer-category:")
    for cat, m in summary["categories"].items():
        print(
            f"  {cat:<18} within {m['within_range_rate']:.0%}  "
            f"bias {m['mean_signed_midpoint_error']:+.1f}  "
            f"mean-miss {m['mean_out_of_range_distance']:.1f}"
        )
    print("=" * 78 + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate the hiring agent against the golden dataset."
    )
    parser.add_argument(
        "--golden-dir",
        default=DEFAULT_GOLDEN_DIR,
        help="Directory of golden *.json cases.",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Runs per case (averages to smooth LLM noise).",
    )
    parser.add_argument(
        "--filter", default=None, help="Only run the case with this id."
    )
    parser.add_argument(
        "--out", default=None, help="Write the JSON report to this path."
    )
    parser.add_argument(
        "--min-band-accuracy",
        type=float,
        default=None,
        help="Exit non-zero if band exact accuracy is below this (0..1).",
    )
    args = parser.parse_args(argv)

    cases = load_cases(args.golden_dir)
    if args.filter:
        cases = [c for c in cases if c.id == args.filter]
    if not cases:
        print("No golden cases found.", file=sys.stderr)
        return 1

    report = run(cases, repeat=args.repeat)
    _print_report(report)

    if args.out:
        write_report(report, args.out)
        print(f"Report written to {args.out}")

    if args.min_band_accuracy is not None:
        acc = report["summary"]["band"]["exact_accuracy"]
        if acc < args.min_band_accuracy:
            print(
                f"FAIL: band accuracy {acc:.2%} < threshold {args.min_band_accuracy:.2%}",
                file=sys.stderr,
            )
            return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
