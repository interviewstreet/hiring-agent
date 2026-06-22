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
DEFAULT_MODEL_NAME = "llama-3.3-70b-versatile"
DEFAULT_PROVIDER = ModelProvider.GROQ

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
    # Groq models
    "llama-3.3-70b-versatile": {"temperature": 0.1, "top_p": 0.9},
    "llama-3.1-8b-instant": {"temperature": 0.1, "top_p": 0.9},
    "mixtral-8x7b-32768": {"temperature": 0.1, "top_p": 0.9},
    # OpenRouter models
    "meta-llama/llama-3.3-70b-instruct:free": {"temperature": 0.1, "top_p": 0.9},
    "google/gemma-2-9b-it:free": {"temperature": 0.1, "top_p": 0.9},
    "mistralai/mistral-7b-instruct:free": {"temperature": 0.1, "top_p": 0.9},
    # Mistral models
    "mistral-small-latest": {"temperature": 0.1, "top_p": 0.9},
    "open-mistral-nemo": {"temperature": 0.1, "top_p": 0.9},
    "codestral-latest": {"temperature": 0.1, "top_p": 0.9},
    # Cerebras models
    "llama3.1-8b": {"temperature": 0.1, "top_p": 0.9},
    "llama-3.3-70b": {"temperature": 0.1, "top_p": 0.9},
}

# Model provider mapping
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
    # Groq models
    "llama-3.3-70b-versatile": ModelProvider.GROQ,
    "llama-3.1-8b-instant": ModelProvider.GROQ,
    "mixtral-8x7b-32768": ModelProvider.GROQ,
    # OpenRouter models
    "meta-llama/llama-3.3-70b-instruct:free": ModelProvider.OPENROUTER,
    "google/gemma-2-9b-it:free": ModelProvider.OPENROUTER,
    "mistralai/mistral-7b-instruct:free": ModelProvider.OPENROUTER,
    # Mistral models
    "mistral-small-latest": ModelProvider.MISTRAL,
    "open-mistral-nemo": ModelProvider.MISTRAL,
    "codestral-latest": ModelProvider.MISTRAL,
    # Cerebras models
    "llama3.1-8b": ModelProvider.CEREBRAS,
    "llama-3.3-70b": ModelProvider.CEREBRAS,
}

# Provider base URLs for OpenAI-compatible APIs
PROVIDER_BASE_URLS = {
    ModelProvider.GROQ: "https://api.groq.com/openai/v1",
    ModelProvider.OPENROUTER: "https://openrouter.ai/api/v1",
    ModelProvider.MISTRAL: "https://api.mistral.ai/v1",
    ModelProvider.CEREBRAS: "https://api.cerebras.ai/v1",
}

# Get API keys from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")

PROVIDER_API_KEYS = {
    ModelProvider.GEMINI: GEMINI_API_KEY,
    ModelProvider.GROQ: GROQ_API_KEY,
    ModelProvider.OPENROUTER: OPENROUTER_API_KEY,
    ModelProvider.MISTRAL: MISTRAL_API_KEY,
    ModelProvider.CEREBRAS: CEREBRAS_API_KEY,
}
