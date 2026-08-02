"""Run offline validation with an optional live Gemini smoke check."""

import argparse
import json
import os
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_offline_tests() -> bool:
    suite = unittest.defaultTestLoader.discover(str(PROJECT_ROOT / "tests"))
    return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()


def run_live_check() -> None:
    from config import DEFAULT_MODEL
    from llm_utils import initialize_llm_provider

    if not DEFAULT_MODEL.startswith("gemini-"):
        raise RuntimeError(
            f"Live verification expects a Gemini DEFAULT_MODEL, got {DEFAULT_MODEL!r}."
        )
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to .env or your shell.")

    provider = initialize_llm_provider(DEFAULT_MODEL)
    response = provider.chat(
        model=DEFAULT_MODEL,
        messages=[
            {
                "role": "user",
                "content": "Return an object with ok=true and no other properties.",
            }
        ],
        options={"temperature": 0.0, "top_p": 0.9},
        format={
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
            "additionalProperties": False,
        },
    )
    payload = json.loads(response["message"]["content"])
    if payload != {"ok": True}:
        raise RuntimeError(f"Gemini returned an unexpected payload: {payload!r}")
    print(f"Live Gemini check passed with {DEFAULT_MODEL}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="also make one real Gemini API request"
    )
    args = parser.parse_args()
    if not run_offline_tests():
        return 1
    if args.live:
        run_live_check()
    else:
        print("Offline verification passed. Use --live to check Gemini credentials.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"Verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
