"""
Utility functions for LLM providers.
"""

import logging
from typing import Any, Dict, Optional
from models import (
    ModelProvider,
    OllamaProvider,
    GeminiProvider,
    OpenAICompatibleProvider,
)
from prompt import (
    PROVIDER,
    MODEL_PROVIDER_MAPPING,
    PROVIDER_BASE_URLS,
    PROVIDER_API_KEYS,
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
    think_tag = "redacted" + "_thinking"
    if f"<{think_tag}>" in response_text:
        think_start = response_text.find(f"<{think_tag}>")
        think_end = response_text.find(f"</{think_tag}>")
        if think_start != -1 and think_end != -1:
            response_text = (
                response_text[:think_start]
                + response_text[think_end + len(f"</{think_tag}>") :]
            )

    # Remove leading ```json if present
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    # Remove trailing ``` if present
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    return response_text


def _resolve_provider(model_name: str) -> ModelProvider:
    """Resolve provider from env var or model mapping."""
    try:
        provider = ModelProvider(PROVIDER)
    except ValueError:
        provider = ModelProvider.OLLAMA

    mapped = MODEL_PROVIDER_MAPPING.get(model_name)
    if mapped:
        provider = mapped

    return provider


def initialize_llm_provider(model_name: str) -> Any:
    """
    Initialize the appropriate LLM provider based on config and model name.

    Args:
        model_name: The name of the model to use

    Returns:
        An initialized LLM provider
    """
    provider_type = _resolve_provider(model_name)

    if provider_type == ModelProvider.GEMINI:
        api_key = PROVIDER_API_KEYS[ModelProvider.GEMINI]
        if not api_key:
            logger.warning("Gemini API key not found. Falling back to Ollama.")
            return OllamaProvider()
        logger.info(f"Using Google Gemini with model {model_name}")
        return GeminiProvider(api_key=api_key)

    if provider_type in PROVIDER_BASE_URLS:
        api_key = PROVIDER_API_KEYS[provider_type]
        if not api_key:
            logger.warning(
                f"{provider_type.value} API key not found. Falling back to Ollama."
            )
            return OllamaProvider()
        logger.info(f"Using {provider_type.value} with model {model_name}")
        return OpenAICompatibleProvider(
            api_key=api_key,
            base_url=PROVIDER_BASE_URLS[provider_type],
        )

    logger.info(f"Using Ollama with model {model_name}")
    return OllamaProvider()
