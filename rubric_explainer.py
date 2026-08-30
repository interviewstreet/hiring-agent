from math import isfinite
from typing import Optional


def explain_score(category, score: float) -> Optional[dict]:
    """Return a deterministic explanation for a category score."""

    if (
        isinstance(score, bool)
        or not isinstance(score, (int, float))
        or not isfinite(score)
    ):
        return None

    bands = []

    for band in category.explanation_bands:
        if not isinstance(band, dict):
            continue

        required_keys = (
            "name",
            "min",
            "max",
            "description",
            "improvement",
        )

        if not all(key in band for key in required_keys):
            continue

        name = band["name"]
        lower = band["min"]
        upper = band["max"]

        if (
            not isinstance(name, str)
            or isinstance(lower, bool)
            or isinstance(upper, bool)
            or not isinstance(lower, (int, float))
            or not isinstance(upper, (int, float))
            or not isfinite(lower)
            or not isfinite(upper)
            or lower > upper
        ):
            continue

        bands.append(band)

    bands.sort(
        key=lambda band: (
            band["min"],
            band["max"],
            band["name"],
        )
    )

    for band in bands:
        if band["min"] <= score <= band["max"]:
            return {
                "band": band["name"],
                "range": f"{band['min']:g}-{band['max']:g}",
                "description": band["description"],
                "improvement": band["improvement"],
            }

    return None