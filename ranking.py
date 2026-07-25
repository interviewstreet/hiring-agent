"""Percentile ranking and cutoff helpers for batch scoring."""

from __future__ import annotations

from typing import Dict, List, Tuple


def _parse_score(row: dict, score_key: str) -> float:
    value = row.get(score_key, "N/A")
    if value in (None, "", "N/A"):
        return float("-inf")
    return float(value)


def add_percentile_ranks(rows: List[dict], score_key: str = "final_score") -> List[dict]:
    if not rows:
        return rows

    scored = []
    for index, row in enumerate(rows):
        scored.append((index, _parse_score(row, score_key)))

    valid_scores = [score for _, score in scored if score != float("-inf")]
    if not valid_scores:
        for row in rows:
            row["rank"] = "N/A"
            row["percentile"] = "N/A"
            row["passes_cutoff"] = "N/A"
        return rows

    sorted_scores = sorted(valid_scores)
    n = len(sorted_scores)

    for index, score in scored:
        if score == float("-inf"):
            rows[index]["rank"] = "N/A"
            rows[index]["percentile"] = "N/A"
            rows[index]["passes_cutoff"] = False
            continue

        rank = sum(1 for value in sorted_scores if value > score) + 1
        percentile = round(100 * (n - rank) / max(n - 1, 1), 1)
        rows[index]["rank"] = rank
        rows[index]["percentile"] = percentile
        rows[index]["passes_cutoff"] = True

    return rows


def apply_cutoff(
    rows: List[dict], cutoff_percentile: float, score_key: str = "final_score"
) -> Tuple[List[dict], List[dict]]:
    """Split rows; bottom `cutoff_percentile` percent fail (e.g. 15 → bottom 15%)."""
    ranked = add_percentile_ranks(rows, score_key=score_key)
    passed: List[dict] = []
    failed: List[dict] = []

    for row in ranked:
        percentile = row.get("percentile", "N/A")
        if percentile == "N/A":
            row["passes_cutoff"] = False
            failed.append(row)
            continue

        if float(percentile) <= cutoff_percentile:
            row["passes_cutoff"] = False
            failed.append(row)
        else:
            row["passes_cutoff"] = True
            passed.append(row)

    return passed, failed
