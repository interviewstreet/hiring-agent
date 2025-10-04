"""
Configuration loader for the hiring agent application.

This module provides functionality to load and manage configuration settings
from YAML files with support for environment variable overrides.
"""

import os
import yaml
import logging
from typing import Any, Dict, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Configuration loader that handles YAML configuration files with environment variable overrides.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the configuration loader.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self._config: Optional[Dict[str, Any]] = None
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"Configuration file not found: {self.config_path}")
                self._config = self._get_default_config()
                return
            
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self._config = yaml.safe_load(file)
            
            # Apply environment variable overrides
            self._apply_env_overrides()
            
            logger.info(f"Configuration loaded from {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self._config = self._get_default_config()
    
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        # Override model settings
        if os.getenv("DEFAULT_MODEL"):
            self._config["models"]["default"] = os.getenv("DEFAULT_MODEL")
        
        if os.getenv("LLM_PROVIDER"):
            # Update provider mapping if needed
            default_model = self._config["models"]["default"]
            self._config["models"]["provider_mapping"][default_model] = os.getenv("LLM_PROVIDER")
        
        # Override development mode
        if os.getenv("DEVELOPMENT_MODE"):
            self._config["app"]["development_mode"] = os.getenv("DEVELOPMENT_MODE").lower() == "true"
        
        # Override GitHub token
        if os.getenv("GITHUB_TOKEN"):
            # Store in a way that can be accessed by other modules
            self._config["api"]["github"]["token"] = os.getenv("GITHUB_TOKEN")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration when file is not found."""
        return {
            "app": {
                "name": "Hiring Agent",
                "version": "1.0.0",
                "development_mode": True,
                "cache_directory": "cache",
                "output_directory": "output"
            },
            "evaluation": {
                "scoring_weights": {
                    "open_source": 35,
                    "self_projects": 30,
                    "production": 25,
                    "technical_skills": 10
                },
                "max_scores": {
                    "open_source": 35,
                    "self_projects": 30,
                    "production": 25,
                    "technical_skills": 10
                },
                "bonus_points": {
                    "max_total": 20,
                    "criteria": []
                },
                "deductions": {
                    "max_total": 20,
                    "rules": []
                },
                "score_limits": {
                    "min_final_score": -20,
                    "max_final_score": 120
                }
            },
            "models": {
                "default": "gemma3:4b",
                "parameters": {
                    "gemma3:4b": {"temperature": 0.1, "top_p": 0.9}
                },
                "provider_mapping": {
                    "gemma3:4b": "ollama"
                }
            },
            "file_processing": {
                "pdf": {
                    "max_size_mb": 50,
                    "supported_extensions": [".pdf"],
                    "min_file_size_bytes": 100
                },
                "github": {
                    "max_repos": 100,
                    "max_contributors_per_repo": 100,
                    "min_commit_threshold": 1,
                    "fork_threshold": 5
                },
                "project_selection": {
                    "max_projects_to_select": 7,
                    "min_author_commits": 1,
                    "prefer_open_source": True
                }
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)5s - %(lineno)5d - %(funcName)33s - %(levelname)5s - %(message)s",
                "file": "hiring_agent.log",
                "max_file_size_mb": 10,
                "backup_count": 5
            },
            "cache": {
                "enabled": True,
                "ttl_hours": 24,
                "max_size_mb": 100,
                "cleanup_interval_hours": 6
            },
            "api": {
                "github": {
                    "timeout_seconds": 10,
                    "retry_attempts": 3,
                    "retry_delay_seconds": 1
                },
                "llm": {
                    "timeout_seconds": 30,
                    "retry_attempts": 2,
                    "retry_delay_seconds": 2
                }
            },
            "output": {
                "csv": {
                    "filename": "resume_evaluations.csv",
                    "include_timestamp": True
                },
                "json": {
                    "pretty_print": True,
                    "include_metadata": True
                },
                "reports": {
                    "include_charts": False,
                    "template": "default"
                }
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to the configuration value (e.g., "models.default")
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        if self._config is None:
            return default
        
        keys = key_path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get an entire configuration section.
        
        Args:
            section: Section name (e.g., "models", "evaluation")
            
        Returns:
            Configuration section as dictionary
        """
        return self.get(section, {})
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()
    
    def is_development_mode(self) -> bool:
        """Check if development mode is enabled."""
        return self.get("app.development_mode", True)
    
    def get_model_parameters(self, model_name: str) -> Dict[str, Any]:
        """
        Get model parameters for a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Model parameters dictionary
        """
        return self.get(f"models.parameters.{model_name}", {"temperature": 0.1, "top_p": 0.9})
    
    def get_scoring_weights(self) -> Dict[str, int]:
        """Get scoring weights for evaluation categories."""
        return self.get("evaluation.scoring_weights", {})
    
    def get_max_scores(self) -> Dict[str, int]:
        """Get maximum scores for evaluation categories."""
        return self.get("evaluation.max_scores", {})
    
    def get_bonus_criteria(self) -> list:
        """Get bonus point criteria."""
        return self.get("evaluation.bonus_points.criteria", [])
    
    def get_deduction_rules(self) -> list:
        """Get deduction rules."""
        return self.get("evaluation.deductions.rules", [])
    
    def get_file_limits(self) -> Dict[str, Any]:
        """Get file processing limits."""
        return self.get("file_processing", {})
    
    def get_github_settings(self) -> Dict[str, Any]:
        """Get GitHub API settings."""
        return self.get("file_processing.github", {})
    
    def get_pdf_settings(self) -> Dict[str, Any]:
        """Get PDF processing settings."""
        return self.get("file_processing.pdf", {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.get("logging", {})
    
    def get_cache_settings(self) -> Dict[str, Any]:
        """Get cache configuration."""
        return self.get("cache", {})
    
    def get_output_settings(self) -> Dict[str, Any]:
        """Get output configuration."""
        return self.get("output", {})


# Global configuration instance
_config_loader: Optional[ConfigLoader] = None


def get_config(config_path: str = "config.yaml") -> ConfigLoader:
    """
    Get the global configuration loader instance.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        ConfigLoader instance
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader(config_path)
    return _config_loader


def reload_config() -> None:
    """Reload the global configuration."""
    global _config_loader
    if _config_loader is not None:
        _config_loader.reload()
