import unittest

from models import Deductions


class DeductionsTest(unittest.TestCase):
    def test_total_is_normalized_to_positive(self):
        deductions = Deductions(total=-10, reasons="Broken links")

        self.assertEqual(deductions.total, 10.0)


if __name__ == "__main__":
    unittest.main()
