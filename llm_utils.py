"""
Utility functions for LLM providers.
"""

import logging
from typing import Any, Dict, Optional
from models import ModelProvider, OllamaProvider, GeminiProvider
from prompt import MODEL_PROVIDER_MAPPING, GEMINI_API_KEY, LLM_PROVIDER

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
    Initialize the appropriate LLM provider based on the LLM_PROVIDER environment variable.

    Args:
        model_name: The name of the model to use

    Returns:
        An initialized LLM provider (either OllamaProvider or GeminiProvider)
    """
    # Use the environment variable to determine the provider
    if LLM_PROVIDER == ModelProvider.GEMINI.value:
        if not GEMINI_API_KEY:
            logger.error("❌ Gemini provider selected, but GEMINI_API_KEY is not set.")
            raise ValueError("GEMINI_API_KEY not found for Gemini provider")
        logger.info(f"🔄 Using Google Gemini API provider with model {model_name}")
        return GeminiProvider(api_key=GEMINI_API_KEY)

    # Default to Ollama for any other case
    logger.info(f"🔄 Using Ollama provider with model {model_name}")
    return OllamaProvider()
