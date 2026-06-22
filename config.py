"""
Configuration settings for the hiring agent application.
"""
import os

# Global development mode flag
DEVELOPMENT_MODE = os.getenv('DEVELOPMENT_MODE', 'False').lower() == 'true'
