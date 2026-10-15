"""Offline checks for the structured-output schema sent to Gemini models.

Through OpenRouter, Gemini answered every bonus item with {} when the schema had
$ref, additionalProperties: false and integer enums, and the evaluation failed
validation. Run with: python -m unittest discover -s tests -v
"""

from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models import (  # noqa: E402
    OpenAICompatibleProvider,
    build_evaluation_model,
    gemini_compatible_schema,
)
from roles import load_role  # noqa: E402

ROLE = load_role("software_engineering_intern")


def walk(node):
    """Yield every dict in a JSON schema."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk(item)


def evaluation_schema():
    return build_evaluation_model(ROLE).model_json_schema()


def bonus_answer(**overrides):
    items = {
        rule["key"]: {"points": 0, "evidence": "Not evidenced."}
        for rule in ROLE.bonus_rules
    }
    items["orchestrate"]["rank"] = None
    items.update(overrides)
    category = {"score": 1, "max": 1, "evidence": "Evidence."}
    return {
        "scores": {category_.key: category for category_ in ROLE.categories},
        "bonus_points": {"items": items},
        "deductions": {"total": 0, "reasons": "None."},
        "key_strengths": ["Strength."],
        "areas_for_improvement": ["Improvement."],
    }


class GeminiSchemaTests(unittest.TestCase):
    def test_evaluation_schema_needs_adapting(self):
        # Guards the test below: the raw schema has every construct Gemini mishandled.
        nodes = list(walk(evaluation_schema()))
        self.assertTrue(any("$ref" in node for node in nodes))
        self.assertTrue(any(node.get("additionalProperties") is False for node in nodes))
        self.assertTrue(
            any("enum" in node and node.get("type") == "integer" for node in nodes)
        )

    def test_adapted_schema_has_no_unsupported_keywords(self):
        for node in walk(gemini_compatible_schema(evaluation_schema())):
            self.assertNotIn("$ref", node)
            self.assertNotIn("$defs", node)
            self.assertNotIn("additionalProperties", node)
            if "enum" in node:
                self.assertEqual(node["type"], "string")

    def test_bonus_items_keep_their_fields_and_allowed_values(self):
        schema = gemini_compatible_schema(evaluation_schema())
        items = schema["properties"]["bonus_points"]["properties"]["items"]
        self.assertEqual(
            list(items["properties"]), [rule["key"] for rule in ROLE.bonus_rules]
        )
        founder = items["properties"]["founder"]
        self.assertEqual(founder["required"], ["points", "evidence"])
        self.assertEqual(founder["description"], ROLE.bonus_rules[3]["description"])
        self.assertEqual(founder["properties"]["points"]["type"], "integer")
        self.assertEqual(
            founder["properties"]["points"]["description"],
            "Allowed values: 0, 3, 4, 5",
        )
        self.assertIn("rank", items["properties"]["orchestrate"]["properties"])

    def test_string_enums_are_kept(self):
        schema = {"type": "string", "enum": ["low", "high"]}
        self.assertEqual(gemini_compatible_schema(schema), schema)

    def test_input_schema_is_not_modified(self):
        schema = evaluation_schema()
        gemini_compatible_schema(schema)
        self.assertEqual(schema, evaluation_schema())

    def test_full_model_still_rejects_points_outside_the_rule(self):
        model = build_evaluation_model(ROLE)
        model.model_validate(bonus_answer())
        with self.assertRaises(ValidationError):
            model.model_validate(
                bonus_answer(founder={"points": 7, "evidence": "Founded a startup."})
            )
        with self.assertRaises(ValidationError):
            model.model_validate(bonus_answer(founder={}))

    def test_only_gemini_requests_send_the_adapted_schema(self):
        schema = evaluation_schema()
        response = Mock(status_code=200)
        response.json.return_value = {"choices": [{"message": {"content": "{}"}}]}
        provider = OpenAICompatibleProvider(base_url="http://offline.test/v1")
        cases = {
            "google/gemini-3.1-pro-preview": gemini_compatible_schema(schema),
            "gemini-2.5-flash": gemini_compatible_schema(schema),
            "gemma4:latest": schema,
            "gpt-6-luna": schema,
        }
        with patch("requests.post", return_value=response) as post:
            for model, expected in cases.items():
                with self.subTest(model=model):
                    provider.chat(model=model, messages=[], format=schema)
                    sent = post.call_args.kwargs["json"]["response_format"]
                    self.assertEqual(sent["json_schema"]["schema"], expected)


if __name__ == "__main__":
    unittest.main()
