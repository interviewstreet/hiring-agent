# Run real scoring (Windows)

Run these inside your fork of hiring-agent, with this package's files copied in.

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt spacy
    python -m spacy download en_core_web_md
    copy .env.example .env
    ollama pull gemma4:latest
    python benchmark/run_real_scoring.py --per-group 5 --controls 20 --out real_results.jsonl

Set DEFAULT_MODEL in `.env` to a model from `providers.json`; for Gemini, also set GEMINI_API_KEY.
The script makes 70 scorer calls, can be stopped and resumed, and prints a summary at the end.
Send back `real_results.jsonl`. It contains only synthetic resumes.
