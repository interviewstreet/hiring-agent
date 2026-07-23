"""
Prompts for Resume Evaluation System

This module contains all the prompts used by the resume evaluation system.
Centralizing prompts here makes them easier to maintain and update.
"""

from config import DEFAULT_MODEL, MODEL_PARAMETERS

# Re-exported for consumers (score.py, evaluator.py, pdf.py, github.py).
__all__ = ["DEFAULT_MODEL", "MODEL_PARAMETERS"]
