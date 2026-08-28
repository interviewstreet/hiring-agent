from unittest.mock import MagicMock, patch

from models import OpenAICompatibleProvider


def _mock_response(payload=None, status_code=200, headers=None):
    response = MagicMock()
    response.status_code = status_code
    response.headers = headers or {}
    response.json.return_value = payload or {
        "choices": [{"message": {"content": '{"ok": true}'}}]
    }
    return response


def test_json_schema_response_format():
    response = _mock_response()
    with patch("requests.post", return_value=response) as post:
        provider = OpenAICompatibleProvider(
            base_url="http://localhost:11434/v1",
            structured_output="json_schema",
        )
        result = provider.chat(
            model="gemma4:latest",
            messages=[{"role": "user", "content": "hi"}],
            options={"temperature": 0.1, "top_p": 0.9},
            format={"type": "object"},
        )

    body = post.call_args.kwargs["json"]
    assert body["model"] == "gemma4:latest"
    assert body["temperature"] == 0.1
    assert body["top_p"] == 0.9
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["schema"] == {"type": "object"}
    assert result == {"message": {"role": "assistant", "content": '{"ok": true}'}}


def test_json_object_response_format():
    response = _mock_response()
    with patch("requests.post", return_value=response) as post:
        provider = OpenAICompatibleProvider(
            base_url="https://example.com/v1",
            structured_output="json_object",
        )
        provider.chat(
            model="test-model",
            messages=[{"role": "user", "content": "hi"}],
            format={"type": "object"},
        )

    body = post.call_args.kwargs["json"]
    assert body["response_format"] == {"type": "json_object"}


def test_structured_output_none_omits_response_format():
    response = _mock_response()
    with patch("requests.post", return_value=response) as post:
        provider = OpenAICompatibleProvider(
            base_url="https://example.com/v1",
            structured_output="none",
        )
        provider.chat(
            model="test-model",
            messages=[{"role": "user", "content": "hi"}],
            format={"type": "object"},
        )

    body = post.call_args.kwargs["json"]
    assert "response_format" not in body


def test_extra_body_and_authorization_header():
    response = _mock_response()
    with patch("requests.post", return_value=response) as post:
        provider = OpenAICompatibleProvider(
            base_url="https://example.com/v1/",
            api_key="secret",
            extra_body={"num_ctx": 32768},
        )
        provider.chat(
            model="test-model",
            messages=[{"role": "user", "content": "hi"}],
        )

    assert post.call_args.args[0] == "https://example.com/v1/chat/completions"
    assert post.call_args.kwargs["json"]["num_ctx"] == 32768
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer secret"


def test_unexpected_response_shape_raises():
    response = _mock_response(payload={"unexpected": True})
    with patch("requests.post", return_value=response):
        provider = OpenAICompatibleProvider(base_url="https://example.com/v1")
        try:
            provider.chat(
                model="test-model",
                messages=[{"role": "user", "content": "hi"}],
            )
            assert False, "expected ValueError"
        except ValueError as e:
            assert "Unexpected response shape" in str(e)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("ALL PASS")
