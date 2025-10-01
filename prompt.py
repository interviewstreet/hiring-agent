"""
Prompts for Resume Evaluation System

This module contains all the prompts used by the resume evaluation system.
Centralizing prompts here makes them easier to maintain and update.
"""
import os
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from models import ModelProvider

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
DEFAULT_MODEL_NAME = "gemma3:4b"
DEFAULT_PROVIDER = ModelProvider.OLLAMA

# Get model and provider from environment or use defaults
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", DEFAULT_MODEL_NAME)
PROVIDER = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER.value)

# Validate provider with better error handling
def _validate_provider(provider_str: str) -> str:
    """Validate provider string and return valid value."""
    valid_providers = [p.value for p in ModelProvider]
    if provider_str not in valid_providers:
        logger.warning(f"Invalid provider '{provider_str}'. Using default '{DEFAULT_PROVIDER.value}'. "
                      f"Available: {valid_providers}")
        return DEFAULT_PROVIDER.value
    return provider_str

PROVIDER = _validate_provider(PROVIDER)

# Model-specific parameters with validation
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
    "gemini-2.5-pro": ModelProvider.GEMINI
}

# Validate default model exists
def _validate_default_model(model_name: str) -> str:
    """Validate default model and return valid model name."""
    if model_name not in MODEL_PARAMETERS:
        logger.warning(f"Default model '{model_name}' not found. Using '{DEFAULT_MODEL_NAME}'")
        return DEFAULT_MODEL_NAME
    return model_name

DEFAULT_MODEL = _validate_default_model(DEFAULT_MODEL)

# Get API keys from environment with validation
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

def validate_api_keys() -> bool:
    """
    Validate that required API keys are present for the current provider.
    
    Returns:
        bool: True if all required keys are present, False otherwise
    """
    if PROVIDER == ModelProvider.GEMINI.value and not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is required for Gemini provider but not set")
        return False
    return True

def get_model_config(model_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get configuration parameters for a specific model.
    
    Args:
        model_name: Name of the model. Uses DEFAULT_MODEL if None.
        
    Returns:
        Dictionary containing model configuration
        
    Raises:
        KeyError: If model is not supported
    """
    model = model_name or DEFAULT_MODEL
    
    if model not in MODEL_PARAMETERS:
        available = list(MODEL_PARAMETERS.keys())
        raise KeyError(f"Unsupported model '{model}'. Available: {available}")
    
    config = MODEL_PARAMETERS[model].copy()
    config.update({
        "model_name": model,
        "provider": MODEL_PROVIDER_MAPPING.get(model, DEFAULT_PROVIDER)
    })
    
    return config

def get_supported_models(provider: Optional[ModelProvider] = None) -> List[str]:
    """
    Get list of supported models, optionally filtered by provider.
    
    Args:
        provider: Filter by this provider. Returns all if None.
        
    Returns:
        List of model names
    """
    if provider is None:
        return list(MODEL_PARAMETERS.keys())
    
    return [
        model for model, model_provider in MODEL_PROVIDER_MAPPING.items()
        if model_provider == provider
    ]

def get_provider_for_model(model_name: str) -> ModelProvider:
    """
    Get the provider for a specific model.
    
    Args:
        model_name: Name of the model
        
    Returns:
        ModelProvider enum
        
    Raises:
        KeyError: If model is not supported
    """
    if model_name not in MODEL_PROVIDER_MAPPING:
        available = list(MODEL_PROVIDER_MAPPING.keys())
        raise KeyError(f"Model '{model_name}' not found. Available: {available}")
    
    return MODEL_PROVIDER_MAPPING[model_name]

# Validate configuration on module load
if not validate_api_keys():
    logger.warning("API key validation failed. Some providers may not work correctly.")

# Log current configuration
logger.info(f"Configuration loaded - Model: {DEFAULT_MODEL}, Provider: {PROVIDER}")
