# Config-Driven LLM Providers — Design

**Date:** 2026-06-29
**Status:** Approved (design)

## Problem

Adding an LLM provider or model today requires editing Python in four places:
the `ModelProvider` enum and a hand-written provider class (`models.py`), the
`MODEL_PROVIDER_MAPPING` + `MODEL_PARAMETERS` dicts (`prompt.py`), and the
if/else dispatch in `initialize_llm_provider` (`llm_utils.py`). Only Ollama and
Gemini are supported. There is no way for a user to point the tool at another
provider (OpenAI, Groq, OpenRouter, DeepSeek, LM Studio, vLLM, …) without
writing code.

## Goal

A user can add **any provider or model purely through configuration — zero
Python edits**. Achieved by leaning on the fact that nearly every LLM API today
is OpenAI-chat-compatible, *including* the two already supported: Ollama exposes
`http://localhost:11434/v1` and Gemini exposes `…/v1beta/openai/`. One generic
OpenAI-compatible provider pointed at a configurable `base_url` covers them all.

## Out of Scope

- Non-OpenAI-compatible APIs (e.g. a bespoke SDK). A user needing one would
  still have to write code; this design does not provide a Python plugin
  registry. (Explicitly decided against — config-only was the chosen audience.)
- Streaming responses (the evaluator uses `stream: false`).
- A config UI. Editing `providers.json` by hand is the interface.

## Constraints

- **Zero new dependencies.** `requests` (already present) makes the HTTP call;
  stdlib `json` parses the config. The `openai` SDK and a YAML parser are both
  deliberately avoided.
- Must preserve the existing call contract: `evaluator.py` calls
  `provider.chat(model=…, messages=…, options=…, format=<schema>)` and reads
  `response["message"]["content"]`.

## Approach (chosen: A)

One generic provider; configuration drives everything. Ollama and Gemini become
config entries pointed at their `/v1` compat endpoints, so all provider-specific
Python is deleted.

Approaches B (generic provider *alongside* native Ollama/Gemini) and C (same as
A but with the official `openai` SDK) were rejected: B keeps two code paths and
the enum/dicts; C adds a dependency for what `requests` already does in ~15
lines.

## Components

### `providers.json` (repo root) — single source of truth

```json
{
  "default_model": "gemma3:4b",
  "providers": {
    "ollama": {
      "base_url": "http://localhost:11434/v1",
      "api_key_env": null,
      "structured_output": "json_schema",
      "models": {
        "gemma3:4b":  { "temperature": 0.1, "top_p": 0.9 },
        "qwen3:4b":   { "temperature": 0.1, "top_p": 0.4 },
        "mistral:7b": { "temperature": 0.1, "top_p": 0.9 }
      }
    },
    "gemini": {
      "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
      "api_key_env": "GEMINI_API_KEY",
      "structured_output": "json_schema",
      "models": {
        "gemini-2.5-pro":   { "temperature": 0.1, "top_p": 0.9 },
        "gemini-2.5-flash": { "temperature": 0.1, "top_p": 0.9 }
      }
    }
  }
}
```

- Ships pre-populated with the current Ollama + Gemini models so existing
  behavior is preserved out of the box.
- A model lives *under* its provider → implicitly replaces
  `MODEL_PROVIDER_MAPPING`.
- Per-model params replace `MODEL_PARAMETERS`.
- `api_key_env` names the env var holding the secret (`null`/omitted for keyless
  local Ollama). Secrets stay in `.env`.
- `structured_output` (per provider): `"json_schema"` (default), `"json_object"`,
  or `"none"`. Providers differ in what they accept; this knob prevents silent
  breakage.
- `extra_body` (optional, per provider or per model): dict merged into the
  request body. Escape hatch for provider-specific fields the compat endpoint
  needs (e.g. preserving Ollama context size).

### `config.py` (new)

Loads `providers.json` once and exposes:

- `default_model` — overridable by `DEFAULT_MODEL` env var.
- `model_params(model)` → `{temperature, top_p}` for that model.
- `provider_for(model)` → resolved `{base_url, api_key, structured_output,
  extra_body}` for the model's provider (api_key read from `os.getenv(api_key_env)`).
- Raises a clear `ValueError` listing available models when a model is unknown.

### `OpenAICompatibleProvider` (in `models.py`)

One class implementing the existing `LLMProvider` Protocol. `chat()`:

1. Builds the OpenAI body: `model`, `messages`, `temperature`, `top_p`,
   `stream: false`, plus merged `extra_body`.
2. Translates the `format=<schema>` kwarg → `response_format` per the provider's
   `structured_output` setting:
   - `json_schema` → `{"type": "json_schema", "json_schema": {"name": "response",
     "schema": <schema>}}`
   - `json_object` → `{"type": "json_object"}`
   - `none` → omit `response_format`
3. POSTs to `{base_url}/chat/completions` via `requests`; sends
   `Authorization: Bearer <key>` only when a key exists.
4. Retries on HTTP 429 with exponential backoff + jitter (generalized from the
   existing Gemini code; honors `Retry-After`).
5. Adapts the response back to `{"message": {"role": "assistant", "content": …}}`
   — the shape `evaluator.py` already consumes.

### `initialize_llm_provider(model_name)` (`llm_utils.py`)

Becomes: `provider_for(model_name)` → instantiate
`OpenAICompatibleProvider(base_url, api_key)`. A missing required key raises a
clear error rather than today's silent fallback to Ollama.

## Deletions

- `ModelProvider` enum, `OllamaProvider`, `GeminiProvider` (`models.py`)
- `MODEL_PROVIDER_MAPPING`, `MODEL_PARAMETERS`, `PROVIDER` validation (`prompt.py`)
- if/else dispatch in `initialize_llm_provider` (`llm_utils.py`)
- `ollama` and `google-generativeai` from `requirements.txt`
- `LLM_PROVIDER` from `.env.example` (model now implies provider); keeps
  `GEMINI_API_KEY` and `DEFAULT_MODEL`.

The `LLMProvider` Protocol stays — the generic provider satisfies it.

## Error Handling

- Unknown model → `ValueError` listing available models.
- Provider needs a key but env var is unset/empty → clear error (no silent
  fallback).
- HTTP errors → surfaced via `raise_for_status()`.
- 429 → backoff retry; exhausted retries re-raise.

## Testing

- `test_providers.py`: mock `requests.post`; assert request body shape
  (temperature/top_p, `response_format` mapping for each `structured_output`
  mode, `extra_body` merge) and response adaptation to the `message.content`
  contract. Plain `assert`s, no framework.
- One manual smoke test against local Ollama `/v1` to confirm the native→compat
  behavior shift (structured output + context) is acceptable.

## Known Risk

Ollama/Gemini now route through their `/v1` compat endpoints, not native SDKs.
Native `num_ctx=32768` is not a compat field — if resumes need larger context,
set it via `extra_body`. The smoke test confirms structured output still parses.
