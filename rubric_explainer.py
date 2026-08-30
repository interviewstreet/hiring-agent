from math import isfinite
from typing import Optional


def explain_score(category, score: float) -> Optional[dict]:
    """Return a deterministic explanation for a category score."""

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

        lower = band["min"]
        upper = band["max"]

        if (
            isinstance(lower, bool)
            or isinstance(upper, bool)
            or not isinstance(lower, (int, float))
            or not isinstance(upper, (int, float))
            or not isfinite(lower)
            or not isfinite(upper)
        ):
            continue

        bands.append(band)

    bands.sort(key=lambda band: (band["min"], band["max"]))

    for band in bands:
        if band["min"] <= score <= band["max"]:
            return {
                "band": band["name"],
                "range": f"{band['min']:g}-{band['max']:g}",
                "description": band["description"],
                "improvement": band["improvement"],
            }

    return None