"""Loads providers.json and exposes provider/model resolution."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Global development mode flag. Preserved here because score.py and github.py
# import it from this module.
DEVELOPMENT_MODE = True

# Load .env before any os.getenv below, so values apply regardless of import order.
load_dotenv(Path(__file__).parent / ".env")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# Phase 0 — PDF integrity
ENABLE_PDF_INTEGRITY = _env_bool("ENABLE_PDF_INTEGRITY", True)
BLOCK_ON_PDF_INTEGRITY_FAIL = _env_bool("BLOCK_ON_PDF_INTEGRITY_FAIL", False)

# Phase 1 — Score validation
ENSEMBLE_RUNS = max(1, int(os.getenv("ENSEMBLE_RUNS", "1")))

# Phase 2 — Writing quality
ENABLE_WRITING_QUALITY = _env_bool("ENABLE_WRITING_QUALITY", True)
WRITING_QUALITY_USE_LLM = _env_bool("WRITING_QUALITY_USE_LLM", False)

# Phase 3 — Blog enrichment
ENABLE_BLOG_ENRICHMENT = _env_bool("ENABLE_BLOG_ENRICHMENT", True)
ENABLE_BLOG_LLM_SCORING = _env_bool("ENABLE_BLOG_LLM_SCORING", False)

# Phase 4 — Batch ranking
BATCH_CUTOFF_PERCENTILE = float(os.getenv("BATCH_CUTOFF_PERCENTILE", "15"))

# Web report
ENABLE_WEB_REPORT = _env_bool("ENABLE_WEB_REPORT", True)
WEB_REPORT_OUTPUT_DIR = os.getenv("WEB_REPORT_OUTPUT_DIR", "reports")
ENABLE_REPORT_LLM = _env_bool("ENABLE_REPORT_LLM", False)

_CONFIG_PATH = Path(__file__).parent / "providers.json"

with open(_CONFIG_PATH) as _f:
    _config = json.load(_f)

# Default model, overridable by env.
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", _config["default_model"])

# Flat model -> {temperature, top_p} map. Preserves the contract that
# prompt.MODEL_PARAMETERS exposed to evaluator.py / pdf.py / github.py / score.py.
MODEL_PARAMETERS = {
    model: {k: v for k, v in params.items() if k in ("temperature", "top_p")}
    for provider in _config["providers"].values()
    for model, params in provider["models"].items()
}


def provider_for(model_name: str) -> dict:
    """Resolve provider config for a model.

    Returns {base_url, api_key, structured_output, extra_body}.
    Raises ValueError if the model is unknown or its required key is unset.
    """
    for name, prov in _config["providers"].items():
        if model_name not in prov["models"]:
            continue
        api_key_env = prov.get("api_key_env")
        api_key = os.getenv(api_key_env) if api_key_env else None
        if api_key_env and not api_key:
            raise ValueError(
                f"Model '{model_name}' uses provider '{name}', which requires "
                f"env var '{api_key_env}', but it is unset."
            )
        extra_body = {
            **prov.get("extra_body", {}),
            **prov["models"][model_name].get("extra_body", {}),
        }
        return {
            "base_url": prov["base_url"].rstrip("/"),
            "api_key": api_key,
            "structured_output": prov.get("structured_output", "json_schema"),
            "extra_body": extra_body,
        }

    available = ", ".join(sorted(MODEL_PARAMETERS))
    raise ValueError(
        f"Unknown model '{model_name}'. Available models: {available}"
    )
