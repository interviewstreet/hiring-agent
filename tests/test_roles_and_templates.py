import pytest
from models import build_bonus_model, build_evaluation_model
from prompts.template_manager import TemplateManager
from pydantic import ValidationError
from roles import list_available_roles, load_role


def test_software_engineering_intern_portfolio_criteria_matches_role_json():
    role = load_role("software_engineering_intern")
    template_manager = TemplateManager()

    # Find the portfolio rule in role.json
    portfolio_rule = next(
        (r for r in role.bonus_rules if r.get("key") == "portfolio"), None
    )
    assert portfolio_rule is not None, "portfolio rule must be defined in role.json"
    assert (
        "GitHub projects and competitive-programming profiles do not qualify"
        in portfolio_rule["description"]
    )

    # Render criteria
    rendered_criteria = template_manager.render_string(
        role.criteria_source, text_content="Sample resume text"
    )

    # Render system message
    rendered_system = template_manager.render_string(
        role.system_message_source,
        bonus_rules=role.bonus_rules,
        bonus_max=role.bonus_max,
    )
    assert "portfolio website" in rendered_system.lower()

    # Criteria must NOT instruct that a GitHub URL qualifies for the portfolio bonus
    assert "GitHub URL in basics.url" not in rendered_criteria, (
        "criteria.jinja contradicts role.json by stating '(GitHub URL in basics.url)' awards portfolio bonus"
    )

    # Criteria must NOT reference the internal JSON Resume property path 'basics.url'
    assert "basics.url" not in rendered_criteria, (
        "criteria.jinja references 'basics.url' which the evaluator LLM never sees"
    )

    # Criteria should clearly qualify personal portfolio website and state GitHub profiles do not qualify
    assert "portfolio website" in rendered_criteria.lower()
    assert (
        "GitHub profiles, repository links, and competitive-programming profiles do not qualify"
        in rendered_criteria
    )


def test_all_roles_load_and_render_cleanly():
    roles = list_available_roles()
    assert len(roles) > 0
    template_manager = TemplateManager()

    for role_name in roles:
        role = load_role(role_name)
        assert role.name == role_name
        assert role.bonus_max > 0
        assert len(role.categories) > 0

        # Verify template renders without syntax errors
        rendered_criteria = template_manager.render_string(
            role.criteria_source, text_content="Resume Content"
        )
        assert "Resume Content" in rendered_criteria

        rendered_system = template_manager.render_string(
            role.system_message_source,
            bonus_rules=role.bonus_rules,
            bonus_max=role.bonus_max,
        )
        assert len(rendered_system) > 0


def test_intern_role_evaluation_model_schema():
    role = load_role("software_engineering_intern")
    eval_model = build_evaluation_model(role)
    schema = eval_model.model_json_schema()

    # Check top-level properties
    assert "scores" in schema["properties"]
    assert "bonus_points" in schema["properties"]
    assert "deductions" in schema["properties"]
    assert "key_strengths" in schema["properties"]
    assert "areas_for_improvement" in schema["properties"]

    # Verify category fields in scores
    scores_def = schema["$defs"]["Scores"]
    expected_categories = {
        "open_source",
        "self_projects",
        "production",
        "technical_skills",
        "ai_fluency",
    }
    assert set(scores_def["properties"].keys()) == expected_categories


def test_bonus_points_validation_and_capping():
    role = load_role("software_engineering_intern")
    BonusModel = build_bonus_model(role)

    # Construct valid bonus items
    data = {
        "items": {
            "gsoc": {"points": 5, "evidence": "Contributed to CNCF in GSoC 2025"},
            "girl_script": {"points": 0, "evidence": "None"},
            "orchestrate": {
                "rank": 50,
                "points": 4,
                "evidence": "Rank 50 in Orchestrate",
            },
            "founder": {"points": 0, "evidence": "None"},
            "early_engineer": {"points": 0, "evidence": "None"},
            "portfolio": {
                "points": 2,
                "evidence": "Personal portfolio at https://portfolio.dev",
            },
            "linkedin": {"points": 1, "evidence": "LinkedIn profile found"},
            "technical_blogs": {"points": 0, "evidence": "None"},
        }
    }
    bonus_obj = BonusModel(**data)
    assert bonus_obj.total == 12  # 5 + 4 + 2 + 1
    assert "Subtotal: 12" in bonus_obj.breakdown

    # Invalid portfolio points (e.g. 3 instead of 0 or 2)
    invalid_data = {
        "items": {
            **data["items"],
            "portfolio": {"points": 3, "evidence": "Invalid points"},
        }
    }
    with pytest.raises(ValidationError):
        BonusModel(**invalid_data)
