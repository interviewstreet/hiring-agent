import json
import os
import unittest
from unittest.mock import Mock, patch

import config
from llm_utils import initialize_llm_provider
from models import OpenAICompatibleProvider


class GeminiConfigurationTests(unittest.TestCase):
    def test_default_model_is_gemini(self):
        self.assertEqual(config._config["default_model"], "gemini-flash-latest")

    def test_gemini_requires_key_without_leaking_it(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "GEMINI_API_KEY") as error:
                config.provider_for("gemini-flash-latest")
        self.assertNotIn("Bearer", str(error.exception))

    def test_gemini_provider_is_resolved_from_environment(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-only-key"}, clear=True):
            provider = initialize_llm_provider("gemini-flash-latest")
        self.assertEqual(
            provider.base_url,
            "https://generativelanguage.googleapis.com/v1beta/openai",
        )
        self.assertEqual(provider.api_key, "test-only-key")
        self.assertEqual(provider.structured_output, "json_schema")


class GeminiRequestContractTests(unittest.TestCase):
    @patch("requests.post")
    def test_structured_output_request_and_response_contract(self, post):
        response = Mock(status_code=200, headers={})
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": '{"ok": true}'}}]
        }
        post.return_value = response
        provider = OpenAICompatibleProvider(
            "https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key="test-only-key",
        )

        result = provider.chat(
            model="gemini-flash-latest",
            messages=[{"role": "user", "content": "Return JSON"}],
            options={"temperature": 0.0, "top_p": 0.9},
            format={"type": "object", "properties": {"ok": {"type": "boolean"}}},
        )

        url = post.call_args.args[0]
        request = post.call_args.kwargs
        self.assertEqual(
            url,
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        )
        self.assertEqual(request["headers"]["Authorization"], "Bearer test-only-key")
        self.assertEqual(request["json"]["response_format"]["type"], "json_schema")
        self.assertFalse(request["json"]["stream"])
        self.assertEqual(json.loads(result["message"]["content"]), {"ok": True})

    @patch("requests.post")
    def test_unexpected_response_fails_clearly(self, post):
        response = Mock(status_code=200, headers={})
        response.raise_for_status.return_value = None
        response.json.return_value = {"unexpected": "shape"}
        post.return_value = response
        provider = OpenAICompatibleProvider("https://example.invalid")

        with self.assertRaisesRegex(ValueError, "Unexpected response shape"):
            provider.chat(model="model", messages=[])


if __name__ == "__main__":
    unittest.main()
