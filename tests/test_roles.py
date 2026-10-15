"""Offline checks that every role's prompts agree with its role.json.

The criteria and system-message prompts restate each category's limits and the
bonus keys by hand, so they can drift from role.json without anything failing.
Run with: python -m unittest discover -s tests -v
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models import build_evaluation_model, gemini_compatible_schema  # noqa: E402
from prompts.template_manager import TemplateManager  # noqa: E402
from roles import list_available_roles, load_role  # noqa: E402

RESUME_TEXT = "RESUME TEXT PLACEHOLDER"


def walk(node):
    """Yield every dict in a JSON schema."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk(item)


class RoleTests(unittest.TestCase):
    def setUp(self):
        self.templates = TemplateManager(str(ROOT / "prompts" / "templates"))

    def roles(self):
        names = list_available_roles()
        self.assertIn("senior_software_engineer", names)
        for name in names:
            with self.subTest(role=name):
                yield load_role(name)

    def render(self, role):
        system = self.templates.render_string(
            role.system_message_source,
            bonus_rules=role.bonus_rules,
            bonus_max=role.bonus_max,
        )
        criteria = self.templates.render_string(
            role.criteria_source, text_content=RESUME_TEXT
        )
        return system, criteria

    def test_prompts_state_each_category_limit(self):
        for role in self.roles():
            system, criteria = self.render(role)
            for category in role.categories:
                limit = f"{category.key}: 0-{category.max} points"
                self.assertIn(limit, system)
                self.assertIn(limit, criteria)
                self.assertIn(
                    f'"{category.key}": {{"score": 0, "max": {category.max},', criteria
                )

    def test_prompts_state_the_bonus_cap_and_every_bonus_key(self):
        for role in self.roles():
            system, criteria = self.render(role)
            self.assertIn(f"must be <= {role.bonus_max}", system)
            self.assertIn(f"Maximum total: {role.bonus_max} points", criteria)
            for rule in role.bonus_rules:
                self.assertIn(rule["label"], system)
                self.assertIn(f'"{rule["key"]}": {{', criteria)

    def test_criteria_ends_with_the_resume(self):
        for role in self.roles():
            _, criteria = self.render(role)
            self.assertTrue(criteria.rstrip().endswith(RESUME_TEXT))

    def test_category_maxima_add_up_to_the_final_score_bounds(self):
        for role in self.roles():
            self.assertEqual(
                role.max_final_score,
                sum(category.max for category in role.categories) + role.bonus_max,
            )

    def test_evaluation_schema_is_gemini_compatible(self):
        for role in self.roles():
            schema = gemini_compatible_schema(
                build_evaluation_model(role).model_json_schema()
            )
            for node in walk(schema):
                self.assertNotIn("$ref", node)
                self.assertNotIn("additionalProperties", node)


if __name__ == "__main__":
    unittest.main()
