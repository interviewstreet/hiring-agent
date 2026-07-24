import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


def load_extract_json_from_response():
    models = types.ModuleType("models")
    models.ModelProvider = types.SimpleNamespace(OLLAMA="ollama")
    models.OllamaProvider = object
    models.GeminiProvider = object

    prompt = types.ModuleType("prompt")
    prompt.MODEL_PROVIDER_MAPPING = {}
    prompt.GEMINI_API_KEY = None

    module_path = Path(__file__).parents[1] / "llm_utils.py"
    spec = importlib.util.spec_from_file_location("llm_utils", module_path)
    module = importlib.util.module_from_spec(spec)

    with patch.dict(sys.modules, {"models": models, "prompt": prompt}):
        spec.loader.exec_module(module)

    return module.extract_json_from_response


extract_json_from_response = load_extract_json_from_response()


class ExtractJsonFromResponseTests(unittest.TestCase):
    def test_supported_response_shapes_are_valid_json(self):
        responses = {
            "plain JSON": '{"ok": true}',
            "fenced JSON": '```json\n{"ok": true}\n```',
            "think block then fenced JSON": (
                '<think>reasoning</think>\n```json\n{"ok": true}\n```'
            ),
        }

        for name, response in responses.items():
            with self.subTest(name=name):
                cleaned = extract_json_from_response(response)
                self.assertEqual(json.loads(cleaned), {"ok": True})


if __name__ == "__main__":
    unittest.main()
