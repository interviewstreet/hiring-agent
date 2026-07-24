import sys
import types
import unittest


sys.modules.setdefault("models", types.SimpleNamespace(JSONResume=object))

from transform import parse_date_range


class TransformDateRangeTests(unittest.TestCase):
    def test_parse_month_range_with_en_dash(self):
        self.assertEqual(parse_date_range("Jan–Mar 2021"), ("Jan 2021", "Mar 2021"))

    def test_parse_year_range_with_en_dash(self):
        self.assertEqual(parse_date_range("2020–2021"), ("2020-01", "2021-12"))

    def test_parse_year_range_with_em_dash(self):
        self.assertEqual(parse_date_range("2020—2021"), ("2020-01", "2021-12"))


if __name__ == "__main__":
    unittest.main()
