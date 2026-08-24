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


#: Transports understood by llm_utils.initialize_llm_provider. "openai" covers
#: every provider exposing an OpenAI-compatible /chat/completions endpoint;
#: "bedrock" uses SigV4 + the Converse API, which is not OpenAI-compatible.
SUPPORTED_TRANSPORTS = ("openai", "bedrock")


def provider_for(model_name: str) -> dict:
    """Resolve provider config for a model.

    Returns {transport, base_url, api_key, structured_output, extra_body, region,
    max_tokens}. Raises ValueError if the model is unknown, its required key is
    unset, or it declares an unsupported transport.

    ``structured_output`` may be declared per provider and overridden per model,
    because capability is not uniform within a provider: on Bedrock, Claude and
    Nova honour a forced toolConfig while google.gemma-3-* silently ignores it
    and answers in prose.
    """
    for name, prov in _config["providers"].items():
        if model_name not in prov["models"]:
            continue
        model_cfg = prov["models"][model_name]

        transport = prov.get("transport", "openai")
        if transport not in SUPPORTED_TRANSPORTS:
            raise ValueError(
                f"Provider '{name}' declares unsupported transport "
                f"'{transport}'. Supported: {', '.join(SUPPORTED_TRANSPORTS)}."
            )

        api_key_env = prov.get("api_key_env")
        api_key = os.getenv(api_key_env) if api_key_env else None
        if api_key_env and not api_key:
            raise ValueError(
                f"Model '{model_name}' uses provider '{name}', which requires "
                f"env var '{api_key_env}', but it is unset."
            )
        extra_body = {
            **prov.get("extra_body", {}),
            **model_cfg.get("extra_body", {}),
        }
        return {
            "transport": transport,
            "base_url": prov.get("base_url", "").rstrip("/"),
            "api_key": api_key,
            "structured_output": model_cfg.get(
                "structured_output",
                prov.get("structured_output", "json_schema"),
            ),
            "extra_body": extra_body,
            # Bedrock-only. Env wins so one providers.json works across regions.
            "region": os.getenv("AWS_REGION") or prov.get("region"),
            "max_tokens": model_cfg.get("max_tokens", prov.get("max_tokens", 8192)),
        }

    available = ", ".join(sorted(MODEL_PARAMETERS))
    raise ValueError(f"Unknown model '{model_name}'. Available models: {available}")
