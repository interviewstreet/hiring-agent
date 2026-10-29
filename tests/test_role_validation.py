import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from pathlib import Path
from roles import _validate_role_name, scaffold_role, load_role, list_available_roles


def test_validate_role_name_valid():
    # Valid names should pass without exception
    _validate_role_name("backend-engineer")
    _validate_role_name("intern")
    _validate_role_name("role_123")


@pytest.mark.parametrize("invalid_name", [
    "",
    "   ",
    None,
    "../evil",
    "../../etc/passwd",
    "roles/nested",
    "foo/bar",
    "foo\\bar",
    "/absolute/path",
])
def test_validate_role_name_invalid(invalid_name):
    with pytest.raises(ValueError, match="path traversal|non-empty string"):
        _validate_role_name(invalid_name)


def test_scaffold_role_rejects_path_traversal():
    with pytest.raises(ValueError, match="path traversal|non-empty string"):
        scaffold_role("../evil_scaffold")


def test_load_role_rejects_path_traversal():
    with pytest.raises(ValueError, match="path traversal|non-empty string"):
        load_role("../evil_role")


def test_load_role_handles_null_optional_fields(tmp_path, monkeypatch):
    import roles
    import json

    monkeypatch.setattr(roles, "ROLES_DIR", tmp_path)

    test_role_dir = tmp_path / "custom-role"
    test_role_dir.mkdir()

    manifest = {
        "position_title": "Custom Engineer",
        "categories": [
            {"key": "cat1", "label": "Category 1", "max": 40}
        ],
        "bonus_max": None,
        "min_final_score": None,
        "max_final_score": None,
        "bonus_rules": None,
    }
    (test_role_dir / "role.json").write_text(json.dumps(manifest), encoding="utf-8")
    (test_role_dir / "criteria.jinja").write_text("criteria", encoding="utf-8")
    (test_role_dir / "system_message.jinja").write_text("system message", encoding="utf-8")

    role = load_role("custom-role")
    assert role.name == "custom-role"
    assert role.bonus_max == 20
    assert role.min_final_score == 0
    assert role.max_final_score == 60  # 40 + 20
    assert role.bonus_rules == []


def test_load_existing_roles():
    available = list_available_roles()
    assert len(available) > 0
    for name in available:
        role = load_role(name)
        assert role.name == name
        assert len(role.categories) > 0
        assert isinstance(role.bonus_rules, list)
