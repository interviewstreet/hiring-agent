"""
Prompts for Resume Evaluation System

This module contains all the prompts used by the resume evaluation system.
Centralizing prompts here makes them easier to maintain and update.
"""

import os
import logging
from dotenv import load_dotenv
from models import ModelProvider

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
DEFAULT_MODEL_NAME = "gemma3:4b"
DEFAULT_PROVIDER = ModelProvider.OLLAMA

# Get model and provider from environment or use defaults. Strip surrounding
# whitespace so a stray space in .env (e.g. "claude_cli ") does not silently
# fail to match a provider and fall back to Ollama.
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", DEFAULT_MODEL_NAME).strip()
PROVIDER = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER.value).strip()

# Whether LLM_PROVIDER was explicitly set by the user. When it is, the provider
# choice is authoritative; otherwise we infer it from MODEL_PROVIDER_MAPPING.
PROVIDER_EXPLICITLY_SET = os.getenv("LLM_PROVIDER") is not None

# Validate provider. An explicitly set but unknown value is surfaced as a
# warning instead of being swallowed silently.
if PROVIDER not in [p.value for p in ModelProvider]:
    if PROVIDER_EXPLICITLY_SET:
        logger.warning(
            f"⚠️ Unknown LLM_PROVIDER '{PROVIDER}'. Falling back to "
            f"'{DEFAULT_PROVIDER.value}'. Valid values: "
            f"{', '.join(p.value for p in ModelProvider)}."
        )
    PROVIDER = DEFAULT_PROVIDER.value
    PROVIDER_EXPLICITLY_SET = False

# Model-specific parameters
MODEL_PARAMETERS = {
    # Ollama models
    "qwen3:1.7b": {"temperature": 0.0, "top_p": 0.9},
    "gemma3:1b": {"temperature": 0.0, "top_p": 0.9},
    "qwen3:4b": {"temperature": 0.1, "top_p": 0.4},
    "gemma3:4b": {"temperature": 0.1, "top_p": 0.9},
    "gemma3:12b": {"temperature": 0.1, "top_p": 0.9},
    "mistral:7b": {"temperature": 0.1, "top_p": 0.9},
    # Google Gemini models
    "gemini-2.0-flash": {"temperature": 0.1, "top_p": 0.9},
    "gemini-2.0-flash-lite": {"temperature": 0.1, "top_p": 0.9},
    "gemini-2.5-pro": {"temperature": 0.1, "top_p": 0.9},
    "gemini-2.5-flash": {"temperature": 0.1, "top_p": 0.9},
    "gemini-2.5-flash-lite": {"temperature": 0.1, "top_p": 0.9},
    "gemini-3.5-flash": {"temperature": 0.1, "top_p": 0.9},
    "gemini-3.1-flash-lite": {"temperature": 0.1, "top_p": 0.9},
    # Anthropic Claude models (HTTP API or Claude Code CLI)
    "claude-opus-4-8": {"temperature": 0.1, "top_p": 0.9},
    "claude-sonnet-4-6": {"temperature": 0.1, "top_p": 0.9},
    "claude-haiku-4-5": {"temperature": 0.1, "top_p": 0.9},
}

# Model provider mapping
# Maps model names to their provider
MODEL_PROVIDER_MAPPING = {
    # Ollama models
    "qwen3:1.7b": ModelProvider.OLLAMA,
    "gemma3:1b": ModelProvider.OLLAMA,
    "qwen3:4b": ModelProvider.OLLAMA,
    "gemma3:4b": ModelProvider.OLLAMA,
    "gemma3:12b": ModelProvider.OLLAMA,
    "mistral:7b": ModelProvider.OLLAMA,
    # Google Gemini models
    "gemini-2.0-flash": ModelProvider.GEMINI,
    "gemini-2.0-flash-lite": ModelProvider.GEMINI,
    "gemini-2.5-flash": ModelProvider.GEMINI,
    "gemini-2.5-flash-lite": ModelProvider.GEMINI,
    "gemini-2.5-pro": ModelProvider.GEMINI,
    "gemini-3.5-flash": ModelProvider.GEMINI,
    "gemini-3.1-flash-lite": ModelProvider.GEMINI,
    # Anthropic Claude models (default to the HTTP API; use LLM_PROVIDER=claude_cli
    # to route the same model names through the Claude Code CLI instead)
    "claude-opus-4-8": ModelProvider.CLAUDE,
    "claude-sonnet-4-6": ModelProvider.CLAUDE,
    "claude-haiku-4-5": ModelProvider.CLAUDE,
}

# Get API keys from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# CLI provider command overrides (useful if the binaries are not named
# "claude"/"gemini" or are not on PATH).
CLAUDE_CLI_COMMAND = os.getenv("CLAUDE_CLI_COMMAND", "claude")
GEMINI_CLI_COMMAND = os.getenv("GEMINI_CLI_COMMAND", "gemini")
