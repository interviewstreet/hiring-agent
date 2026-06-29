import os
import config


def test_default_model():
    assert config.DEFAULT_MODEL == "gemma3:4b"


def test_model_parameters_flat_map():
    assert config.MODEL_PARAMETERS["gemma3:4b"] == {"temperature": 0.1, "top_p": 0.9}
    assert config.MODEL_PARAMETERS["qwen3:4b"] == {"temperature": 0.1, "top_p": 0.4}
    # only temperature/top_p surface here, nothing else
    assert set(config.MODEL_PARAMETERS["gemma3:4b"]) == {"temperature", "top_p"}


def test_provider_for_ollama_keyless():
    cfg = config.provider_for("gemma3:4b")
    assert cfg["base_url"] == "http://localhost:11434/v1"
    assert cfg["api_key"] is None
    assert cfg["structured_output"] == "json_schema"
    assert cfg["extra_body"] == {}


def test_provider_for_gemini_reads_key():
    os.environ["GEMINI_API_KEY"] = "test-key-123"
    cfg = config.provider_for("gemini-2.5-pro")
    assert cfg["api_key"] == "test-key-123"
    assert cfg["base_url"].endswith("/openai")


def test_provider_for_missing_key_raises():
    os.environ.pop("GEMINI_API_KEY", None)
    try:
        config.provider_for("gemini-2.5-pro")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "GEMINI_API_KEY" in str(e)


def test_unknown_model_raises_with_list():
    try:
        config.provider_for("no-such-model")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "no-such-model" in str(e)
        assert "gemma3:4b" in str(e)  # lists available models


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("ALL PASS")
