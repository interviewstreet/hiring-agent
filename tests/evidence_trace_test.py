from copy import deepcopy
from contextlib import chdir
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from evidence_trace import (
    build_source_catalog,
    build_trace_report,
    render_source_catalog,
    render_trace_markdown,
    write_trace_reports,
)
from models import JSONResume, build_evaluation_model, GitHubProfile
from roles import Category, Role, load_role


def example_role():
    return Role(
        name="example",
        position_title="Example engineer",
        categories=[
            Category("projects", "Projects", 30),
            Category("production", "Production", 25),
        ],
        bonus_max=10,
        min_final_score=0,
        max_final_score=65,
        criteria_source="Evaluate these records: {{ text_content }}",
        system_message_source="Evaluate demonstrated experience.",
    )


def evaluation_payload(citations=None):
    score = {"score": 20, "max": 30, "evidence": "Built REST APIs"}
    if citations is not None:
        score["citations"] = citations
    return {
        "scores": {"projects": deepcopy(score), "production": deepcopy(score)},
        "bonus_points": {"total": 0, "breakdown": "No bonus"},
        "deductions": {"total": 0, "reasons": "None"},
        "key_strengths": ["API development"],
        "areas_for_improvement": ["More production evidence"],
    }


class SourceCatalogTests(unittest.TestCase):
    def setUp(self):
        self.resume = JSONResume(
            projects=[{"name": "Service", "description": "Built REST APIs"}]
        )

    def test_stable_ids_across_key_and_record_reordering(self):
        first = JSONResume(
            projects=[
                {"name": "A", "description": "First"},
                {"name": "B", "description": "Second"},
            ]
        )
        second = JSONResume(
            projects=[
                {"description": "Second", "name": "B"},
                {"description": "First", "name": "A"},
            ]
        )
        left = build_source_catalog(first)
        right = build_source_catalog(second)
        self.assertEqual(set(left), set(right))
        for source_id in left:
            self.assertEqual(left[source_id]["data"], right[source_id]["data"])

    def test_content_change_changes_id(self):
        changed = self.resume.model_copy(deep=True)
        changed.projects[0].description = "Built a different service"
        self.assertNotEqual(
            set(build_source_catalog(self.resume)), set(build_source_catalog(changed))
        )

    def test_duplicate_records_keep_both_locations(self):
        duplicate = JSONResume(
            projects=[self.resume.projects[0], self.resume.projects[0]]
        )
        sources = build_source_catalog(duplicate)
        self.assertEqual(len(sources), 1)
        self.assertEqual(
            next(iter(sources.values()))["locations"],
            ["resume.projects[0]", "resume.projects[1]"],
        )

    def test_empty_sections_have_no_sources(self):
        self.assertEqual(build_source_catalog(JSONResume()), {})

    def test_catalog_does_not_mutate_resume_or_github(self):
        github = {"projects": [{"name": "Repository"}]}
        before = deepcopy(github)
        original_resume = self.resume.model_dump()
        build_source_catalog(self.resume, github)
        self.assertEqual(github, before)
        self.assertEqual(self.resume.model_dump(), original_resume)

    def test_catalog_snapshots_data_before_caller_mutation(self):
        github = {"projects": [{"name": "Repository", "technologies": ["Python"]}]}
        sources = build_source_catalog(self.resume, github)
        github["projects"][0]["technologies"].append("Invented language")
        source = next(
            source for source in sources.values() if source["section"] == "repository"
        )
        self.assertEqual(source["data"]["technologies"], ["Python"])

    def test_legacy_enrichment_is_not_labelled_api_data(self):
        sources = build_source_catalog(
            self.resume,
            {
                "profile": {"bio": "GSoC participant"},
                "projects": [{"name": "Invented"}],
            },
        )
        origins = {source["origin"] for source in sources.values()}
        self.assertNotIn("github_api_snapshot", origins)
        self.assertIn("github_enrichment_unverified", origins)

    def test_pre_selector_snapshot_separates_text_metadata_and_derived_counts(self):
        repo = {
            "name": "service",
            "github_url": "https://github.com/example/service",
            "description": "A user-written claim",
            "author_commit_count": 12,
            "project_type": "open_source",
            "contributor_count": 2,
            "github_details": {
                "stars": 50,
                "description": "A user-written claim",
                "topics": ["backend"],
                "contributors": 2,
            },
        }
        selected = deepcopy(repo)
        selected["github_details"]["stars"] = 999999
        github = {
            "projects": [selected],
            "evidence_sources": {
                "profile": {
                    "username": "example",
                    "bio": "User bio",
                    "public_repos": 3,
                },
                "repositories": [repo],
            },
        }
        sources = build_source_catalog(self.resume, github)
        metrics = [
            source
            for source in sources.values()
            if source["origin"] == "github_api_snapshot"
            and source["section"] == "repository"
        ]
        self.assertEqual(metrics[0]["data"]["stars"], 50)
        self.assertNotIn("description", metrics[0]["data"])
        self.assertNotIn("contributors", metrics[0]["data"])
        derived = [
            source
            for source in sources.values()
            if source["origin"] == "github_derived_metrics"
        ]
        self.assertEqual(derived[0]["data"]["author_commit_count"], 12)
        self.assertIn(
            "github_user_written_text",
            {source["origin"] for source in sources.values()},
        )

    def test_selector_invented_repository_remains_unverified(self):
        github = {
            "projects": [{"github_url": "https://github.com/invented/repo"}],
            "evidence_sources": {"profile": {}, "repositories": []},
        }
        sources = build_source_catalog(self.resume, github)
        repo = next(
            source for source in sources.values() if source["section"] == "repository"
        )
        self.assertEqual(repo["origin"], "github_enrichment_unverified")

    def test_unselected_repositories_are_not_added(self):
        github = {
            "projects": [],
            "evidence_sources": {
                "profile": {},
                "repositories": [{"github_url": "https://github.com/example/repo"}],
            },
        }
        self.assertEqual(
            build_source_catalog(self.resume, github), build_source_catalog(self.resume)
        )

    def test_catalog_json_round_trip_and_unverified_blog(self):
        sources = build_source_catalog(self.resume, blog_data={"summary": "Some blog"})
        self.assertEqual(
            json.loads(render_source_catalog(sources))["sources"],
            list(sources.values()),
        )
        self.assertIn(
            "blog_enrichment_unverified",
            {source["origin"] for source in sources.values()},
        )


class CitationValidationTests(unittest.TestCase):
    def setUp(self):
        self.role = example_role()
        self.sources = build_source_catalog(
            JSONResume(projects=[{"name": "Service", "description": "Built REST APIs"}])
        )
        self.source_id = next(iter(self.sources))
        self.model = build_evaluation_model(self.role, evidence_trace=True)

    def report(self, source_id, quote):
        evaluation = self.model(
            **evaluation_payload([{"source_id": source_id, "quote": quote}])
        )
        return build_trace_report(evaluation, self.role, self.sources, "fixture-model")

    def test_resolves_reference_and_matching_quote(self):
        report = self.report(self.source_id, "Built REST APIs")
        self.assertEqual(
            report["categories"][0]["status"], "references_and_quotes_match"
        )
        self.assertEqual(report["summary"]["matching_quotes"], 2)

    def test_unknown_source_is_flagged_and_not_dropped(self):
        report = self.report("S-invented", "Built REST APIs")
        citation = report["categories"][0]["citations"][0]
        self.assertEqual(citation["status"], "unknown_source")
        self.assertEqual(citation["source_id"], "S-invented")
        self.assertEqual(report["summary"]["resolved_references"], 0)

    def test_fabricated_quote_with_real_id_is_flagged(self):
        report = self.report(self.source_id, "Participated in GSoC")
        self.assertEqual(
            report["categories"][0]["citations"][0]["status"], "quote_not_found"
        )
        self.assertEqual(report["categories"][0]["status"], "needs_review")

    def test_quote_in_other_source_does_not_count(self):
        self.sources.update(
            build_source_catalog(JSONResume(awards=[{"title": "GSoC participant"}]))
        )
        report = self.report(self.source_id, "GSoC participant")
        self.assertEqual(report["summary"]["matching_quotes"], 0)

    def test_source_id_is_not_itself_supporting_quote(self):
        report = self.report(self.source_id, self.source_id)
        self.assertEqual(report["summary"]["matching_quotes"], 0)

    def test_empty_citations_are_uncited(self):
        evaluation = self.model(**evaluation_payload([]))
        report = build_trace_report(
            evaluation, self.role, self.sources, "fixture-model"
        )
        self.assertTrue(
            all(category["status"] == "uncited" for category in report["categories"])
        )

    def test_whitespace_only_quote_does_not_count(self):
        report = self.report(self.source_id, " \n ")
        self.assertEqual(report["summary"]["matching_quotes"], 0)

    def test_joined_array_values_are_not_an_exact_quote(self):
        self.sources = build_source_catalog(
            JSONResume(
                projects=[
                    {
                        "name": "Service",
                        "technologies": ["Python", "FastAPI", "PostgreSQL"],
                    }
                ]
            )
        )
        self.source_id = next(iter(self.sources))
        report = self.report(self.source_id, "Python, FastAPI, PostgreSQL")
        self.assertEqual(report["summary"]["matching_quotes"], 0)
        self.assertEqual(
            self.report(self.source_id, "Python")["summary"]["matching_quotes"], 2
        )

    def test_unicode_and_escaped_strings(self):
        self.sources = build_source_catalog(
            JSONResume(projects=[{"description": 'Built "café"\nREST APIs'}])
        )
        self.source_id = next(iter(self.sources))
        report = self.report(self.source_id, 'Built "café" REST APIs')
        self.assertEqual(report["summary"]["matching_quotes"], 2)

    def test_mixed_citations_need_review(self):
        citations = [
            {"source_id": self.source_id, "quote": "Built REST APIs"},
            {"source_id": "fake", "quote": "GSoC"},
        ]
        evaluation = self.model(**evaluation_payload(citations))
        report = build_trace_report(
            evaluation, self.role, self.sources, "fixture-model"
        )
        self.assertEqual(report["categories"][0]["status"], "needs_review")
        self.assertEqual(report["summary"]["citations"], 4)
        self.assertEqual(report["summary"]["matching_quotes"], 2)

    def test_matching_quote_does_not_certify_semantic_support(self):
        payload = evaluation_payload(
            [{"source_id": self.source_id, "quote": "Built REST APIs"}]
        )
        payload["scores"]["projects"]["evidence"] = "Candidate participated in GSoC"
        evaluation = self.model(**payload)
        before = evaluation.model_dump()
        report = build_trace_report(
            evaluation, self.role, self.sources, "fixture-model"
        )
        self.assertEqual(
            report["categories"][0]["status"], "references_and_quotes_match"
        )
        self.assertIn("semantic support is not verified", report["limitations"][0])
        self.assertEqual(evaluation.model_dump(), before)

    def test_default_schema_unchanged_and_trace_requires_citations(self):
        default = build_evaluation_model(self.role)
        self.assertNotIn(
            "citations",
            default.model_json_schema()["$defs"]["CategoryScore"]["properties"],
        )
        default(**evaluation_payload())
        with self.assertRaises(ValidationError):
            self.model(**evaluation_payload())

    def test_trace_schema_supports_shipped_role_and_structured_bonuses(self):
        role = load_role("software_engineering_intern")
        payload = evaluation_payload([])
        payload["scores"] = {
            category.key: {
                "score": 0,
                "max": category.max,
                "evidence": "No cited support",
                "citations": [],
            }
            for category in role.categories
        }
        items = {}
        for rule in role.bonus_rules:
            items[rule["key"]] = {"points": 0, "evidence": "No cited support"}
            if "tiers" in rule:
                items[rule["key"]]["rank"] = None
        payload["bonus_points"] = {"items": items}
        evaluation = build_evaluation_model(role, evidence_trace=True)(**payload)
        self.assertEqual(evaluation.bonus_points.total, 0)
        report = build_trace_report(evaluation, role, {}, "fixture-model")
        self.assertEqual(report["summary"]["categories"], len(role.categories))

    def test_report_uses_role_max_and_preserves_model_score(self):
        payload = evaluation_payload([])
        payload["scores"]["production"].update(score=28, max=999)
        report = build_trace_report(
            self.model(**payload), self.role, self.sources, "fixture-model"
        )
        self.assertEqual(report["categories"][1]["rubric_max"], 25)
        self.assertEqual(report["categories"][1]["model_score"], 28)

    def test_reports_round_trip_utf8_and_dotted_stem(self):
        report = self.report(self.source_id, "Built REST APIs")
        with tempfile.TemporaryDirectory() as directory:
            paths = write_trace_reports(
                report, Path(directory) / "nested" / "candidate.v1"
            )
            self.assertEqual(paths[0].name, "candidate.v1.json")
            self.assertEqual(json.loads(paths[0].read_text(encoding="utf-8")), report)
            markdown = paths[1].read_text(encoding="utf-8")
            self.assertIn("resume_extracted_claim", markdown)
            self.assertIn("Built REST APIs", markdown)

    def test_markdown_escapes_untrusted_html_and_fences(self):
        payload = evaluation_payload([])
        payload["scores"]["projects"][
            "evidence"
        ] = "<script>alert(1)</script> [click](javascript:bad)"
        report = build_trace_report(
            self.model(**payload), self.role, self.sources, "fixture-model"
        )
        markdown = render_trace_markdown(report)
        self.assertNotIn("<script>", markdown)
        self.assertNotIn("[click](", markdown)
        self.sources[self.source_id]["data"]["description"] = "```\n# Forged heading"
        report = self.report(self.source_id, "Forged heading")
        self.assertIn("````json", render_trace_markdown(report))


class PipelineTests(unittest.TestCase):
    def test_main_cache_migration_and_default_cache_compatibility(self):
        import score

        role = example_role()
        resume = JSONResume(
            basics={
                "name": "Example",
                "profiles": [
                    {"network": "GitHub", "url": "https://github.com/example"}
                ],
            },
            projects=[{"name": "Service", "description": "Built REST APIs"}],
        )
        source_id = next(
            source["id"]
            for source in build_source_catalog(resume).values()
            if source["section"] == "projects"
        )
        legacy = {"profile": {"username": "example"}, "projects": []}
        current = {
            **legacy,
            "evidence_sources": {"profile": legacy["profile"], "repositories": []},
        }
        for mode in ("default", "legacy_trace", "current_trace", "failed_refresh"):
            with self.subTest(
                mode=mode
            ), tempfile.TemporaryDirectory() as directory, chdir(directory), patch(
                "score.DEVELOPMENT_MODE", True
            ), patch(
                "score.PDFHandler"
            ) as pdf, patch(
                "score.fetch_and_display_github_info"
            ) as fetch, patch(
                "evaluator.initialize_llm_provider"
            ) as initialize, patch(
                "sys.stdout", new=io.StringIO()
            ):
                Path("cache").mkdir()
                Path("cache/resumecache_candidate.json").write_text(
                    resume.model_dump_json(), encoding="utf-8"
                )
                cache_path = Path("cache/githubcache_candidate.json")
                old = current if mode == "current_trace" else legacy
                cache_path.write_text(json.dumps(old), encoding="utf-8")
                fetch.return_value = {} if mode == "failed_refresh" else current
                citations = (
                    None
                    if mode == "default"
                    else [{"source_id": source_id, "quote": "Built REST APIs"}]
                )
                initialize.return_value.chat.return_value = {
                    "message": {"content": json.dumps(evaluation_payload(citations))}
                }
                score.main(
                    "candidate.pdf",
                    role,
                    trace_output=None if mode == "default" else "trace",
                )
                pdf.assert_not_called()
                initialize.return_value.chat.assert_called_once()
                if mode in ("legacy_trace", "failed_refresh"):
                    fetch.assert_called_once_with(
                        "https://github.com/example",
                        position_title=role.position_title,
                        include_evidence_sources=True,
                    )
                else:
                    fetch.assert_not_called()
                expected_cache = (
                    current if mode in ("legacy_trace", "current_trace") else legacy
                )
                self.assertEqual(
                    json.loads(cache_path.read_text(encoding="utf-8")), expected_cache
                )
                self.assertEqual(Path("trace.json").exists(), mode != "default")

    def test_evaluator_requests_citations_and_cli_writes_report_in_one_call(self):
        import score

        role = example_role()
        resume = JSONResume(
            projects=[{"name": "Service", "description": "Built REST APIs"}]
        )
        sources = build_source_catalog(resume)
        source_id = next(iter(sources))
        payload = evaluation_payload(
            [{"source_id": source_id, "quote": "Built REST APIs"}]
        )
        with tempfile.TemporaryDirectory() as directory, patch(
            "evaluator.initialize_llm_provider"
        ) as initialize, patch("sys.stdout", new=io.StringIO()):
            initialize.return_value.chat.return_value = {
                "message": {"content": json.dumps(payload)}
            }
            result = score._evaluate_resume(
                resume,
                role,
                build_evaluation_model(role, evidence_trace=True),
                trace_output=str(Path(directory) / "trace"),
            )
            initialize.return_value.chat.assert_called_once()
            request = initialize.return_value.chat.call_args.kwargs
            self.assertIn("EVIDENCE TRACE MODE", request["messages"][0]["content"])
            self.assertIn(source_id, request["messages"][1]["content"])
            self.assertIn(
                "citations",
                request["format"]["$defs"]["TracedCategoryScore"]["required"],
            )
            report = json.loads(
                (Path(directory) / "trace.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["summary"]["matching_quotes"], 2)
            self.assertEqual(result.scores.projects.score, 20)

    def test_default_pipeline_has_no_trace_instructions_or_catalog(self):
        import score

        role = example_role()
        resume = JSONResume(
            projects=[{"name": "Service", "description": "Built REST APIs"}]
        )
        with patch("evaluator.initialize_llm_provider") as initialize:
            initialize.return_value.chat.return_value = {
                "message": {"content": json.dumps(evaluation_payload())}
            }
            result = score._evaluate_resume(resume, role, build_evaluation_model(role))
            request = initialize.return_value.chat.call_args.kwargs
            self.assertNotIn("EVIDENCE TRACE MODE", request["messages"][0]["content"])
            self.assertIn("=== PROJECTS ===", request["messages"][1]["content"])
            self.assertFalse(hasattr(result.scores.projects, "citations"))

    def test_github_snapshot_precedes_selector_mutation(self):
        import github

        projects = [{"name": "Original", "github_details": {"stars": 10}}]

        def selector(records, **kwargs):
            records[0]["github_details"]["stars"] = 999
            return records

        with patch(
            "github.fetch_github_profile",
            return_value=GitHubProfile(username="example"),
        ), patch("github.fetch_all_github_repos", return_value=projects), patch(
            "github.generate_projects_json", side_effect=selector
        ), patch(
            "sys.stdout", new=io.StringIO()
        ):
            result = github.fetch_and_display_github_info(
                "https://github.com/example", include_evidence_sources=True
            )
        self.assertEqual(result["projects"][0]["github_details"]["stars"], 999)
        self.assertEqual(
            result["evidence_sources"]["repositories"][0]["github_details"]["stars"], 10
        )

    def test_default_github_output_has_no_added_provenance_fields(self):
        import github

        with patch(
            "github.fetch_github_profile",
            return_value=GitHubProfile(username="example"),
        ), patch("github.fetch_all_github_repos", return_value=[]), patch(
            "github.generate_projects_json", return_value=[]
        ), patch(
            "sys.stdout", new=io.StringIO()
        ):
            result = github.fetch_and_display_github_info("https://github.com/example")
        self.assertEqual(set(result), {"profile", "projects", "total_projects"})

    def test_synthetic_demo_expected_checks(self):
        from examples.evidence_trace_demo import run_demo

        with tempfile.TemporaryDirectory() as directory, patch(
            "sys.stdout", new=io.StringIO()
        ):
            summary = run_demo(directory)
            self.assertEqual(summary["passed"], 6)
            self.assertEqual(summary["total"], 6)
            self.assertEqual(len(list(Path(directory).glob("*.md"))), 6)
            self.assertIn("not a model benchmark", summary["kind"])


if __name__ == "__main__":
    unittest.main()
