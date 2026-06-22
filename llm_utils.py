"""
Utility functions for LLM providers.
"""

import logging
from typing import Any, Dict, Optional
from models import (
    ModelProvider,
    OllamaProvider,
    GeminiProvider,
    CliLLMProvider,
)
from prompt import (
    MODEL_PROVIDER_MAPPING,
    GEMINI_API_KEY,
    PROVIDER,
    CLAUDE_CODE_COMMAND,
    CLAUDE_CODE_MODEL,
    CLAUDE_CODE_TIMEOUT_SECONDS,
    CODEX_COMMAND,
    CODEX_MODEL,
    CODEX_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


def extract_json_from_response(response_text: str) -> str:
    """
    Extract JSON content from markdown code blocks.

    Args:
        response_text: Text that may contain JSON wrapped in markdown code blocks

    Returns:
        Text with markdown code block syntax removed
    """

    response_text = response_text.strip()
    if "<think>" in response_text:
        think_start = response_text.find("<think>")
        think_end = response_text.find("</think>")
        if think_start != -1 and think_end != -1:
            response_text = response_text[:think_start] + response_text[think_end + 8 :]

    # Remove leading ```json if present
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    # Remove trailing ``` if present
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    return response_text


CLI_PROVIDER_SETTINGS = {
    ModelProvider.CLAUDE_CODE.value: {
        "command": CLAUDE_CODE_COMMAND,
        "timeout": CLAUDE_CODE_TIMEOUT_SECONDS,
        "model": CLAUDE_CODE_MODEL,
        "label": "Claude Code CLI",
    },
    ModelProvider.CODEX.value: {
        "command": CODEX_COMMAND,
        "timeout": CODEX_TIMEOUT_SECONDS,
        "model": CODEX_MODEL,
        "label": "Codex CLI",
    },
}


def _build_cli_provider(provider_name: str) -> Any:
    """Construct a shared CLI provider from environment configuration."""
    settings = CLI_PROVIDER_SETTINGS[provider_name]
    logger.info(f"Using {settings['label']} provider (local authenticated session)")
    return CliLLMProvider(
        backend=provider_name,
        command=settings["command"],
        timeout=settings["timeout"],
        model=settings["model"],
    )


def initialize_llm_provider(model_name: str) -> Any:
    """
    Initialize the appropriate LLM provider.

    Selection order:
      1. An explicit CLI provider (``LLM_PROVIDER=claude_code`` or
         ``LLM_PROVIDER=codex``) wins regardless of the model name. (Previously
         provider selection was driven solely by the model mapping, so
         LLM_PROVIDER was ignored.)
      2. Otherwise the provider is inferred from ``MODEL_PROVIDER_MAPPING``:
         Gemini (requires ``GEMINI_API_KEY``, else falls back to Ollama),
         Claude Code, or Ollama (the default fallback).

    Args:
        model_name: The name of the model to use.

    Returns:
        An initialized LLM provider implementing the ``chat`` interface.
    """
    # 1. Explicit provider selection wins; this is what makes CLI-backed
    #    providers take effect even when DEFAULT_MODEL is just a logical label.
    if PROVIDER in CLI_PROVIDER_SETTINGS:
        return _build_cli_provider(PROVIDER)

    # 2. Infer the provider from the model mapping (legacy behavior).
    model_provider = MODEL_PROVIDER_MAPPING.get(model_name, ModelProvider.OLLAMA)

    if model_provider.value in CLI_PROVIDER_SETTINGS:
        return _build_cli_provider(model_provider.value)

    if model_provider == ModelProvider.GEMINI:
        if not GEMINI_API_KEY:
            logger.warning("Gemini API key not found. Falling back to Ollama.")
            return OllamaProvider()
        logger.info(f"Using Google Gemini API provider with model {model_name}")
        return GeminiProvider(api_key=GEMINI_API_KEY)

    logger.info(f"Using Ollama provider with model {model_name}")
    return OllamaProvider()
