"""Replay synthetic responses to demonstrate checks, without LLM/network calls.

Run from the repository root: python -m examples.evidence_trace_demo
These cases test the validator; they do not measure model performance.
"""

import argparse
import json
from pathlib import Path

from evidence_trace import build_source_catalog, build_trace_report, write_trace_reports
from models import JSONResume, build_evaluation_model
from roles import Category, Role


def run_demo(output_directory):
    fixture = json.loads(
        Path(__file__)
        .with_name("evidence_trace_cases.json")
        .read_text(encoding="utf-8")
    )
    resume = JSONResume(**fixture["resume"])
    sources = build_source_catalog(resume)
    role = Role(
        name="synthetic_demo",
        position_title="Example engineer",
        categories=[Category("projects", "Projects", 30)],
        bonus_max=0,
        min_final_score=0,
        max_final_score=30,
        criteria_source="",
        system_message_source="",
    )
    model = build_evaluation_model(role, evidence_trace=True)
    results = []
    for case in fixture["cases"]:
        source_id = case.get("source_id") or next(
            source["id"]
            for source in sources.values()
            if source["section"] == case["section"]
        )
        citations = (
            []
            if case["quote"] is None
            else [{"source_id": source_id, "quote": case["quote"]}]
        )
        evaluation = model(
            scores={
                "projects": {
                    "score": 20,
                    "max": 30,
                    "evidence": case["explanation"],
                    "citations": citations,
                }
            },
            bonus_points={"total": 0, "breakdown": "No bonus"},
            deductions={"total": 0, "reasons": "None"},
            key_strengths=["Synthetic example"],
            areas_for_improvement=["Manual review required"],
        )
        report = build_trace_report(
            evaluation, role, sources, "synthetic-response-fixture"
        )
        report["fixture"] = {
            "name": case["name"],
            "manual_support_label": case["manual_support_label"],
        }
        category = report["categories"][0]
        status = (
            category["citations"][0]["status"]
            if category["citations"]
            else category["status"]
        )
        paths = write_trace_reports(report, Path(output_directory) / case["name"])
        results.append(
            {
                "case": case["name"],
                "actual_check": status,
                "expected_check": case["expected_check"],
                "passed": status == case["expected_check"],
                "manual_support_label": case["manual_support_label"],
            }
        )
        print(f"{case['name']}: {status} -> {paths[1]}")
    summary = {
        "kind": "offline synthetic validator cases, not a model benchmark",
        "cases": results,
        "passed": sum(result["passed"] for result in results),
        "total": len(results),
    }
    output = Path(output_directory) / "summary.json"
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{summary['passed']}/{summary['total']} expected checks matched")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="cache/evidence_trace_demo")
    args = parser.parse_args()
    result = run_demo(args.out)
    raise SystemExit(0 if result["passed"] == result["total"] else 1)
