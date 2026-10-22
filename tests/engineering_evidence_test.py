import json
import unittest
from types import SimpleNamespace

from engineering_evidence import (
    format_engineering_evidence_for_evaluation,
    format_engineering_evidence_report,
    needs_engineering_evidence_extraction,
    validate_engineering_evidence,
)
from models import (
    EngineeringEvidenceCandidate,
    EngineeringEvidenceExtraction,
    JSONResume,
    EngineeringEvidenceReport,
    Skill,
)
from pdf import PDFHandler
from prompts.template_manager import TemplateManager
from evaluator import ResumeEvaluator
from transform import convert_json_resume_to_text


class FakeProvider:
    def __init__(self, content):
        self.content = content
        self.call = None

    def chat(self, **kwargs):
        self.call = kwargs
        return {"message": {"content": self.content}}


class StubEvaluationModel:
    @classmethod
    def model_json_schema(cls):
        return {}

    def __init__(self, **data):
        self.data = data


class EngineeringEvidenceTests(unittest.TestCase):
    def test_missing_or_failed_evidence_is_retried_from_cache(self):
        self.assertTrue(needs_engineering_evidence_extraction(None))
        self.assertTrue(
            needs_engineering_evidence_extraction(
                EngineeringEvidenceReport(status="extraction_error")
            )
        )
        self.assertFalse(
            needs_engineering_evidence_extraction(
                EngineeringEvidenceReport(status="complete")
            )
        )
        self.assertTrue(
            needs_engineering_evidence_extraction(
                EngineeringEvidenceReport(status="complete", rejected_observations=1)
            )
        )

    def test_valid_quote_links_listed_skills_and_records_source_lines(self):
        source = (
            "Skills: Redis, Docker\n"
            "Fixed stale inventory results by invalidating Redis entries after "
            "database updates; added regression tests for concurrent purchases."
        )
        quote = source.splitlines()[1]
        extraction = EngineeringEvidenceExtraction(
            observations=[
                EngineeringEvidenceCandidate(
                    source_id=2,
                    source_section="project",
                    problem="Stale inventory results",
                    contribution="Invalidated cache entries and added tests",
                    technical_approach="Invalidation after database updates",
                    verification="Regression tests for concurrent purchases",
                    skills=["Redis", "Docker"],
                    ownership="individual",
                    ownership_phrase="I fixed",
                )
            ]
        )

        report = validate_engineering_evidence(extraction, source, ["Redis", "Docker"])

        self.assertEqual(report.status, "complete")
        self.assertEqual(len(report.observations), 1)
        record = report.observations[0]
        self.assertEqual(record.source_start, source.index(quote))
        self.assertEqual(record.source_end, source.index(quote) + len(quote))
        self.assertEqual((record.line_start, record.line_end), (2, 2))
        self.assertEqual(record.skills, ["Redis"])
        self.assertEqual(report.skills_with_evidence, ["Redis"])
        self.assertEqual(report.skills_without_examples, ["Docker"])
        self.assertEqual(record.ownership, "unspecified")
        self.assertIsNone(record.ownership_phrase)

    def test_unknown_source_id_is_rejected_and_not_presented_as_evidence(self):
        extraction = EngineeringEvidenceExtraction(
            observations=[
                EngineeringEvidenceCandidate(
                    source_id=99,
                    contribution="Led migration",
                )
            ]
        )

        report = validate_engineering_evidence(
            extraction, "Migrated the service to a new database.", ["PostgreSQL"]
        )

        self.assertEqual(report.status, "complete")
        self.assertEqual(report.observations, [])
        self.assertEqual(report.rejected_observations, 1)
        self.assertEqual(report.skills_without_examples, ["PostgreSQL"])

    def test_explicit_ownership_phrase_is_preserved(self):
        source = "Our team fixed stale results using Redis."
        extraction = EngineeringEvidenceExtraction(
            observations=[
                EngineeringEvidenceCandidate(
                    source_id=1,
                    ownership="team",
                    ownership_phrase="Our team",
                )
            ]
        )

        report = validate_engineering_evidence(extraction, source, [])

        self.assertEqual(report.observations[0].ownership, "team")
        self.assertEqual(report.observations[0].ownership_phrase, "Our team")

    def test_empty_observations_means_no_evidence_not_extraction_error(self):
        report = validate_engineering_evidence(
            EngineeringEvidenceExtraction(observations=[]),
            "Skills: Go\nWorked on several projects.",
            ["Go"],
        )

        self.assertEqual(report.status, "complete")
        self.assertEqual(report.observations, [])
        self.assertEqual(report.skills_without_examples, ["Go"])

    def test_missing_source_is_an_extraction_error(self):
        report = validate_engineering_evidence(
            EngineeringEvidenceExtraction(observations=[]), "", ["Go"]
        )

        self.assertEqual(report.status, "extraction_error")
        self.assertIn("empty", report.error)

    def test_formatter_labels_report_as_evaluation_context(self):
        report = validate_engineering_evidence(
            EngineeringEvidenceExtraction(observations=[]), "No work described.", []
        )

        rendered = format_engineering_evidence_report(report)

        self.assertIn("ENGINEERING EVIDENCE", rendered)
        self.assertIn("included as evaluation context", rendered)

    def test_engineering_report_is_added_as_evaluation_context(self):
        source = "Fixed stale results by invalidating Redis after writes."
        report = validate_engineering_evidence(
            EngineeringEvidenceExtraction(
                observations=[
                    EngineeringEvidenceCandidate(
                        source_id=1,
                        contribution="Invalidated stale cache entries",
                    )
                ]
            ),
            source,
            [],
        )
        resume = JSONResume(engineering_evidence=report)

        score_input = convert_json_resume_to_text(resume)

        self.assertIn("SUPPLEMENTAL ENGINEERING EVIDENCE", score_input)
        self.assertIn(source, score_input)

    def test_evaluator_receives_missing_information_guidance(self):
        evaluator = ResumeEvaluator.__new__(ResumeEvaluator)
        evaluator.role = SimpleNamespace(
            criteria_source="Resume input:\n{{ text_content }}",
            system_message_source="Role evaluation rules.",
            bonus_rules=[],
            bonus_max=20,
        )
        evaluator.evaluation_model = StubEvaluationModel
        evaluator.model_name = "test-model"
        evaluator.model_params = {}
        evaluator.template_manager = TemplateManager()
        evaluator.provider = FakeProvider("{}")

        evaluator.evaluate_resume(
            "=== SUPPLEMENTAL ENGINEERING EVIDENCE ===\n"
            "No observations were extracted. Treat this as insufficient information."
        )

        system_message = evaluator.provider.call["messages"][0]["content"]
        self.assertIn("insufficient information", system_message)
        self.assertIn("Do not penalize a listed skill", system_message)

    def test_no_observations_are_marked_as_insufficient_information(self):
        report = validate_engineering_evidence(
            EngineeringEvidenceExtraction(observations=[]), "No work described.", []
        )

        evaluation_context = format_engineering_evidence_for_evaluation(report)

        self.assertIn("insufficient information", evaluation_context)
        self.assertIn("not as evidence that the candidate lacks", evaluation_context)
        score_input = convert_json_resume_to_text(
            JSONResume(engineering_evidence=report)
        )
        self.assertIn("insufficient information", score_input)

    def test_pdf_handler_calls_model_and_validates_returned_quote(self):
        source = "Fixed stale results by invalidating Redis after writes."
        content = json.dumps(
            {
                "observations": [
                    {
                        "source_id": 1,
                        "source_section": "work",
                        "problem": "Stale results",
                        "contribution": "Invalidated Redis",
                        "technical_approach": "Invalidation after writes",
                        "verification": None,
                        "outcome": None,
                        "skills": ["Redis"],
                        "ownership": "unspecified",
                        "ownership_phrase": None,
                    }
                ]
            }
        )
        handler = PDFHandler.__new__(PDFHandler)
        handler.template_manager = TemplateManager()
        handler.provider = FakeProvider(content)
        handler.model_name = "test-model"

        from unittest.mock import patch

        with patch("pdf.DEFAULT_MODEL", "test-model"), patch(
            "pdf.MODEL_PARAMETERS", {"test-model": {"temperature": 0}}
        ):
            resume = JSONResume(skills=[Skill(name="Redis"), Skill(name="Docker")])
            report = handler.extract_engineering_evidence(source, resume)

        self.assertEqual(report.status, "complete")
        self.assertEqual(report.skills_with_evidence, ["Redis"])
        self.assertEqual(report.skills_without_examples, ["Docker"])
        self.assertIn("Redis", handler.provider.call["messages"][1]["content"])
        self.assertIn("format", handler.provider.call)


if __name__ == "__main__":
    unittest.main()
