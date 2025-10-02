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

# if gemini is used
# DEFAULT_MODEL_NAME = "gemini-2.0-flash"
# DEFAULT_PROVIDER = ModelProvider.GEMINI

# Get model and provider from environment or use defaults
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", DEFAULT_MODEL_NAME)
PROVIDER = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER.value)

# Validate provider
if PROVIDER not in [p.value for p in ModelProvider]:
    PROVIDER = DEFAULT_PROVIDER.value

# Model-specific parameters
MODEL_PARAMETERS = {
    # Ollama models
    "qwen3:1.7b": {
        "temperature": 0.0,
        "top_p": 0.9
    },
    "gemma3:1b": {
        "temperature": 0.0,
        "top_p": 0.9
    },    
    "qwen3:4b": {
        "temperature": 0.1,
        "top_p": 0.4
    },
    "gemma3:4b": {
        "temperature": 0.1,
        "top_p": 0.9
    },
    "gemma3:12b": {
        "temperature": 0.1,
        "top_p": 0.9
    },
    "mistral:7b": {
        "temperature": 0.1,
        "top_p": 0.9
    },
    
    # Google Gemini models
    "gemini-2.0-flash": {
        "temperature": 0.1,
        "top_p": 0.9
    },
    "gemini-2.0-flash-exp": {
        "temperature": 0.1,
        "top_p": 0.9
    },
    # Legacy support
    "gemini-2.0-flash-lite": {
        "temperature": 0.1,
        "top_p": 0.9
    },
    "gemini-2.5-pro": {
        "temperature": 0.1,
        "top_p": 0.9
    },
    "gemini-2.5-flash": {
        "temperature": 0.1,
        "top_p": 0.9
    },
    "gemini-2.5-flash-lite": {
        "temperature": 0.1,
        "top_p": 0.9
    }
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
    "gemini-2.0-flash-exp": ModelProvider.GEMINI,
    # Legacy support for existing configs
    "gemini-2.0-flash-lite": ModelProvider.GEMINI,
    "gemini-2.5-flash": ModelProvider.GEMINI,
    "gemini-2.5-flash-lite": ModelProvider.GEMINI,
    "gemini-2.5-pro": ModelProvider.GEMINI
}

# Get API keys from environment (supports both variable names)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")