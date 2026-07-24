"""Robust smoke tests to validate repository basic health."""

import sys
from pathlib import Path
import importlib
import importlib.util
import traceback

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

def test_score_py_exists():
    assert (REPO_ROOT / "score.py").exists(), "score.py missing — add main logic or file"

def test_core_modules_importable():
    """Try to import core modules and show real errors for debugging."""
    modules = ("score", "evaluator", "github", "pdf")
    for mod in modules:
        try:
            importlib.import_module(mod)
        except Exception as e:
            tb = traceback.format_exc()
            raise AssertionError(f"Importing module '{mod}' failed with:\n{tb}") from e

def test_placeholder():
    assert True
