import sys
import types
import unittest


sys.modules.setdefault("requests", types.SimpleNamespace())
sys.modules.setdefault("models", types.SimpleNamespace(GitHubProfile=object))
sys.modules.setdefault(
    "pdf",
    types.SimpleNamespace(
        logger=types.SimpleNamespace(warning=lambda *args, **kwargs: None)
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
from github import _parse_rate_limit_header


class GitHubRateLimitHeaderTests(unittest.TestCase):
    def test_parse_valid_rate_limit_header(self):
        self.assertEqual(
            _parse_rate_limit_header("42", "X-RateLimit-Remaining"),
            42,
        )

    def test_parse_missing_rate_limit_header(self):
        self.assertIsNone(
            _parse_rate_limit_header(None, "X-RateLimit-Remaining"),
        )

    def test_parse_invalid_rate_limit_header(self):
        self.assertIsNone(
            _parse_rate_limit_header("not-an-int", "X-RateLimit-Remaining"),
        )


if __name__ == "__main__":
    unittest.main()
