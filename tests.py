import unittest
from unittest.mock import patch, MagicMock
from models import ModelProvider, OpenCodeProvider
from llm_utils import initialize_llm_provider


class TestOpenCodeProvider(unittest.TestCase):
    def setUp(self):
        self.api_key = "test_key"
        self.provider = OpenCodeProvider(self.api_key)

    @patch("requests.post")
    def test_chat_success(self, mock_post):
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        mock_post.return_value = mock_response

        messages = [
            {"role": "system", "content": "You are an assistant"},
            {"role": "user", "content": "Hello"},
            {"role": "model", "content": "Hi"},
        ]

        response = self.provider.chat(
            model="deepseek-v4-flash",
            messages=messages,
            options={"temperature": 0.5, "top_p": 0.8},
        )

        # Assert response structure
        self.assertEqual(
            response, {"message": {"role": "assistant", "content": "Test response"}}
        )

        # Verify POST request parameters
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://opencode.ai/zen/go/v1/chat/completions")
        self.assertEqual(kwargs["headers"]["Authorization"], f"Bearer {self.api_key}")

        # Verify message roles conversion (model -> assistant)
        payload = kwargs["json"]
        self.assertEqual(payload["model"], "deepseek-v4-flash")
        self.assertEqual(payload["temperature"], 0.5)
        self.assertEqual(payload["top_p"], 0.8)
        self.assertEqual(payload["messages"][2]["role"], "assistant")

    @patch("requests.post")
    def test_chat_failure(self, mock_post):
        # Mock API failure
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_post.return_value = mock_response

        with self.assertRaises(Exception):
            self.provider.chat(
                model="deepseek-v4-flash",
                messages=[{"role": "user", "content": "Hello"}],
            )


class TestLLMProviderInitialization(unittest.TestCase):
    @patch("llm_utils.PROVIDER", "opencode")
    @patch("llm_utils.OPENCODE_API_KEY", "test_key")
    def test_initialize_opencode_by_provider(self):
        provider = initialize_llm_provider("some-model")
        self.assertIsInstance(provider, OpenCodeProvider)
        self.assertEqual(provider.api_key, "test_key")

    @patch("llm_utils.PROVIDER", "ollama")
    @patch("llm_utils.OPENCODE_API_KEY", "")
    @patch(
        "llm_utils.MODEL_PROVIDER_MAPPING",
        {"deepseek-v4-flash": ModelProvider.OPENCODE},
    )
    def test_initialize_opencode_fallback_without_key(self):
        # Should fallback to Ollama if no key
        provider = initialize_llm_provider("deepseek-v4-flash")
        from models import OllamaProvider

        self.assertIsInstance(provider, OllamaProvider)


if __name__ == "__main__":
    unittest.main()
