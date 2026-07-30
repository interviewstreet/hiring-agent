"""
Utility functions for LLM providers.
"""

import logging
import re
from typing import Any, Dict, Optional
from config import provider_for
from models import OpenAICompatibleProvider

logger = logging.getLogger(__name__)

_CODE_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```$", re.DOTALL)


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
        response_text = response_text.strip()

    # Strip a wrapping ```json ... ``` or bare ``` ... ``` fence, if present.
    match = _CODE_FENCE_PATTERN.match(response_text)
    if match:
        response_text = match.group(1)

    return response_text.strip()


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
