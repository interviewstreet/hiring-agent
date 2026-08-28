import importlib
import os

import config


def test_default_model_is_configured():
    assert config.DEFAULT_MODEL in config.MODEL_PARAMETERS


def test_default_model_env_override():
    original = os.environ.get("DEFAULT_MODEL")
    os.environ["DEFAULT_MODEL"] = "qwen3:4b"
    try:
        importlib.reload(config)
        assert config.DEFAULT_MODEL == "qwen3:4b"
    finally:
        if original is None:
            os.environ.pop("DEFAULT_MODEL", None)
        else:
            os.environ["DEFAULT_MODEL"] = original
        importlib.reload(config)


def test_model_parameters_flat_map():
    assert config.MODEL_PARAMETERS["gemma4:latest"] == {
        "temperature": 0.1,
        "top_p": 0.9,
    }
    assert config.MODEL_PARAMETERS["qwen3:4b"] == {"temperature": 0.1, "top_p": 0.4}
    assert set(config.MODEL_PARAMETERS["gemma4:latest"]) == {"temperature", "top_p"}


def test_provider_for_ollama_keyless():
    cfg = config.provider_for("gemma4:latest")
    assert cfg["base_url"] == "http://localhost:11434/v1"
    assert cfg["api_key"] is None
    assert cfg["structured_output"] == "json_schema"
    assert cfg["extra_body"] == {"num_ctx": 32768}


def test_provider_for_gemini_reads_key():
    original = os.environ.get("GEMINI_API_KEY")
    os.environ["GEMINI_API_KEY"] = "test-key-123"
    try:
        cfg = config.provider_for("gemini-2.5-pro")
        assert cfg["api_key"] == "test-key-123"
        assert cfg["base_url"] == "https://generativelanguage.googleapis.com/v1beta/openai"
        assert cfg["structured_output"] == "json_schema"
    finally:
        if original is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = original


def test_provider_for_missing_key_raises():
    original = os.environ.get("GEMINI_API_KEY")
    os.environ.pop("GEMINI_API_KEY", None)
    try:
        config.provider_for("gemini-2.5-pro")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "GEMINI_API_KEY" in str(e)
    finally:
        if original is not None:
            os.environ["GEMINI_API_KEY"] = original


def test_unknown_model_raises_with_list():
    try:
        config.provider_for("no-such-model")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "no-such-model" in str(e)
        assert "gemma4:latest" in str(e)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("ALL PASS")
