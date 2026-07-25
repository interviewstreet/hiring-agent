"""Regression tests for deterministic score arithmetic.

Run with: python -m unittest test_scoring.py
"""

import unittest

from models import EvaluationData
from scoring import calculate_total_score


def evaluation(**overrides):
    payload = {
        "scores": {
            "open_source": {"score": 10, "max": 35, "evidence": "evidence"},
            "self_projects": {"score": 20, "max": 30, "evidence": "evidence"},
            "production": {"score": 15, "max": 25, "evidence": "evidence"},
            "technical_skills": {"score": 8, "max": 10, "evidence": "evidence"},
        },
        "bonus_points": {"total": 5, "breakdown": "bonus"},
        "deductions": {"total": 2, "reasons": "deduction"},
        "key_strengths": ["strength"],
        "areas_for_improvement": ["improvement"],
    }
    for key, value in overrides.items():
        payload[key] = value
    return EvaluationData(**payload)


class ScoreArithmeticTests(unittest.TestCase):
    def test_adds_categories_bonus_and_deductions(self):
        total, maximum, capped, was_capped = calculate_total_score(evaluation())
        self.assertEqual(total, 56)
        self.assertEqual(maximum, 100)
        self.assertEqual(capped["open_source"], 10)
        self.assertFalse(was_capped)

    def test_caps_category_scores_before_total(self):
        item = evaluation()
        item.scores.open_source.score = 99
        total, _, capped, _ = calculate_total_score(item)
        self.assertEqual(capped["open_source"], 35)
        self.assertEqual(total, 81)

    def test_caps_total_at_category_maximum_plus_bonus(self):
        item = evaluation()
        item.scores.open_source.score = 35
        item.scores.self_projects.score = 30
        item.scores.production.score = 25
        item.scores.technical_skills.score = 10
        item.bonus_points.total = 50
        item.deductions.total = 0
        total, maximum, _, was_capped = calculate_total_score(item)
        self.assertEqual(maximum, 100)
        self.assertEqual(total, 120)
        self.assertTrue(was_capped)


if __name__ == "__main__":
    unittest.main()
