"""Pure metric functions for the golden-dataset evaluation.

Every function here is deterministic and free of I/O, LLM calls, and heavy
dependencies, so the whole module is unit-testable offline.
"""

from typing import Dict, List, Optional, Sequence

# Bands in ascending quality order. Used for ordinal comparisons.
BAND_ORDER: Dict[str, int] = {"weak": 0, "medium": 1, "strong": 2}

# Lower bound (inclusive) of each band on the 0..120 total scale.
# strong >= 70, medium >= 40, else weak.
DEFAULT_BAND_THRESHOLDS: Dict[str, float] = {"strong": 70, "medium": 40}


def score_to_band(total: float, thresholds: Optional[Dict[str, float]] = None) -> str:
    """Bucket a numeric total into a band using inclusive lower thresholds."""
    t = thresholds or DEFAULT_BAND_THRESHOLDS
    if total >= t["strong"]:
        return "strong"
    if total >= t["medium"]:
        return "medium"
    return "weak"


def category_range_metrics(score: float, lo: float, hi: float) -> Dict[str, float]:
    """Compare a single category score against its golden ``[lo, hi]`` range.

    Returns whether it is within range, how far outside it fell (0 if inside),
    and the signed error relative to the range midpoint (bias/calibration).
    """
    within = lo <= score <= hi
    if score < lo:
        out_of_range_distance = lo - score
    elif score > hi:
        out_of_range_distance = score - hi
    else:
        out_of_range_distance = 0.0
    midpoint = (lo + hi) / 2.0
    return {
        "within": within,
        "out_of_range_distance": out_of_range_distance,
        "signed_midpoint_error": score - midpoint,
    }


def _rank(values: Sequence[float]) -> List[float]:
    """Return fractional (average) ranks, handling ties."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0  # 1-based average rank for the tie group
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return None
    return cov / ((var_x**0.5) * (var_y**0.5))


def spearman(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    """Spearman rank correlation. Returns None when undefined (n < 2 or no variance)."""
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    r = _pearson(_rank(xs), _rank(ys))
    if r is None:
        return None
    # Clamp and round away floating-point noise (e.g. 0.9999999999999998).
    return round(max(-1.0, min(1.0, r)), 6)


def summarize(cases: List[dict], thresholds: Optional[Dict[str, float]] = None) -> dict:
    """Aggregate per-case results into summary agreement metrics.

    Each item in ``cases`` is a dict with keys:
      ``id``, ``gold_band``, ``gold_categories`` ({cat: {"min", "max"}}),
      ``agent_total`` (float), ``agent_categories`` ({cat: score}).
    """
    thresholds = thresholds or DEFAULT_BAND_THRESHOLDS
    n = len(cases)

    predicted_bands: Dict[str, str] = {}
    band_exact = 0
    band_within_one = 0
    confusion: Dict[str, Dict[str, int]] = {
        g: {p: 0 for p in BAND_ORDER} for g in BAND_ORDER
    }

    # Per-category accumulators.
    cat_names: List[str] = []
    cat_within: Dict[str, int] = {}
    cat_out_dist: Dict[str, float] = {}
    cat_signed: Dict[str, float] = {}
    cat_count: Dict[str, int] = {}

    overall_within = 0
    overall_cat_count = 0

    totals_for_rank: List[float] = []
    gold_ordinals_for_rank: List[float] = []

    for case in cases:
        pred = score_to_band(case["agent_total"], thresholds)
        gold = case["gold_band"]
        predicted_bands[case["id"]] = pred

        confusion[gold][pred] += 1
        if pred == gold:
            band_exact += 1
        if abs(BAND_ORDER[pred] - BAND_ORDER[gold]) <= 1:
            band_within_one += 1

        totals_for_rank.append(case["agent_total"])
        gold_ordinals_for_rank.append(BAND_ORDER[gold])

        for cat, rng in case["gold_categories"].items():
            score = case["agent_categories"].get(cat)
            if score is None:
                continue
            if cat not in cat_count:
                cat_names.append(cat)
                cat_within[cat] = 0
                cat_out_dist[cat] = 0.0
                cat_signed[cat] = 0.0
                cat_count[cat] = 0
            m = category_range_metrics(score, rng["min"], rng["max"])
            cat_count[cat] += 1
            if m["within"]:
                cat_within[cat] += 1
                overall_within += 1
            cat_out_dist[cat] += m["out_of_range_distance"]
            cat_signed[cat] += m["signed_midpoint_error"]
            overall_cat_count += 1

    categories = {
        cat: {
            "within_range_rate": cat_within[cat] / cat_count[cat],
            "mean_out_of_range_distance": cat_out_dist[cat] / cat_count[cat],
            "mean_signed_midpoint_error": cat_signed[cat] / cat_count[cat],
            "n": cat_count[cat],
        }
        for cat in cat_names
    }

    return {
        "n_cases": n,
        "band": {
            "exact_accuracy": band_exact / n if n else 0.0,
            "within_one_rate": band_within_one / n if n else 0.0,
            "confusion": confusion,
        },
        "categories": categories,
        "overall_within_range_rate": (
            overall_within / overall_cat_count if overall_cat_count else 0.0
        ),
        "rank_correlation_spearman": spearman(totals_for_rank, gold_ordinals_for_rank),
        "predicted_bands": predicted_bands,
    }
