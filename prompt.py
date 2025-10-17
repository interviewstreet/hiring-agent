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
    # DeepSeek models
    "deepseek/deepseek-chat": {"temperature": 0.1, "top_p": 0.9},
    "deepseek/deepseek-coder": {"temperature": 0.1, "top_p": 0.9},
    # OpenAI models
    "openai/gpt-4": {"temperature": 0.1, "top_p": 0.9},
    "openai/gpt-4-turbo": {"temperature": 0.1, "top_p": 0.9},
    "openai/gpt-3.5-turbo": {"temperature": 0.1, "top_p": 0.9},
    # Anthropic models
    "anthropic/claude-3-opus-20240229": {"temperature": 0.1, "top_p": 0.9},
    "anthropic/claude-3-sonnet-20240229": {"temperature": 0.1, "top_p": 0.9},
    "anthropic/claude-3-haiku-20240307": {"temperature": 0.1, "top_p": 0.9},
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
    # DeepSeek models
    "deepseek/deepseek-chat": ModelProvider.DEEPSEEK,
    "deepseek/deepseek-coder": ModelProvider.DEEPSEEK,
    # OpenAI models
    "openai/gpt-4": ModelProvider.OPENAI,
    "openai/gpt-4-turbo": ModelProvider.OPENAI,
    "openai/gpt-3.5-turbo": ModelProvider.OPENAI,
    # Anthropic models
    "anthropic/claude-3-opus-20240229": ModelProvider.ANTHROPIC,
    "anthropic/claude-3-sonnet-20240229": ModelProvider.ANTHROPIC,
    "anthropic/claude-3-haiku-20240307": ModelProvider.ANTHROPIC,
}

# Get API keys from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Ollama API base URL
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
