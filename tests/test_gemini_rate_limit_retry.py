import unittest
from unittest.mock import patch

from models import (
    GEMINI_BASE_DELAY_SECONDS,
    GEMINI_MAX_DELAY_SECONDS,
    calculate_gemini_retry_delay_seconds,
    calculate_gemini_sleep_seconds,
    extract_gemini_retry_delay_seconds,
)


class GeminiRateLimitRetryTests(unittest.TestCase):
    def test_extracts_retry_in_delay(self):
        error = Exception("Quota exceeded. Please retry in 15.857796757s.")

        self.assertEqual(extract_gemini_retry_delay_seconds(error), 15.857796757)

    def test_extracts_retry_delay_metadata(self):
        error = Exception("retry_delay { seconds: 12 nanos: 500000000 }")

        self.assertEqual(extract_gemini_retry_delay_seconds(error), 12.5)

    def test_returns_none_when_retry_delay_is_missing(self):
        error = Exception("Quota exceeded.")

        self.assertIsNone(extract_gemini_retry_delay_seconds(error))

    def test_uses_api_hint_when_it_is_longer_than_backoff(self):
        error = Exception("Quota exceeded. Please retry in 15.857796757s.")

        delay = calculate_gemini_retry_delay_seconds(error, attempt=0)

        self.assertEqual(delay, 15.857796757)

    def test_uses_exponential_backoff_when_api_hint_is_shorter(self):
        error = Exception("Quota exceeded. Please retry in 5s.")

        delay = calculate_gemini_retry_delay_seconds(error, attempt=1)

        self.assertEqual(delay, GEMINI_BASE_DELAY_SECONDS * 2)

    def test_caps_exponential_backoff_without_api_hint(self):
        error = Exception("Quota exceeded.")

        delay = calculate_gemini_retry_delay_seconds(error, attempt=10)

        self.assertEqual(delay, GEMINI_MAX_DELAY_SECONDS)

    def test_sleep_jitter_does_not_retry_before_api_hint(self):
        error = Exception("Quota exceeded. Please retry in 15.857796757s.")

        with patch("random.uniform", return_value=1.0) as mock_uniform:
            sleep_time = calculate_gemini_sleep_seconds(error, attempt=0)

        self.assertEqual(sleep_time, 15.86)
        mock_uniform.assert_called_once_with(1.0, 1.2)

    def test_sleep_jitter_can_reduce_backoff_without_api_hint(self):
        error = Exception("Quota exceeded.")

        with patch("random.uniform", return_value=0.8) as mock_uniform:
            sleep_time = calculate_gemini_sleep_seconds(error, attempt=0)

        self.assertEqual(sleep_time, 8.0)
        mock_uniform.assert_called_once_with(0.8, 1.2)

    def test_sleep_fails_fast_when_api_hint_exceeds_max_wait(self):
        error = Exception("Quota exceeded. Please retry in 121s.")

        with self.assertRaises(RuntimeError):
            calculate_gemini_sleep_seconds(error, attempt=0)


if __name__ == "__main__":
    unittest.main()
