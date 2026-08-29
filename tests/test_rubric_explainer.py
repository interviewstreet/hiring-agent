from roles import load_role
from rubric_explainer import explain_score


def get_open_source_category():
    role = load_role("software_engineering_intern")

    return next(
        category
        for category in role.categories
        if category.key == "open_source"
    )


def test_open_source_boundaries():
    category = get_open_source_category()

    assert explain_score(category, 0)["band"] == "VERY LOW"
    assert explain_score(category, 4)["band"] == "VERY LOW"
    assert explain_score(category, 5)["band"] == "LOW"
    assert explain_score(category, 10)["band"] == "LOW"
    assert explain_score(category, 15)["band"] == "MEDIUM"
    assert explain_score(category, 24)["band"] == "MEDIUM"
    assert explain_score(category, 25)["band"] == "HIGH"
    assert explain_score(category, 35)["band"] == "HIGH"


def test_unmapped_score_returns_none():
    category = get_open_source_category()

    assert explain_score(category, 12) is None


def test_category_without_bands_returns_none():
    role = load_role("software_engineering_intern")

    category = next(
        category
        for category in role.categories
        if category.key == "technical_skills"
    )

    assert explain_score(category, 8) is None


def test_role_loads_explanation_bands():
    category = get_open_source_category()

    assert len(category.explanation_bands) == 4