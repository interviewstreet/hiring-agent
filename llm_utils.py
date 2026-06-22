"""
Utility functions for LLM providers.
"""

import logging
from typing import Any, Dict, Optional
from models import ModelProvider, OllamaProvider, GeminiProvider, OpenRouterProvider
from prompt import MODEL_PROVIDER_MAPPING, PROVIDER, GEMINI_API_KEY, OPENROUTER_API_KEY

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


def initialize_llm_provider(model_name: str) -> Any:
    """
    Initialize the appropriate LLM provider based on the model name.

    Args:
        model_name: The name of the model to use

    Returns:
        An initialized LLM provider
    """
    configured_provider = (
        ModelProvider(PROVIDER)
        if PROVIDER in [provider.value for provider in ModelProvider]
        else ModelProvider.OLLAMA
    )
    model_provider = (
        configured_provider
        if configured_provider != ModelProvider.OLLAMA
        else MODEL_PROVIDER_MAPPING.get(model_name, configured_provider)
    )

    if model_provider == ModelProvider.GEMINI:
        if not GEMINI_API_KEY:
            logger.warning("⚠️ Gemini API key not found. Falling back to Ollama.")
            provider = OllamaProvider()
        else:
            logger.info(f"🔄 Using Google Gemini API provider with model {model_name}")
            provider = GeminiProvider(api_key=GEMINI_API_KEY)
    elif model_provider == ModelProvider.OPENROUTER:
        logger.info(f"🔄 Using OpenRouter API provider with model {model_name}")
        provider = OpenRouterProvider(api_key=OPENROUTER_API_KEY)
    else:
        logger.info(f"🔄 Using Ollama provider with model {model_name}")
        provider = OllamaProvider()
    return provider
