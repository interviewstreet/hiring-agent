import unittest

from transform import transform_achievements


class TransformAchievementsTests(unittest.TestCase):
    def test_preserves_extracted_date(self):
        for fields in ({"date": "2026-09"}, {"date": "2026-09", "year": "2025"}):
            with self.subTest(fields=fields):
                award = {
                    "title": "Example award",
                    "awarder": "Example organization",
                    "summary": "Example achievement",
                    **fields,
                }

                self.assertEqual(
                    transform_achievements([award]),
                    [
                        {
                            "title": "Example award",
                            "date": "2026-09",
                            "awarder": "Example organization",
                            "summary": "Example achievement",
                        }
                    ],
                )

    def test_falls_back_to_legacy_year(self):
        result = transform_achievements([{"year": "2026"}])

        self.assertEqual(result[0]["date"], "2026-01")

    def test_missing_date_and_year_remains_none(self):
        result = transform_achievements([{"title": "Undated award"}])

        self.assertIsNone(result[0]["date"])


if __name__ == "__main__":
    unittest.main()
