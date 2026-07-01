"""
Utility functions for LLM providers.
"""
import logging
from typing import Any
from models import ModelProvider, OllamaProvider, GeminiProvider, ZAIProvider
from prompt import MODEL_PROVIDER_MAPPING, GEMINI_API_KEY, ZAI_API_KEY

logger = logging.getLogger(__name__)

def extract_json_from_response(response_text: str) -> str:
    response_text = response_text.strip()
    if "<think>" in response_text:
        think_start = response_text.find("<think>")
        think_end = response_text.find("</think>")
        if think_start != -1 and think_end != -1:
            response_text = response_text[:think_start] + response_text[think_end + 8:]
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    return response_text

def initialize_llm_provider(model_name: str) -> Any:
    provider = OllamaProvider()
    model_provider = MODEL_PROVIDER_MAPPING.get(model_name, ModelProvider.OLLAMA)

    if model_provider == ModelProvider.GEMINI:
        if not GEMINI_API_KEY:
            logger.warning("⚠️ Gemini API key not found. Falling back to Ollama.")
        else:
            logger.info(f"🔄 Using Google Gemini API provider with model {model_name}")
            provider = GeminiProvider(api_key=GEMINI_API_KEY)
    elif model_provider == ModelProvider.ZAI:
        if not ZAI_API_KEY:
            logger.warning("⚠️ Z.AI API key not found. Falling back to Ollama.")
        else:
            logger.info(f"🔄 Using Z.AI provider with model {model_name}")
            provider = ZAIProvider(api_key=ZAI_API_KEY)
    else:
        logger.info(f"🔄 Using Ollama provider with model {model_name}")

    return provider
