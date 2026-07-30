import unittest
from unittest.mock import patch

import score


class FailingEvaluator:
    def __init__(self, *args, **kwargs):
        pass

    def evaluate_resume(self, resume_text):
        raise ValueError("invalid model response")


class EvaluationFailureTest(unittest.TestCase):
    def test_evaluate_resume_returns_none_when_evaluator_fails(self):
        with (
            patch.object(score, "ResumeEvaluator", FailingEvaluator),
            patch.object(score, "convert_json_resume_to_text", return_value="resume"),
            self.assertLogs(score.logger, level="ERROR") as logs,
        ):
            result = score._evaluate_resume(resume_data=object())

        self.assertIsNone(result)
        self.assertTrue(
            any("Resume evaluation failed" in message for message in logs.output)
        )


if __name__ == "__main__":
    unittest.main()
