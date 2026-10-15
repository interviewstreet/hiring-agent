"""Offline checks for the configured OpenRouter Gemini models.

Run with: python -m unittest discover -s tests -v
The tests never load a real .env or send HTTP requests.
"""

import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
PRO_MODEL = "google/gemini-3.1-pro-preview"
FLASH_MODEL = "google/gemini-3.8-flash"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OpenRouterConfigTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {}, clear=True))
        self.dotenv_loader = self.enterContext(patch("dotenv.load_dotenv"))
        self.config = load_module("test_config", ROOT / "config.py")

    def initialize(self, model):
        with patch.dict(sys.modules, {"config": self.config}):
            utils = load_module("test_llm_utils", ROOT / "llm_utils.py")
        return utils.initialize_llm_provider(model)

    def test_default_is_openrouter_pro(self):
        self.assertEqual(self.config.DEFAULT_MODEL, PRO_MODEL)

    def test_environment_can_select_flash(self):
        os.environ["DEFAULT_MODEL"] = FLASH_MODEL
        config = load_module("test_flash_config", ROOT / "config.py")
        self.assertEqual(config.DEFAULT_MODEL, FLASH_MODEL)

    def test_both_models_resolve_using_shell_key(self):
        os.environ["OPENROUTER_API_KEY"] = "offline-test-key"
        for model in (PRO_MODEL, FLASH_MODEL):
            with self.subTest(model=model):
                resolved = self.config.provider_for(model)
                self.assertEqual(resolved["base_url"], "https://openrouter.ai/api/v1")
                self.assertEqual(resolved["api_key"], "offline-test-key")
                self.assertEqual(resolved["structured_output"], "json_schema")
                self.assertEqual(
                    self.config.MODEL_PARAMETERS[model]["temperature"], 0.1
                )

    def test_missing_shell_key_has_actionable_error(self):
        for model in (PRO_MODEL, FLASH_MODEL):
            with self.subTest(model=model):
                with self.assertRaisesRegex(ValueError, "OPENROUTER_API_KEY"):
                    self.config.provider_for(model)

    def test_dotenv_does_not_replace_shell_key(self):
        # Exercise python-dotenv's real default precedence without reading .env.
        from io import StringIO

        os.environ["OPENROUTER_API_KEY"] = "offline-shell-key"
        load_dotenv(stream=StringIO("OPENROUTER_API_KEY=offline-file-key\n"))
        self.assertEqual(os.environ["OPENROUTER_API_KEY"], "offline-shell-key")
        self.dotenv_loader.assert_called_once_with(ROOT / ".env")

    def test_existing_local_provider_remains_available(self):
        resolved = self.config.provider_for("gemma4:latest")
        self.assertEqual(resolved["base_url"], "http://localhost:11434/v1")
        self.assertIsNone(resolved["api_key"])

    def test_both_models_send_structured_requests_without_network(self):
        os.environ["OPENROUTER_API_KEY"] = "offline-test-key"
        schema = {"type": "object", "properties": {"score": {"type": "number"}}}
        messages = [{"role": "user", "content": "Return a JSON score."}]
        response = Mock(status_code=200)
        response.json.return_value = {
            "choices": [{"message": {"content": '{"score": 80}'}}]
        }
        with patch("requests.post", return_value=response) as post:
            for model in (PRO_MODEL, FLASH_MODEL):
                with self.subTest(model=model):
                    provider = self.initialize(model)
                    result = provider.chat(
                        model=model,
                        messages=messages,
                        options=self.config.MODEL_PARAMETERS[model],
                        format=schema,
                    )
                    args, kwargs = post.call_args
                    self.assertEqual(
                        args[0], "https://openrouter.ai/api/v1/chat/completions"
                    )
                    self.assertEqual(
                        kwargs["headers"]["Authorization"], "Bearer offline-test-key"
                    )
                    body = kwargs["json"]
                    self.assertEqual(body["model"], model)
                    self.assertEqual(body["messages"], messages)
                    self.assertFalse(body["stream"])
                    self.assertEqual(body["temperature"], 0.1)
                    self.assertEqual(body["response_format"]["type"], "json_schema")
                    self.assertEqual(
                        body["response_format"]["json_schema"]["schema"], schema
                    )
                    self.assertEqual(result["message"]["content"], '{"score": 80}')
            self.assertEqual(post.call_count, 2)


if __name__ == "__main__":
    unittest.main()
