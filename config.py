"""
Configuration settings for the hiring agent application.

This module provides backward compatibility and easy access to configuration settings.
"""

from config_loader import get_config

# Get the global configuration
config = get_config()

# Backward compatibility - expose commonly used settings
DEVELOPMENT_MODE = config.is_development_mode()

# Export configuration getter for other modules
def get_setting(key_path: str, default=None):
    """Get a configuration setting by key path."""
    return config.get(key_path, default)
