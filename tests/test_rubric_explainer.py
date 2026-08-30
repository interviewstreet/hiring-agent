import json

import roles
from roles import load_role
from rubric_explainer import explain_score


class FakeCategory:
    def __init__(self, explanation_bands):
        self.explanation_bands = explanation_bands


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


def test_category_remains_hashable():
    category = get_open_source_category()

    assert hash(category) is not None


def test_explanation_mapping_is_independent_of_band_order():
    category = FakeCategory(
        [
            {"name": "HIGH", "min": 25, "max": 35,
             "description": "high", "improvement": "improve"},
            {"name": "VERY LOW", "min": 0, "max": 4,
             "description": "very low", "improvement": "improve"},
            {"name": "MEDIUM", "min": 15, "max": 24,
             "description": "medium", "improvement": "improve"},
            {"name": "LOW", "min": 5, "max": 10,
             "description": "low", "improvement": "improve"},
        ]
    )

    assert explain_score(category, 25)["band"] == "HIGH"


def test_invalid_bands_are_ignored():
    category = FakeCategory(
        [
            None,
            "invalid",
            {"name": "BROKEN"},
            {"name": "HIGH", "min": 25, "max": 35,
             "description": "high", "improvement": "improve"},
        ]
    )

    assert explain_score(category, 25)["band"] == "HIGH"


def test_invalid_band_fields_are_ignored():
    category = FakeCategory(
        [
            {
                "name": "INVALID",
                "min": "25",
                "max": 35,
                "description": "invalid",
                "improvement": "invalid",
            },
            {
                "name": "MISSING",
                "min": 25,
                "max": 35,
            },
            {
                "name": "HIGH",
                "min": 25,
                "max": 35,
                "description": "high",
                "improvement": "improve",
            },
        ]
    )

    assert explain_score(category, 25)["band"] == "HIGH"


def test_non_list_explanation_bands_are_normalized(tmp_path, monkeypatch):
    role_dir = tmp_path / "null_bands"
    role_dir.mkdir()
    (role_dir / "role.json").write_text(
        json.dumps(
            {
                "position_title": "Test Role",
                "categories": [
                    {"key": "test", "label": "Test", "max": 10,
                     "explanation_bands": None}
                ],
                "bonus_max": 0,
                "min_final_score": 0,
                "max_final_score": 10,
            }
        ),
        encoding="utf-8",
    )
    (role_dir / "criteria.jinja").write_text("criteria", encoding="utf-8")
    (role_dir / "system_message.jinja").write_text("system", encoding="utf-8")
    monkeypatch.setattr(roles, "ROLES_DIR", tmp_path)

    role = load_role("null_bands")

    assert role.categories[0].explanation_bands == ()
