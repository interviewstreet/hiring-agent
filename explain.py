"""
Deterministic, rubric-based explanations for evaluation scores.

This module does NOT call the LLM. It maps each category score produced by the
evaluator onto the scoring bands defined in
`prompts/templates/resume_evaluation_criteria.jinja`, so the output explains
*why* a score lands where it does ("which band, and what that band means") and
*how to improve it* ("what the next band up requires") strictly according to the
current scoring algorithm. The numbers themselves are still an LLM judgment; this
only makes the rubric mapping transparent.
"""

from typing import List, Optional

# Each band: (min_inclusive, max_inclusive, name, description).
# Ordered high -> low. Bands are contiguous so every score 0..max maps to one.
RUBRIC = {
    "open_source": {
        "label": "🌐 Open Source",
        "max": 35,
        "bands": [
            (
                25,
                35,
                "HIGH",
                "Contributions to popular OSS (1000+ stars), significant/sustained "
                "contributions, GSoC, substantial community involvement",
            ),
            (
                15,
                24,
                "MEDIUM",
                "Contributions to smaller OSS projects; meaningful contributions to "
                "other people's repositories",
            ),
            (
                5,
                14,
                "LOW",
                "Only personal repositories; minimal open-source activity",
            ),
            (
                0,
                4,
                "VERY LOW",
                "No GitHub presence, or only very basic personal repositories",
            ),
        ],
        "to_max": "Make sustained, substantial contributions across multiple "
        "well-known projects (1000+ stars). Note: personal repos do not count as "
        "open source — contributing to other people's projects does.",
    },
    "self_projects": {
        "label": "🚀 Self Projects",
        "max": 30,
        "bands": [
            (
                20,
                30,
                "HIGH",
                "Complex projects with real-world impact, advanced architecture, "
                "multiple technologies, or user adoption",
            ),
            (
                10,
                19,
                "MEDIUM",
                "Projects with some complexity, good documentation, multiple features",
            ),
            (
                1,
                9,
                "LOW",
                "Simple tutorial projects (todo, calculator, basic CRUD), classroom "
                "assignments, minimal complexity",
            ),
            (0, 0, "ZERO", "No projects, or only extremely basic ones"),
        ],
        "to_max": "Ship complex, original projects with live demos and clear "
        "real-world impact; always include working links (missing links cut scores "
        "30-50%).",
    },
    "production": {
        "label": "🏢 Production Experience",
        "max": 25,
        "bands": [
            (
                18,
                25,
                "HIGH",
                "Significant production/internship experience with measurable, "
                "real-world impact; founder/early-stage roles",
            ),
            (
                10,
                17,
                "MEDIUM",
                "Some internship or work experience with production exposure",
            ),
            (
                1,
                9,
                "LOW",
                "Limited or indirect production experience",
            ),
            (0, 0, "ZERO", "No work/volunteer/production experience"),
        ],
        "to_max": "Add internship/production work with quantified impact (latency, "
        "MTTR, revenue, users). Founder/co-founder or first-10-20-employee roles "
        "score highest.",
    },
    "technical_skills": {
        "label": "💻 Technical Skills",
        "max": 10,
        "bands": [
            (
                8,
                10,
                "HIGH",
                "Broad modern stack plus demonstrated problem-solving in projects, "
                "work, or competitions",
            ),
            (
                5,
                7,
                "MEDIUM",
                "Solid set of core languages and tools",
            ),
            (
                1,
                4,
                "LOW",
                "Limited or narrow skill set",
            ),
            (0, 0, "ZERO", "No demonstrable technical skills"),
        ],
        "to_max": "Demonstrate technical breadth across languages/frameworks AND "
        "back it with evidence of problem-solving (not just a skills list).",
    },
}


def _find_band(category: str, score: float):
    """Return (index, band tuple) for the band a (capped) score falls into."""
    bands = RUBRIC[category]["bands"]
    capped = max(0, min(int(round(score)), RUBRIC[category]["max"]))
    for i, band in enumerate(bands):
        low, high = band[0], band[1]
        if low <= capped <= high:
            return i, band
    # Fallback: lowest band.
    return len(bands) - 1, bands[-1]


def explain_category(category: str, score: float, evidence: Optional[str]) -> List[str]:
    """Build the explanation lines for a single category score."""
    spec = RUBRIC[category]
    bands = spec["bands"]
    idx, band = _find_band(category, score)
    _, _, band_name, band_desc = band

    capped = max(0, min(int(round(score)), spec["max"]))
    lines = [
        f"{spec['label']}: {capped}/{spec['max']}  [{band_name} band: {band[0]}-{band[1]}]",
        f"   Why: scored in the {band_name} band — {band_desc}.",
    ]
    if evidence:
        lines.append(f'   Model evidence: "{evidence.strip()}"')

    if idx == 0:
        # Already in the top band: explain how to push toward the maximum.
        lines.append(f"   To improve: {spec['to_max']}")
    else:
        higher = bands[idx - 1]
        lines.append(
            f"   To improve: reach the {higher[2]} band ({higher[0]}-{higher[1]}) — {higher[3]}."
        )
    return lines


def print_score_explanations(evaluation) -> None:
    """Print a deterministic 'why + how to improve' breakdown for each category."""
    scores = getattr(evaluation, "scores", None)
    if not scores:
        return

    print("\n" + "=" * 80)
    print("🧭 WHY THESE SCORES & HOW TO IMPROVE (rubric-based, not LLM)")
    print("=" * 80)

    for category in ("open_source", "self_projects", "production", "technical_skills"):
        cat = getattr(scores, category, None)
        if not cat:
            continue
        evidence = getattr(cat, "evidence", None)
        for line in explain_category(category, cat.score, evidence):
            print(line)
        print()

    # Surface the model's own improvement notes, clearly labelled as LLM-generated.
    areas = getattr(evaluation, "areas_for_improvement", None)
    if areas:
        print("📝 Model-suggested areas for improvement:")
        for i, area in enumerate(areas, 1):
            print(f"   {i}. {area}")
        print()
