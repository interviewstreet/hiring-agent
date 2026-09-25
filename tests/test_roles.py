import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import roles


class RoleNumericValidationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        patcher = patch.object(roles, "ROLES_DIR", Path(temporary.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.role_dir = roles.scaffold_role("test_role")
        self.manifest = json.loads((self.role_dir / "role.json").read_text())

    def load(self):
        (self.role_dir / "role.json").write_text(json.dumps(self.manifest))
        return roles.load_role("test_role")

    def test_rejects_non_integer_numeric_settings(self):
        for field in ("max", "bonus_max", "min_final_score", "max_final_score"):
            target = self.manifest["categories"][0] if field == "max" else self.manifest
            original = target[field]
            for value in (True, False, 3.9, 3.0, "3", None, [], {}):
                with self.subTest(field=field, value=value):
                    target[field] = value
                    with self.assertRaises(ValueError) as error:
                        self.load()
                    self.assertIn("test_role", str(error.exception))
                    self.assertIn(field, str(error.exception))
            target[field] = original

    def test_rejects_nonpositive_category_maximum(self):
        for value in (0, -1):
            with self.subTest(value=value):
                self.manifest["categories"][0]["max"] = value
                with self.assertRaisesRegex(ValueError, "category_one.*max"):
                    self.load()

    def test_rejects_negative_bonus_limit(self):
        self.manifest["bonus_max"] = -1
        with self.assertRaisesRegex(ValueError, "bonus_max"):
            self.load()

    def test_rejects_inverted_bounds(self):
        self.manifest.update(min_final_score=21, max_final_score=20)
        with self.assertRaisesRegex(ValueError, "min_final_score.*max_final_score"):
            self.load()

    def test_preserves_defaults_and_custom_category_totals(self):
        self.manifest = {"categories": [{"key": "skills", "max": 7}]}
        role = self.load()
        self.assertEqual(
            (role.bonus_max, role.min_final_score, role.max_final_score), (20, 0, 27)
        )
        self.assertEqual(role.categories[0].max, 7)

    def test_accepts_zero_bonus_and_negative_or_equal_bounds(self):
        for lower, upper in ((-20, 90), (5, 5), (-10, -5)):
            with self.subTest(lower=lower, upper=upper):
                self.manifest.update(
                    bonus_max=0, min_final_score=lower, max_final_score=upper
                )
                role = self.load()
                self.assertEqual(
                    (role.bonus_max, role.min_final_score, role.max_final_score),
                    (0, lower, upper),
                )

    def test_scaffold_remains_loadable(self):
        role = self.load()
        self.assertEqual([category.max for category in role.categories], [50, 50])
        self.assertEqual(role.max_final_score, 110)

    def test_bundled_role_remains_loadable(self):
        with patch.object(roles, "ROLES_DIR", Path(roles.__file__).parent / "roles"):
            role = roles.load_role("software_engineering_intern")
        self.assertEqual(
            [category.max for category in role.categories], [35, 30, 25, 10]
        )
        self.assertEqual(
            (role.bonus_max, role.min_final_score, role.max_final_score), (20, -20, 120)
        )


if __name__ == "__main__":
    unittest.main()
