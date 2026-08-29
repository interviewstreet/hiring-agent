from typing import Optional


def explain_score(category, score: float) -> Optional[dict]:
    """Return a deterministic explanation for a category score."""

    for band in category.explanation_bands:
        if band["min"] <= score <= band["max"]:
            return {
                "band": band["name"],
                "range": f"{band['min']:g}-{band['max']:g}",
                "description": band["description"],
                "improvement": band["improvement"],
            }

    return None