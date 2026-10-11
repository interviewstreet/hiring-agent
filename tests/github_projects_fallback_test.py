import sys
import types
import unittest
from contextlib import redirect_stdout
from io import StringIO


sys.modules.setdefault("requests", types.SimpleNamespace())
sys.modules.setdefault("models", types.SimpleNamespace(GitHubProfile=object))
sys.modules.setdefault(
    "pdf",
    types.SimpleNamespace(
        logger=types.SimpleNamespace(
            error=lambda *args, **kwargs: None,
            info=lambda *args, **kwargs: None,
            warning=lambda *args, **kwargs: None,
        )
    ),
)
sys.modules.setdefault(
    "prompts.template_manager",
    types.SimpleNamespace(TemplateManager=object),
)
sys.modules.setdefault(
    "prompt", types.SimpleNamespace(DEFAULT_MODEL="test", MODEL_PARAMETERS={})
)
sys.modules.setdefault(
    "llm_utils",
    types.SimpleNamespace(
        initialize_llm_provider=lambda *args, **kwargs: None,
        extract_json_from_response=lambda value: value,
    ),
)
sys.modules.setdefault("config", types.SimpleNamespace(DEVELOPMENT_MODE=False))

import github


class GitHubProjectsFallbackTests(unittest.TestCase):
    def test_fallback_preserves_commit_counts(self):
        projects = [
            {
                "name": "example",
                "description": "Example project",
                "github_url": "https://github.com/example/project",
                "live_url": None,
                "technologies": ["Python"],
                "project_type": "open_source",
                "contributor_count": 3,
                "author_commit_count": 12,
                "total_commit_count": 40,
                "github_details": {"stars": 5},
            }
        ]

        original_template_manager = github.TemplateManager
        github.TemplateManager = lambda: (_ for _ in ()).throw(
            RuntimeError("force fallback")
        )
        try:
            with redirect_stdout(StringIO()):
                result = github.generate_projects_json(projects)
        finally:
            github.TemplateManager = original_template_manager

        self.assertEqual(result[0]["author_commit_count"], 12)
        self.assertEqual(result[0]["total_commit_count"], 40)


if __name__ == "__main__":
    unittest.main()
