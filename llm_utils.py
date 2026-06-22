"""
Utility functions for LLM providers.
"""

import logging
import os
from typing import Any, Dict, Optional
from models import (
    ModelProvider,
    OllamaProvider,
    GeminiProvider,
    OpenAICompatibleProvider,
)
from prompt import MODEL_PROVIDER_MAPPING, GEMINI_API_KEY

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
        An initialized LLM provider (OllamaProvider, GeminiProvider, or
        OpenAICompatibleProvider)
    """
    # Check LLM_PROVIDER env var first for the OpenAI-compatible provider,
    # since its model names are not in MODEL_PROVIDER_MAPPING.
    llm_provider_env = os.getenv("LLM_PROVIDER", "ollama").lower()

    if llm_provider_env == "openai":
        base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:1234/v1")
        logger.info(
            f"🔄 Using OpenAI-compatible provider at {base_url} with model {model_name}"
        )
        return OpenAICompatibleProvider(base_url=base_url)

    # Default to Ollama provider
    provider = OllamaProvider()
    # If using Gemini and API key is available, use Gemini provider
    model_provider = MODEL_PROVIDER_MAPPING.get(model_name, ModelProvider.OLLAMA)
    if model_provider == ModelProvider.GEMINI:
        if not GEMINI_API_KEY:
            logger.warning("⚠️ Gemini API key not found. Falling back to Ollama.")
        else:
            logger.info(f"🔄 Using Google Gemini API provider with model {model_name}")
            provider = GeminiProvider(api_key=GEMINI_API_KEY)
    else:
        logger.info(f"🔄 Using Ollama provider with model {model_name}")
    return provider
