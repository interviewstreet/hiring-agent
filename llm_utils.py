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
    """
    # Default to Ollama provider
    provider = OllamaProvider()
    model_provider = MODEL_PROVIDER_MAPPING.get(model_name, ModelProvider.OLLAMA)
    
    # Use print instead of logger for these specific messages
    if model_provider == ModelProvider.GEMINI:
        if not GEMINI_API_KEY:
            logger.warning("Gemini API key not found. Falling back to Ollama.")
            print(f"{'Provider:':<12} Ollama (Fallback)")
            print(f"{'Model:':<12} {model_name}")
            print("🔄 Loading...")
        else:
            print(f"{'Provider:':<12} Google Gemini")
            print(f"{'Model:':<12} {model_name}")
            print("🔄 Loading...")
            provider = GeminiProvider(api_key=GEMINI_API_KEY)
    else:
        print(f"{'Provider:':<12} Ollama")
        print(f"{'Model:':<12} {model_name}")
        print("🔄 Loading...")
        
    return provider
