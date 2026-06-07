"""
Utility functions for LLM providers.
"""

import logging
from typing import Any, Dict, Optional
from models import (
    ModelProvider,
    OllamaProvider,
    GeminiProvider,
    AnthropicProvider,
    ClaudeCLIProvider,
    GeminiCLIProvider,
)
from prompt import (
    MODEL_PROVIDER_MAPPING,
    PROVIDER,
    PROVIDER_EXPLICITLY_SET,
    GEMINI_API_KEY,
    ANTHROPIC_API_KEY,
    CLAUDE_CLI_COMMAND,
    GEMINI_CLI_COMMAND,
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


def _resolve_provider_type(model_name: str) -> ModelProvider:
    """Decide which provider to use for a given model.

    An explicit ``LLM_PROVIDER`` environment variable is authoritative. When it
    is not set, the provider is inferred from ``MODEL_PROVIDER_MAPPING`` (the
    original, backwards-compatible behaviour).
    """
    if PROVIDER_EXPLICITLY_SET:
        try:
            return ModelProvider(PROVIDER)
        except ValueError:
            logger.warning(
                f"⚠️ Unknown LLM_PROVIDER '{PROVIDER}'. Inferring provider from the model name."
            )
    return MODEL_PROVIDER_MAPPING.get(model_name, ModelProvider.OLLAMA)


def initialize_llm_provider(model_name: str) -> Any:
    """
    Initialize the appropriate LLM provider for the given model.

    Supports Ollama, the Google Gemini API, the Anthropic Claude API, and the
    Claude Code / Gemini command-line tools. If a provider's prerequisite
    (an API key or an installed CLI) is missing, it falls back to Ollama.

    Args:
        model_name: The name of the model to use

    Returns:
        An initialized LLM provider.
    """
    provider_type = _resolve_provider_type(model_name)

    try:
        if provider_type == ModelProvider.GEMINI:
            if not GEMINI_API_KEY:
                raise RuntimeError("GEMINI_API_KEY is not set")
            logger.info(f"🔄 Using Google Gemini API provider with model {model_name}")
            return GeminiProvider(api_key=GEMINI_API_KEY)

        if provider_type == ModelProvider.CLAUDE:
            if not ANTHROPIC_API_KEY:
                raise RuntimeError("ANTHROPIC_API_KEY is not set")
            logger.info(
                f"🔄 Using Anthropic Claude API provider with model {model_name}"
            )
            return AnthropicProvider(api_key=ANTHROPIC_API_KEY)

        if provider_type == ModelProvider.CLAUDE_CLI:
            logger.info(f"🔄 Using Claude CLI provider with model {model_name}")
            return ClaudeCLIProvider(command=CLAUDE_CLI_COMMAND)

        if provider_type == ModelProvider.GEMINI_CLI:
            logger.info(f"🔄 Using Gemini CLI provider with model {model_name}")
            return GeminiCLIProvider(command=GEMINI_CLI_COMMAND)
    except Exception as e:
        logger.warning(
            f"⚠️ Could not initialize the '{provider_type.value}' provider ({e}). "
            f"Falling back to Ollama."
        )
        return OllamaProvider()

    logger.info(f"🔄 Using Ollama provider with model {model_name}")
    return OllamaProvider()
