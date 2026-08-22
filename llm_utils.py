"""
Utility functions for LLM providers.
"""

import logging
from typing import Any, Dict, Optional
from config import provider_for
from models import BedrockConverseProvider, OpenAICompatibleProvider

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
    Initialize an LLM provider for the given model, resolving transport /
    base_url / api_key / structured-output mode from providers.json.

    Dispatches on the provider's declared ``transport``. Providers omit it and
    default to "openai", so every existing entry keeps working unchanged.
    """
    cfg = provider_for(model_name)

    if cfg["transport"] == "bedrock":
        if not cfg["region"]:
            raise ValueError(
                f"Model '{model_name}' uses the bedrock transport, which needs a "
                f'region. Set AWS_REGION or add "region" to the provider in '
                f"providers.json."
            )
        logger.info(f"🔄 Using model {model_name} via AWS Bedrock ({cfg['region']})")
        return BedrockConverseProvider(
            region=cfg["region"],
            structured_output=cfg["structured_output"],
            max_tokens=cfg["max_tokens"],
            extra_body=cfg["extra_body"],
        )

    logger.info(f"🔄 Using model {model_name} via {cfg['base_url']}")
    return OpenAICompatibleProvider(
        base_url=cfg["base_url"],
        api_key=cfg["api_key"],
        structured_output=cfg["structured_output"],
        extra_body=cfg["extra_body"],
    )
