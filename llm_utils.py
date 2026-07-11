"""
Utility functions for LLM providers.
"""

import logging
from typing import Any, Dict, Optional
from models import ModelProvider, OllamaProvider, GeminiProvider
from prompt import MODEL_PROVIDER_MAPPING, GEMINI_API_KEY

logger = logging.getLogger(__name__)


def extract_json_from_response(response_text: str) -> str:
    """
    Extract JSON content from markdown code blocks or text wrappers.

    Args:
        response_text: Text that may contain JSON wrapped in markdown code blocks or conversational text

    Returns:
        Clean JSON string
    """
    response_text = response_text.strip()
    if "<think>" in response_text:
        think_start = response_text.find("<think>")
        think_end = response_text.find("</think>")
        if think_start != -1 and think_end != -1:
            response_text = response_text[:think_start] + response_text[think_end + 8 :]

    # Remove leading ```json or ``` if present
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    elif response_text.startswith("```"):
        response_text = response_text[3:]

    # Remove trailing ``` if present
    if response_text.endswith("```"):
        response_text = response_text[:-3]

    response_text = response_text.strip()

    # Extract only the JSON block (enclosed by { and } or [ and ])
    json_start = response_text.find("{")
    json_end = response_text.rfind("}")

    array_start = response_text.find("[")
    array_end = response_text.rfind("]")

    start_idx = -1
    end_idx = -1

    if json_start != -1 and json_end != -1:
        start_idx = json_start
        end_idx = json_end + 1
        if array_start != -1 and array_start < json_start and array_end > json_end:
            start_idx = array_start
            end_idx = array_end + 1
    elif array_start != -1 and array_end != -1:
        start_idx = array_start
        end_idx = array_end + 1

    if start_idx != -1 and end_idx != -1:
        response_text = response_text[start_idx:end_idx]

    return response_text


def initialize_llm_provider(model_name: str) -> Any:
    """
    Initialize the appropriate LLM provider based on the model name.

    Args:
        model_name: The name of the model to use

    Returns:
        An initialized LLM provider (either OllamaProvider or GeminiProvider)
    """
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
