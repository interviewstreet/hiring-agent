"""
Utility functions for LLM providers.
"""

import json
import logging
from typing import Any, Dict, Optional, Union
from models import ModelProvider, OllamaProvider, GeminiProvider
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


def parse_llm_response(
    response_text: str, structured_output: bool = False
) -> Union[Dict, Any]:
    """
    Parse LLM response, with special handling for structured output.

    Args:
        response_text: Raw response text from LLM
        structured_output: Whether this response came from structured output

    Returns:
        Parsed data structure

    Raises:
        Exception: If parsing fails
    """
    if structured_output:
        # For structured output, the response should already be valid JSON
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.warning(
                f"Structured output JSON parsing failed: {e}. Trying cleanup..."
            )
            # Fallback to cleanup and parse
            cleaned_text = extract_json_from_response(response_text)
            return json.loads(cleaned_text)
    else:
        # Regular parsing with cleanup
        try:
            cleaned_text = extract_json_from_response(response_text)
            return json.loads(cleaned_text)
        except Exception as json_error:
            logger.error(f"JSON parsing failed: {json_error}")
            raise json_error


def supports_structured_output(provider: Any, model: str) -> bool:
    """
    Check if the provider and model support structured output.

    Args:
        provider: LLM provider instance
        model: Model name

    Returns:
        True if structured output is supported
    """
    # Only Gemini supports structured output for now
    if isinstance(provider, GeminiProvider):
        return hasattr(provider, "use_new_api") and provider.use_new_api

    # Ollama doesn't use structured output (keep traditional JSON parsing)
    return False
