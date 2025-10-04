"""
Prompts for Resume Evaluation System

This module contains all the prompts used by the resume evaluation system.
Centralizing prompts here makes them easier to maintain and update.
"""

import os
from dotenv import load_dotenv
from models import ModelProvider
from config_loader import get_config

# Load environment variables
load_dotenv()

# Get configuration
config = get_config()

# Constants
DEFAULT_MODEL_NAME = "gemma3:4b"
DEFAULT_PROVIDER = ModelProvider.OLLAMA

# Get model and provider from configuration or environment
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", config.get("models.default", DEFAULT_MODEL_NAME))
PROVIDER = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER.value)

# Validate provider
if PROVIDER not in [p.value for p in ModelProvider]:
    PROVIDER = DEFAULT_PROVIDER.value

# Model-specific parameters from configuration
MODEL_PARAMETERS = config.get("models.parameters", {
    "gemma3:4b": {"temperature": 0.1, "top_p": 0.9}
})

# Model provider mapping from configuration
provider_mapping = config.get("models.provider_mapping", {})
MODEL_PROVIDER_MAPPING = {}
for model, provider_str in provider_mapping.items():
    if provider_str == "ollama":
        MODEL_PROVIDER_MAPPING[model] = ModelProvider.OLLAMA
    elif provider_str == "gemini":
        MODEL_PROVIDER_MAPPING[model] = ModelProvider.GEMINI

# Get API keys from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
