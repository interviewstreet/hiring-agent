"""
Utility functions for LLM providers.
"""

import logging
import json
import hashlib
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


def _try_parse_json(text: str) -> Optional[str]:
    """Attempt to parse JSON and return the canonical string if successful."""
    try:
        obj = json.loads(text)
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return None


def ensure_valid_json(
    response_text: str,
    provider: Any = None,
    model: str = None,
    original_prompt: str = None,
    max_repair_attempts: int = 2,
) -> str:
    """Validate JSON; attempt lightweight repairs or LLM self-repair if needed.

    Strategy:
    1. Strip markdown fences / think tags (already handled outside).
    2. Trim to first/last brace.
    3. Try direct parse.
    4. If still failing and provider available, send a repair prompt asking ONLY for valid JSON.
    5. Return raw text if irreparable to allow upstream fallback handling.
    """
    cleaned = response_text.strip()

    # Fast path
    parsed = _try_parse_json(cleaned)
    if parsed is not None:
        return parsed

    # Attempt brace slicing
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        sliced = cleaned[start : end + 1]
        parsed = _try_parse_json(sliced)
        if parsed is not None:
            return parsed

    # Attempt LLM repair
    if provider and model:
        repair_instruction = (
            "You previously returned malformed JSON. Return ONLY valid JSON for the same task. "
            "No explanations, code fences, or commentary. If fields are missing, infer minimal plausible empty values." 
        )
        for attempt in range(max_repair_attempts):
            try:
                repair_messages = [
                    {"role": "system", "content": repair_instruction},
                    {
                        "role": "user",
                        "content": (
                            "Original prompt:\n" + (original_prompt or "<none>") +
                            "\nMalformed JSON response:\n" + cleaned +
                            "\nReturn ONLY repaired JSON now."
                        ),
                    },
                ]
                # Low creativity for repair
                repair_options = {"temperature": 0.0, "top_p": 0.9}
                repair_resp = provider.chat(
                    model=model,
                    messages=repair_messages,
                    options=repair_options,
                )
                candidate = extract_json_from_response(
                    repair_resp["message"]["content"]
                )
                parsed = _try_parse_json(candidate)
                if parsed is not None:
                    return parsed
            except Exception as e:
                logger.warning(f"JSON repair attempt {attempt+1} failed: {e}")

    # Return original cleaned text (upstream may log and skip)
    return cleaned


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
