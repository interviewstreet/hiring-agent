"""Batch score and rank multiple resume PDFs."""

from __future__ import annotations

import argparse
import csv
import glob
import os
import sys

from config import BATCH_CUTOFF_PERCENTILE
from ranking import add_percentile_ranks, apply_cutoff
from score import score_resume


def _write_csv(rows: list[dict], output_path: str):
    if not rows:
        print("No rows to write.")
        return

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _print_rank_summary(rows: list[dict], cutoff: float):
    print("\n📋 BATCH RANKING SUMMARY")
    print("-" * 80)
    sorted_rows = sorted(
        rows,
        key=lambda row: float(row.get("final_score", float("-inf")))
        if row.get("final_score") not in (None, "", "N/A")
        else float("-inf"),
        reverse=True,
    )
    for row in sorted_rows[:20]:
        name = row.get("file_name", row.get("candidate_name", "unknown"))
        print(
            f"  rank={row.get('rank', 'N/A')} "
            f"score={row.get('final_score', 'N/A')} "
            f"percentile={row.get('percentile', 'N/A')} "
            f"passes={row.get('passes_cutoff', 'N/A')} "
            f"{name}"
        )
    passed = sum(1 for row in rows if row.get("passes_cutoff") is True)
    failed = sum(1 for row in rows if row.get("passes_cutoff") is False)
    print(f"\nCutoff bottom {cutoff}%: passed={passed}, failed={failed}")


def rank_existing_csv(input_path: str, cutoff: float, output_path: str):
    with open(input_path, newline="", encoding="utf-8") as csvfile:
        rows = list(csv.DictReader(csvfile))

    add_percentile_ranks(rows, score_key="final_score")
    passed, failed = apply_cutoff(rows, cutoff, score_key="final_score")
    _write_csv(rows, output_path)
    _print_rank_summary(rows, cutoff)
    print(f"\nWrote ranked CSV to {output_path} ({len(passed)} passed, {len(failed)} failed)")


def score_directory(input_dir: str, cutoff: float, output_path: str):
    pdf_paths = sorted(glob.glob(os.path.join(input_dir, "*.pdf")))
    if not pdf_paths:
        print(f"No PDF files found in {input_dir}")
        return

    rows = []
    for pdf_path in pdf_paths:
        print(f"\n{'=' * 80}\nScoring: {pdf_path}\n{'=' * 80}")
        result = score_resume(pdf_path, write_csv=False)
        if result is None:
            continue

        from transform import transform_evaluation_response

        row = transform_evaluation_response(
            file_name=os.path.basename(pdf_path),
            evaluation=result.validated.evaluation,
            validated=result.validated,
            resume_data=result.resume_data,
            github_data=result.github_data,
            writing_quality=result.writing_quality,
            blog_data=result.blog_data or None,
            pdf_integrity=result.pdf_integrity,
        )
        if result.resume_data.basics and result.resume_data.basics.name:
            row["candidate_name"] = result.resume_data.basics.name
        rows.append(row)

    add_percentile_ranks(rows, score_key="final_score")
    apply_cutoff(rows, cutoff, score_key="final_score")
    _write_csv(rows, output_path)
    _print_rank_summary(rows, cutoff)
    print(f"\nWrote batch results to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Batch score and rank resume PDFs")
    parser.add_argument("input", nargs="?", help="Directory of PDFs or omitted with --rank-only")
    parser.add_argument("--output", default="ranked_resumes.csv", help="Output CSV path")
    parser.add_argument(
        "--cutoff",
        type=float,
        default=BATCH_CUTOFF_PERCENTILE,
        help="Bottom percentile to filter out (default from BATCH_CUTOFF_PERCENTILE)",
    )
    parser.add_argument(
        "--rank-only",
        metavar="CSV",
        help="Re-rank an existing CSV without re-scoring",
    )
    args = parser.parse_args()

    if args.rank_only:
        rank_existing_csv(args.rank_only, args.cutoff, args.output)
        return

    if not args.input:
        parser.error("input directory required unless --rank-only is used")

    if not os.path.isdir(args.input):
        print(f"Error: '{args.input}' is not a directory.")
        sys.exit(1)

    score_directory(args.input, args.cutoff, args.output)


if __name__ == "__main__":
    main()
