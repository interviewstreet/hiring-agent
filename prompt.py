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
OLLAMA_DEFAULT_HOST = "http://localhost:11434"
OLLAMA_CLOUD_HOST = "https://ollama.com"

# Get model and provider from environment or use defaults
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", DEFAULT_MODEL_NAME)
PROVIDER = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER.value)

# Ollama connection settings (local daemon or ollama.com cloud API)
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
_ollama_host = os.getenv("OLLAMA_HOST", "").strip()
if not _ollama_host and os.getenv("OLLAMA_CLOUD", "").lower() in ("1", "true", "yes"):
    _ollama_host = OLLAMA_CLOUD_HOST
OLLAMA_HOST = _ollama_host or OLLAMA_DEFAULT_HOST

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
    # Ollama cloud models (offloaded via local daemon or ollama.com API)
    "gemma4:31b-cloud": {"temperature": 0.1, "top_p": 0.9},
    "gpt-oss:20b-cloud": {"temperature": 0.1, "top_p": 0.9},
    "gpt-oss:120b-cloud": {"temperature": 0.1, "top_p": 0.9},
    # Google Gemini models
    "gemini-2.0-flash": {"temperature": 0.1, "top_p": 0.9},
    "gemini-2.0-flash-lite": {"temperature": 0.1, "top_p": 0.9},
    "gemini-2.5-pro": {"temperature": 0.1, "top_p": 0.9},
    "gemini-2.5-flash": {"temperature": 0.1, "top_p": 0.9},
    "gemini-2.5-flash-lite": {"temperature": 0.1, "top_p": 0.9},
    "gemini-3.5-flash": {"temperature": 0.1, "top_p": 0.9},
    "gemini-3.1-flash-lite": {"temperature": 0.1, "top_p": 0.9},
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
    "gemma4:31b-cloud": ModelProvider.OLLAMA,
    "gpt-oss:20b-cloud": ModelProvider.OLLAMA,
    "gpt-oss:120b-cloud": ModelProvider.OLLAMA,
    # Google Gemini models
    "gemini-2.0-flash": ModelProvider.GEMINI,
    "gemini-2.0-flash-lite": ModelProvider.GEMINI,
    "gemini-2.5-flash": ModelProvider.GEMINI,
    "gemini-2.5-flash-lite": ModelProvider.GEMINI,
    "gemini-2.5-pro": ModelProvider.GEMINI,
    "gemini-3.5-flash": ModelProvider.GEMINI,
    "gemini-3.1-flash-lite": ModelProvider.GEMINI,
}

# Get API keys from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def is_ollama_cloud_model(model_name: str) -> bool:
    """Return True when the model tag is an Ollama cloud offload model."""
    return model_name.endswith("-cloud")


def resolve_ollama_model_name(model_name: str, host: str) -> str:
    """
    Resolve the model name for the target Ollama host.

    The ollama.com cloud API expects tags without the -cloud suffix.
    Local Ollama keeps the full tag when offloading to cloud.
    """
    if "ollama.com" in host.rstrip("/") and is_ollama_cloud_model(model_name):
        return model_name[: -len("-cloud")]
    return model_name


def get_model_parameters(model_name: str) -> dict:
    """Return generation parameters for a model, with sensible defaults."""
    if model_name in MODEL_PARAMETERS:
        return MODEL_PARAMETERS[model_name]
    if is_ollama_cloud_model(model_name):
        return {"temperature": 0.1, "top_p": 0.9}
    return {"temperature": 0.1, "top_p": 0.9}
