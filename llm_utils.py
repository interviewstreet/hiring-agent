"""
Utility functions for LLM providers.
"""

import json
import logging
from typing import Any, Dict, Optional
from models import ModelProvider, OllamaProvider, GeminiProvider
from prompt import MODEL_PROVIDER_MAPPING, GEMINI_API_KEY

logger = logging.getLogger(__name__)


def extract_json_from_response(response_text: str) -> Optional[str]:
    """
    Extract JSON content from markdown code blocks.

    Args:
        response_text: Text that may contain JSON wrapped in markdown code blocks

    Returns:
        Cleaned JSON string if valid, None if parsing fails
    """
    try:
        response_text = response_text.strip()
        
        # Remove <think> tags
        if "<think>" in response_text:
            think_start = response_text.find("<think>")
            think_end = response_text.find("</think>")
            if think_start != -1 and think_end != -1:
                response_text = response_text[:think_start] + response_text[think_end + 8 :]

        # Remove markdown code block syntax
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        # Validate JSON before returning
        json.loads(response_text)
        return response_text
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in LLM response: {e}")
        logger.debug(f"Raw response: {response_text}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in extract_json_from_response: {e}")
        return None


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
