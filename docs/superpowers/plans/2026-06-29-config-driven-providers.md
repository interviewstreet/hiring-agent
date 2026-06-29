# Config-Driven LLM Providers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user add any LLM provider or model purely by editing `providers.json` — zero Python edits — via one generic OpenAI-compatible provider.

**Architecture:** A `providers.json` config file is the single source of truth (each provider's `base_url`, key env var, models + params). `config.py` loads it. One `OpenAICompatibleProvider` POSTs to `{base_url}/chat/completions` via `requests` and adapts the response to the existing `{"message": {"content": …}}` contract. Ollama and Gemini become config entries pointed at their `/v1` compat endpoints, so the enum, both native provider classes, the two mapping dicts, and the if/else dispatch are deleted.

**Tech Stack:** Python, `requests` (already installed), stdlib `json`. No new dependencies. Tests are plain-`assert` scripts run with `python` (no test framework in this repo).

Spec: `docs/superpowers/specs/2026-06-29-config-driven-providers-design.md`

---

## File Structure

- **Create** `providers.json` — config: providers, models, params (root).
- **Create** `config.py` — loads `providers.json`; exposes `DEFAULT_MODEL`, `MODEL_PARAMETERS`, `provider_for(model)`.
- **Create** `test_config.py` — asserts for `config.py`.
- **Create** `test_providers.py` — asserts for `OpenAICompatibleProvider` (mocks `requests.post`).
- **Modify** `models.py` — add `OpenAICompatibleProvider`; delete `ModelProvider` enum, `OllamaProvider`, `GeminiProvider`. Keep `LLMProvider` Protocol.
- **Modify** `llm_utils.py` — `initialize_llm_provider` resolves via `config.provider_for`.
- **Modify** `prompt.py` — `DEFAULT_MODEL`/`MODEL_PARAMETERS` re-exported from `config`; delete enum import, `PROVIDER`, `DEFAULT_PROVIDER`, `MODEL_PROVIDER_MAPPING`, `GEMINI_API_KEY`.
- **Modify** `evaluator.py`, `pdf.py` — drop now-unused `MODEL_PROVIDER_MAPPING`, `GEMINI_API_KEY` imports.
- **Modify** `.env.example` — remove `LLM_PROVIDER`; keep `GEMINI_API_KEY`, `DEFAULT_MODEL`.
- **Modify** `requirements.txt` — remove `ollama`, `google-generativeai`.

---

## Task 1: Create `providers.json`

**Files:**
- Create: `providers.json`

- [ ] **Step 1: Write the config file**

```json
{
  "default_model": "gemma3:4b",
  "providers": {
    "ollama": {
      "base_url": "http://localhost:11434/v1",
      "api_key_env": null,
      "structured_output": "json_schema",
      "models": {
        "qwen3:1.7b":  { "temperature": 0.0, "top_p": 0.9 },
        "gemma3:1b":   { "temperature": 0.0, "top_p": 0.9 },
        "qwen3:4b":    { "temperature": 0.1, "top_p": 0.4 },
        "gemma3:4b":   { "temperature": 0.1, "top_p": 0.9 },
        "gemma3:12b":  { "temperature": 0.1, "top_p": 0.9 },
        "mistral:7b":  { "temperature": 0.1, "top_p": 0.9 }
      }
    },
    "gemini": {
      "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
      "api_key_env": "GEMINI_API_KEY",
      "structured_output": "json_schema",
      "models": {
        "gemini-2.0-flash":      { "temperature": 0.1, "top_p": 0.9 },
        "gemini-2.0-flash-lite": { "temperature": 0.1, "top_p": 0.9 },
        "gemini-2.5-flash":      { "temperature": 0.1, "top_p": 0.9 },
        "gemini-2.5-flash-lite": { "temperature": 0.1, "top_p": 0.9 },
        "gemini-2.5-pro":        { "temperature": 0.1, "top_p": 0.9 }
      }
    }
  }
}
```

- [ ] **Step 2: Verify it parses**

Run: `python -c "import json; json.load(open('providers.json')); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add providers.json
git commit -m "feat: add providers.json config for LLM providers"
```

---

## Task 2: `config.py` loader (TDD)

**Files:**
- Create: `config.py`
- Test: `test_config.py`

- [ ] **Step 1: Write the failing test**

`test_config.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `python test_config.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Write `config.py`**

```python
"""Loads providers.json and exposes provider/model resolution."""

import json
import os
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "providers.json"

with open(_CONFIG_PATH) as _f:
    _config = json.load(_f)

# Default model, overridable by env.
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", _config["default_model"])

# Flat model -> {temperature, top_p} map. Preserves the contract that
# prompt.MODEL_PARAMETERS exposed to evaluator.py / pdf.py / github.py / score.py.
MODEL_PARAMETERS = {
    model: {k: v for k, v in params.items() if k in ("temperature", "top_p")}
    for provider in _config["providers"].values()
    for model, params in provider["models"].items()
}


def provider_for(model_name: str) -> dict:
    """Resolve provider config for a model.

    Returns {base_url, api_key, structured_output, extra_body}.
    Raises ValueError if the model is unknown or its required key is unset.
    """
    for name, prov in _config["providers"].items():
        if model_name not in prov["models"]:
            continue
        api_key_env = prov.get("api_key_env")
        api_key = os.getenv(api_key_env) if api_key_env else None
        if api_key_env and not api_key:
            raise ValueError(
                f"Model '{model_name}' uses provider '{name}', which requires "
                f"env var '{api_key_env}', but it is unset."
            )
        extra_body = {
            **prov.get("extra_body", {}),
            **prov["models"][model_name].get("extra_body", {}),
        }
        return {
            "base_url": prov["base_url"].rstrip("/"),
            "api_key": api_key,
            "structured_output": prov.get("structured_output", "json_schema"),
            "extra_body": extra_body,
        }

    available = ", ".join(sorted(MODEL_PARAMETERS))
    raise ValueError(
        f"Unknown model '{model_name}'. Available models: {available}"
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `python test_config.py`
Expected: `ALL PASS`

- [ ] **Step 5: Commit**

```bash
git add config.py test_config.py
git commit -m "feat: add config.py provider/model resolver"
```

---

## Task 3: `OpenAICompatibleProvider` (TDD)

**Files:**
- Modify: `models.py` (add class; `LLMProvider` Protocol already at top)
- Test: `test_providers.py`

- [ ] **Step 1: Write the failing test**

`test_providers.py`:

```python
from unittest.mock import patch, MagicMock
from models import OpenAICompatibleProvider


def _fake_response(content="{}", status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.headers = {}
    resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    resp.raise_for_status.return_value = None
    return resp


def test_body_has_params_and_adapts_response():
    p = OpenAICompatibleProvider("http://x/v1")
    with patch("requests.post", return_value=_fake_response('{"ok":1}')) as post:
        out = p.chat(
            model="m",
            messages=[{"role": "user", "content": "hi"}],
            options={"temperature": 0.1, "top_p": 0.9, "stream": False},
        )
    body = post.call_args.kwargs["json"]
    assert body["model"] == "m"
    assert body["temperature"] == 0.1
    assert body["top_p"] == 0.9
    assert body["stream"] is False
    # response adapted to the {"message": {"content": ...}} contract
    assert out["message"]["content"] == '{"ok":1}'


def test_json_schema_format_mapping():
    p = OpenAICompatibleProvider("http://x/v1", structured_output="json_schema")
    schema = {"type": "object"}
    with patch("requests.post", return_value=_fake_response()) as post:
        p.chat(model="m", messages=[], format=schema)
    rf = post.call_args.kwargs["json"]["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["schema"] == schema


def test_json_object_format_mapping():
    p = OpenAICompatibleProvider("http://x/v1", structured_output="json_object")
    with patch("requests.post", return_value=_fake_response()) as post:
        p.chat(model="m", messages=[], format={"type": "object"})
    assert post.call_args.kwargs["json"]["response_format"] == {"type": "json_object"}


def test_none_format_omits_response_format():
    p = OpenAICompatibleProvider("http://x/v1", structured_output="none")
    with patch("requests.post", return_value=_fake_response()) as post:
        p.chat(model="m", messages=[], format={"type": "object"})
    assert "response_format" not in post.call_args.kwargs["json"]


def test_auth_header_when_key_present():
    p = OpenAICompatibleProvider("http://x/v1", api_key="sk-123")
    with patch("requests.post", return_value=_fake_response()) as post:
        p.chat(model="m", messages=[])
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer sk-123"


def test_no_auth_header_when_keyless():
    p = OpenAICompatibleProvider("http://x/v1")
    with patch("requests.post", return_value=_fake_response()) as post:
        p.chat(model="m", messages=[])
    assert "Authorization" not in post.call_args.kwargs["headers"]


def test_extra_body_merged():
    p = OpenAICompatibleProvider("http://x/v1", extra_body={"num_ctx": 32768})
    with patch("requests.post", return_value=_fake_response()) as post:
        p.chat(model="m", messages=[])
    assert post.call_args.kwargs["json"]["num_ctx"] == 32768


def test_retries_on_429_then_succeeds():
    p = OpenAICompatibleProvider("http://x/v1")
    responses = [_fake_response(status=429), _fake_response('{"done":1}')]
    with patch("requests.post", side_effect=responses), patch("time.sleep"):
        out = p.chat(model="m", messages=[])
    assert out["message"]["content"] == '{"done":1}'


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("ALL PASS")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python test_providers.py`
Expected: FAIL — `ImportError: cannot import name 'OpenAICompatibleProvider' from 'models'`

- [ ] **Step 3: Add the class to `models.py`**

Append at the end of `models.py` (after the existing classes; the `LLMProvider` Protocol stays at the top):

```python
class OpenAICompatibleProvider:
    """Generic OpenAI-chat-compatible LLM provider.

    Works for Ollama (/v1), Gemini (/v1beta/openai), OpenAI, Groq, OpenRouter,
    DeepSeek, LM Studio, vLLM, etc. via a configurable base_url. Adapts the
    response to the {"message": {"content": ...}} shape the evaluator expects.
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        structured_output: str = "json_schema",
        extra_body: Optional[Dict[str, Any]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.structured_output = structured_output
        self.extra_body = extra_body or {}

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        import requests
        import time
        import random

        options = options or {}
        body: Dict[str, Any] = {"model": model, "messages": messages, "stream": False}
        if "temperature" in options:
            body["temperature"] = options["temperature"]
        if "top_p" in options:
            body["top_p"] = options["top_p"]

        # Structured-output translation: evaluator passes format=<json schema>.
        if "format" in kwargs and self.structured_output != "none":
            schema = kwargs["format"]
            if self.structured_output == "json_schema":
                body["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {"name": "response", "schema": schema},
                }
            elif self.structured_output == "json_object":
                body["response_format"] = {"type": "json_object"}

        body.update(self.extra_body)

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.base_url}/chat/completions"

        MAX_RETRIES = 5
        BASE_DELAY = 10.0  # seconds — base for exponential backoff
        MAX_DELAY = 120.0  # cap so we never wait more than 2 minutes
        for attempt in range(MAX_RETRIES):
            response = requests.post(url, json=body, headers=headers, timeout=300)

            if response.status_code == 429 and attempt < MAX_RETRIES - 1:
                retry_after = response.headers.get("Retry-After")
                exp_delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                delay = float(retry_after) if retry_after else exp_delay
                sleep_time = round(delay * random.uniform(0.8, 1.2), 2)
                print(
                    f"[OpenAICompatibleProvider] Rate limit hit "
                    f"(attempt {attempt + 1}/{MAX_RETRIES}). Retrying in {sleep_time}s..."
                )
                time.sleep(sleep_time)
                continue

            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return {"message": {"role": "assistant", "content": content}}
```

- [ ] **Step 4: Run to verify it passes**

Run: `python test_providers.py`
Expected: `ALL PASS`

- [ ] **Step 5: Commit**

```bash
git add models.py test_providers.py
git commit -m "feat: add OpenAICompatibleProvider"
```

---

## Task 4: Rewire `initialize_llm_provider`

**Files:**
- Modify: `llm_utils.py`

- [ ] **Step 1: Replace imports and the function**

In `llm_utils.py`, replace lines 7–8 (the `from models import …` and `from prompt import …`) with:

```python
from config import provider_for
from models import OpenAICompatibleProvider
```

Then replace the entire `initialize_llm_provider` function body with:

```python
def initialize_llm_provider(model_name: str) -> Any:
    """
    Initialize an OpenAI-compatible LLM provider for the given model,
    resolving base_url / api_key / structured-output mode from providers.json.
    """
    cfg = provider_for(model_name)
    logger.info(f"🔄 Using model {model_name} via {cfg['base_url']}")
    return OpenAICompatibleProvider(
        base_url=cfg["base_url"],
        api_key=cfg["api_key"],
        structured_output=cfg["structured_output"],
        extra_body=cfg["extra_body"],
    )
```

Leave `extract_json_from_response` and the `logger` definition unchanged.

- [ ] **Step 2: Verify imports resolve**

Run: `python -c "import llm_utils; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Verify provider construction end-to-end**

Run: `python -c "from llm_utils import initialize_llm_provider; p=initialize_llm_provider('gemma3:4b'); print(type(p).__name__, p.base_url)"`
Expected: `OpenAICompatibleProvider http://localhost:11434/v1`

- [ ] **Step 4: Commit**

```bash
git add llm_utils.py
git commit -m "refactor: resolve LLM provider from config"
```

---

## Task 5: Delete legacy provider code & fix consumers

**Files:**
- Modify: `models.py`, `prompt.py`, `evaluator.py`, `pdf.py`, `.env.example`, `requirements.txt`

- [ ] **Step 1: Delete legacy classes/enum from `models.py`**

Remove the `ModelProvider` enum (lines ~6–10), the `OllamaProvider` class, and the `GeminiProvider` class. Keep the `LLMProvider` Protocol, all pydantic models, `GitHubProfile`, and the new `OpenAICompatibleProvider`. Remove `Enum` from the `from enum import Enum` line if no longer used (delete that import line).

- [ ] **Step 2: Rewrite `prompt.py` to source config from `config.py`**

Replace the top of `prompt.py` (the `from models import ModelProvider` import through the end of the `MODEL_PROVIDER_MAPPING` dict and `GEMINI_API_KEY`, i.e. lines 8–67) with:

```python
import os
from dotenv import load_dotenv
from config import DEFAULT_MODEL, MODEL_PARAMETERS

# Load environment variables (kept for any downstream os.getenv use)
load_dotenv()

# Re-exported for consumers (score.py, evaluator.py, pdf.py, github.py).
__all__ = ["DEFAULT_MODEL", "MODEL_PARAMETERS"]
```

Keep everything below line 67 (the prompt strings / templates) unchanged.

- [ ] **Step 3: Drop unused imports in `evaluator.py` and `pdf.py`**

In `evaluator.py`, change the `from prompt import (…)` block (lines 13–18) to:

```python
from prompt import (
    DEFAULT_MODEL,
    MODEL_PARAMETERS,
)
```

In `pdf.py`, change the `from prompt import (…)` block (lines 26–31) to:

```python
from prompt import (
    DEFAULT_MODEL,
    MODEL_PARAMETERS,
)
```

- [ ] **Step 4: Update `.env.example`**

Replace its contents with:

```bash
# Default model to use (must exist in providers.json).
# Ollama examples: "gemma3:4b", "qwen3:4b", "mistral:7b"
# Gemini examples: "gemini-2.5-pro", "gemini-2.5-flash"
DEFAULT_MODEL=gemma3:4b

# API keys — only needed for providers whose api_key_env is set in providers.json.
GEMINI_API_KEY=your_gemini_api_key_here
```

- [ ] **Step 5: Remove unused deps from `requirements.txt`**

Delete the lines `ollama==0.5.1` and `google-generativeai==0.4.0`.

- [ ] **Step 6: Verify the whole app imports cleanly**

Run: `python -c "import models, config, prompt, llm_utils, evaluator, pdf, github, score; print('OK')"`
Expected: `OK` (no `ImportError`, no `NameError`)

- [ ] **Step 7: Re-run both test files**

Run: `python test_config.py && python test_providers.py`
Expected: `ALL PASS` from each.

- [ ] **Step 8: Commit**

```bash
git add models.py prompt.py evaluator.py pdf.py .env.example requirements.txt
git commit -m "refactor: delete native Ollama/Gemini providers, config-only now"
```

---

## Task 6: Manual smoke test (behavior-shift validation)

**Files:** none (validation only)

- [ ] **Step 1: Start Ollama and pull the default model**

Run: `ollama pull gemma3:4b` (requires a running Ollama daemon)

- [ ] **Step 2: Run a real evaluation through the new path**

Run the project's normal entry point against a sample resume (e.g. `python score.py` or the documented run command) with `DEFAULT_MODEL=gemma3:4b`.
Expected: a valid `EvaluationData` JSON is produced — confirms structured output parses through Ollama's `/v1` compat endpoint.

- [ ] **Step 3: If context is truncated, set `extra_body`**

If output quality drops vs. the old native `num_ctx=32768`, add to the `ollama` provider in `providers.json`:

```json
"extra_body": { "num_ctx": 32768 }
```

Re-run Step 2 to confirm. Commit `providers.json` if changed.

---

## Notes

- DRY: model→params and model→provider both come from the one `providers.json`; no duplicated lists.
- YAGNI: no Python plugin registry (config-only was the chosen audience); no streaming.
- The `requests` timeout is set to 300s to accommodate slow local models.
