"""
Utility functions for LLM providers.
"""

import json
import logging
from typing import Any, Optional
from config import provider_for
from models import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


def _strip_response_wrappers(response_text: str) -> str:
    """Strip ``<think>`` blocks and markdown fences from an LLM response."""
    response_text = response_text.strip()
    if "<think>" in response_text:
        think_start = response_text.find("<think>")
        think_end = response_text.find("</think>")
        if think_start != -1 and think_end != -1:
            response_text = response_text[:think_start] + response_text[think_end + 8 :]

    if response_text.startswith("```json"):
        response_text = response_text[7:]
    elif response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]

    return response_text.strip()


def _extract_balanced_json(text: str, open_char: str, close_char: str) -> Optional[str]:
    """Return the first balanced JSON object/array, respecting string literals."""
    start = text.find(open_char)
    if start == -1:
        return None

    in_string = False
    escape = False
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def repair_truncated_json(text: str) -> str:
    """Close unclosed strings and braces/brackets left by truncated LLM output."""
    in_string = False
    escape = False
    stack: list[str] = []

    for char in text:
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            stack.append("}")
        elif char == "[":
            stack.append("]")
        elif char in "}]" and stack and stack[-1] == char:
            stack.pop()

    repaired = text
    if in_string:
        repaired += '"'
    repaired = repaired.rstrip()
    if repaired.endswith(","):
        repaired = repaired[:-1]
    repaired += "".join(reversed(stack))
    return repaired


def extract_json_from_response(response_text: str) -> str:
    """
    Extract JSON content from an LLM response.

    Strips markdown fences and ``<think>`` blocks, then keeps the outermost
    JSON object or array when the model wraps the payload in prose. Truncated
    payloads are repaired by closing open strings and braces so ``json.loads``
    can still succeed.
    """
    response_text = _strip_response_wrappers(response_text)

    for open_char, close_char in (("{", "}"), ("[", "]")):
        balanced = _extract_balanced_json(response_text, open_char, close_char)
        if balanced is not None:
            try:
                json.loads(balanced)
                return balanced
            except json.JSONDecodeError:
                repaired = repair_truncated_json(balanced)
                try:
                    json.loads(repaired)
                    return repaired
                except json.JSONDecodeError:
                    pass

        start = response_text.find(open_char)
        if start == -1:
            continue
        repaired = repair_truncated_json(response_text[start:])
        try:
            json.loads(repaired)
            return repaired
        except json.JSONDecodeError:
            continue

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
