import unittest
from dataclasses import replace

from pydantic import ValidationError

from models import build_bonus_model, build_evaluation_model
from roles import load_role


class BonusTests(unittest.TestCase):
    def setUp(self):
        self.role = load_role("software_engineering_intern")
        self.model = build_bonus_model(self.role)

    def entries(self, rank=None, points=4):
        items = {}
        for rule in self.role.bonus_rules:
            items[rule["key"]] = {
                "evidence": "No evidence",
                **(
                    {"rank": rank, "points": points if rank is not None else 0}
                    if "tiers" in rule
                    else {"points": 0}
                ),
            }
        items["orchestrate"]["evidence"] = (
            "HackerRank Orchestrate award" if rank else "No qualifying award"
        )
        return items

    def test_rank_boundaries_and_display(self):
        for rank, expected in [
            (None, 0),
            (1, 4),
            (5, 4),
            (100, 4),
            (101, 3),
            (200, 3),
            (201, 0),
        ]:
            with self.subTest(rank=rank):
                result = self.model(items=self.entries(rank, expected))
                self.assertEqual(result.total, expected)
                self.assertEqual(
                    result.model_dump()["items"]["orchestrate"]["points"], expected
                )
                self.assertIn(
                    f"HackerRank Orchestrate: +{expected} points", result.breakdown
                )
                if rank:
                    self.assertIn(f"rank {rank}", result.breakdown)

    def test_cap_and_serialization(self):
        items = self.entries(5)
        for rule in self.role.bonus_rules:
            if "points" in rule:
                items[rule["key"]]["points"] = max(rule["points"])
        result = self.model(items=items)
        self.assertEqual(result.total, 20)
        self.assertIn("Subtotal: 26", result.breakdown)
        self.assertEqual(result.model_dump()["total"], 20)

    def test_reject_invalid_or_unlisted_bonuses(self):
        cases = []
        items = self.entries(5)
        items["competitive_programming"] = {
            "points": 5,
            "evidence": "Codeforces Expert",
        }
        cases.append({"items": items})
        items = self.entries(5)
        items["linkedin"]["points"] = 5
        cases.append({"items": items})
        items = self.entries(5)
        items["orchestrate"]["points"] = 8
        cases.append({"items": items})
        items = self.entries(5)
        del items["orchestrate"]
        cases.append({"items": items})
        cases.append({"items": self.entries(0)})
        cases.append(
            {"items": self.entries(5), "total": 18, "breakdown": "Generic excellence"}
        )
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                self.model(**payload)

    def test_reject_rank_points_mismatch(self):
        for rank, points in [(5, 3), (100, 3), (101, 4), (200, 4), (201, 3)]:
            with self.subTest(rank=rank, points=points), self.assertRaises(
                ValidationError
            ):
                self.model(items=self.entries(rank, points))
        items = self.entries()
        items["orchestrate"]["points"] = 4
        with self.assertRaises(ValidationError):
            self.model(items=items)

    def test_other_roles_keep_legacy_bonus_schema(self):
        role = replace(self.role, bonus_rules=[])
        schema = build_evaluation_model(role).model_json_schema()
        self.assertEqual(
            set(schema["$defs"]["BonusPoints"]["properties"]), {"total", "breakdown"}
        )

    def test_generated_schema_requires_orchestrate_without_model_total(self):
        schema = build_evaluation_model(self.role).model_json_schema()
        self.assertIn("orchestrate", schema["$defs"]["BonusItems"]["required"])
        self.assertNotIn("total", schema["$defs"]["BonusPoints"]["properties"])
        self.assertIn("points", schema["$defs"]["orchestrateBonus"]["required"])


if __name__ == "__main__":
    unittest.main()
