"""
Utility functions for LLM providers.
"""

import logging
from typing import Any, Dict, Optional
from config import provider_for
from models import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


def extract_json_from_response(response_text: str) -> str:
    """
    Extract JSON content from an LLM response.

    Strips markdown fences and ``<think>`` blocks, then keeps the outermost
    JSON object or array when the model wraps the payload in prose.
    """

    response_text = response_text.strip()
    if "<think>" in response_text:
        think_start = response_text.find("<think>")
        think_end = response_text.find("</think>")
        if think_start != -1 and think_end != -1:
            response_text = response_text[:think_start] + response_text[think_end + 8 :]

    # Remove leading ```json / ``` if present
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    elif response_text.startswith("```"):
        response_text = response_text[3:]
    # Remove trailing ``` if present
    if response_text.endswith("```"):
        response_text = response_text[:-3]

    response_text = response_text.strip()

    # Prefer an object payload; fall back to an array (e.g. project selection).
    for open_char, close_char in (("{", "}"), ("[", "]")):
        start = response_text.find(open_char)
        end = response_text.rfind(close_char)
        if start != -1 and end != -1 and end > start:
            return response_text[start : end + 1]

    return response_text


def initialize_llm_provider(model_name: str) -> Any:
    """
    Initialize an OpenAI-compatible LLM provider for the given model,
    resolving base_url / api_key / structured-output mode from providers.json.
    """
    cfg = provider_for(model_name)
    logger.info(f"🔄 Using model {model_name} via {cfg['base_url']}")
    return OpenAICompatibleProvider(
        base_url=cfg["base_url"],
        api_key=cfg["api_key"],
        structured_output=cfg["structured_output"],
        extra_body=cfg["extra_body"],
    )
