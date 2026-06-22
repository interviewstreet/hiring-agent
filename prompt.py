"""
Prompts for Resume Evaluation System

This module contains all the prompts used by the resume evaluation system.
Centralizing prompts here makes them easier to maintain and update.
"""

import os
from dotenv import load_dotenv
from models import ModelProvider

# Load environment variables
load_dotenv()

# Constants
DEFAULT_MODEL_NAME = "gemma3:4b"
DEFAULT_PROVIDER = ModelProvider.OLLAMA

# Get model and provider from environment or use defaults
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", DEFAULT_MODEL_NAME)
PROVIDER = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER.value)

# Validate provider
if PROVIDER not in [p.value for p in ModelProvider]:
    PROVIDER = DEFAULT_PROVIDER.value

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
    # Claude Code CLI (sampling params are ignored by the CLI; kept for parity)
    "claude-code": {"temperature": 0.1, "top_p": 0.9},
    # Codex CLI (sampling params are ignored by the CLI; kept for parity)
    "codex-cli": {"temperature": 0.1, "top_p": 0.9},
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
    # Claude Code CLI (uses your authenticated local Claude Code session)
    "claude-code": ModelProvider.CLAUDE_CODE,
    # Codex CLI (uses your authenticated local Codex session)
    "codex-cli": ModelProvider.CODEX,
}

# Get API keys from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Claude Code CLI configuration (used when LLM_PROVIDER=claude_code).
# No API key is required; the CLI uses your authenticated Claude Code session.
CLAUDE_CODE_COMMAND = os.getenv("CLAUDE_CODE_COMMAND", "claude")

# Optional concrete model / alias for nested calls (e.g. "sonnet", "opus",
# "claude-sonnet-4-6"). When empty, the CLI uses your session's default model.
CLAUDE_CODE_MODEL = os.getenv("CLAUDE_CODE_MODEL", "").strip() or None

# Per-call timeout for the Claude Code CLI, in seconds (defaults to 300).
try:
    CLAUDE_CODE_TIMEOUT_SECONDS = int(os.getenv("CLAUDE_CODE_TIMEOUT_SECONDS", "300"))
except ValueError:
    CLAUDE_CODE_TIMEOUT_SECONDS = 300

# Codex CLI configuration (used when LLM_PROVIDER=codex).
# No API key is required; the CLI uses your authenticated Codex session.
CODEX_COMMAND = os.getenv("CODEX_COMMAND", "codex")

# Optional concrete model / alias for nested calls. When empty, the CLI uses
# its configured default model.
CODEX_MODEL = os.getenv("CODEX_MODEL", "").strip() or None

# Per-call timeout for the Codex CLI, in seconds (defaults to 300).
try:
    CODEX_TIMEOUT_SECONDS = int(os.getenv("CODEX_TIMEOUT_SECONDS", "300"))
except ValueError:
    CODEX_TIMEOUT_SECONDS = 300
