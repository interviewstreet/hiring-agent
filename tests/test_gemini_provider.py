"""GeminiProvider migrated to the google-genai SDK (#2 provider parity).

Two real bugs are pinned here:
  1. The system message must become Gemini's ``system_instruction`` -- NOT be
     replayed as a "model" turn (the legacy bug).
  2. The ``format`` kwarg (a JSON schema) must drive structured output via
     ``response_mime_type`` + ``response_schema``, matching Ollama's behavior.

Request construction is unit-tested through the pure ``build_gemini_request``
helper; the provider's call contract and rate-limit retry are tested with an
injected fake client, so no API key or network is involved.
"""

import pytest
from google.genai import errors

from models import GeminiProvider, build_gemini_request


MESSAGES = [
    {"role": "system", "content": "You are a strict scorer."},
    {"role": "user", "content": "Score this resume."},
]


def test_system_message_becomes_system_instruction_not_a_turn():
    req = build_gemini_request(MESSAGES, {"temperature": 0.1, "top_p": 0.9}, {})

    assert req["system_instruction"] == "You are a strict scorer."
    # The system text must not leak into the conversation contents.
    for content in req["contents"]:
        assert "strict scorer" not in str(content)
    # Only the non-system turns remain.
    assert len(req["contents"]) == 1


def test_role_mapping_user_and_assistant():
    messages = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    req = build_gemini_request(messages, {}, {})

    roles = [c["role"] for c in req["contents"]]
    assert roles == ["user", "model"]
    assert req["system_instruction"] is None
    # google-genai requires parts to be Part-shaped dicts ({"text": ...}),
    # not bare strings -- the live API rejects bare strings inside a role dict.
    assert req["contents"][0]["parts"] == [{"text": "hi"}]
    assert req["contents"][1]["parts"] == [{"text": "hello"}]


def test_format_kwarg_enables_structured_output():
    schema = {"type": "object", "properties": {"score": {"type": "integer"}}}
    req = build_gemini_request(MESSAGES, {}, {"format": schema})

    gen = req["generation_config"]
    assert gen["response_mime_type"] == "application/json"
    assert gen["response_schema"] == schema


def test_generation_params_mapped_from_options():
    req = build_gemini_request(MESSAGES, {"temperature": 0.3, "top_p": 0.5}, {})

    gen = req["generation_config"]
    assert gen["temperature"] == 0.3
    assert gen["top_p"] == 0.5
    # Without a format kwarg, no structured-output keys are forced on.
    assert "response_schema" not in gen


class _FakeModels:
    def __init__(self, text='{"ok": true}'):
        self._text = text
        self.calls = []

    def generate_content(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})

        class _Resp:
            text = self._text

        return _Resp()


class _FakeClient:
    def __init__(self, text='{"ok": true}'):
        self.models = _FakeModels(text)


def test_chat_returns_ollama_compatible_shape():
    client = _FakeClient(text='{"score": 5}')
    provider = GeminiProvider(api_key="unused", client=client)

    result = provider.chat(
        model="gemini-2.0-flash",
        messages=MESSAGES,
        options={"temperature": 0.1, "top_p": 0.9},
    )

    assert result["message"]["content"] == '{"score": 5}'
    # The system instruction reached the SDK config, not the contents.
    config = client.models.calls[0]["config"]
    assert config.system_instruction == "You are a strict scorer."


class _FlakyModels:
    """Raises a 429 once, then succeeds."""

    def __init__(self):
        self.attempts = 0

    def generate_content(self, model, contents, config):
        self.attempts += 1
        if self.attempts == 1:
            raise errors.APIError(
                429,
                {
                    "error": {
                        "message": "Resource exhausted, retry in 1s",
                        "status": "RESOURCE_EXHAUSTED",
                    }
                },
            )

        class _Resp:
            text = "recovered"

        return _Resp()


class _FlakyClient:
    def __init__(self):
        self.models = _FlakyModels()


def test_chat_retries_on_rate_limit(monkeypatch):
    # Don't actually sleep during the backoff.
    monkeypatch.setattr("models.time.sleep", lambda *_a, **_k: None)
    client = _FlakyClient()
    provider = GeminiProvider(api_key="unused", client=client)

    result = provider.chat(model="gemini-2.0-flash", messages=MESSAGES, options={})

    assert result["message"]["content"] == "recovered"
    assert client.models.attempts == 2
