# Pull Request: Add an optional web UI for the scoring pipeline

> Submit this **after** opening the feature-request issue below and commenting that you're working on it (per CONTRIBUTING.md). Fork `interviewstreet/hiring-agent`, branch off `master`, e.g. `feat/web-ui`.

---

## Suggested issue to open first

**Title:** Optional browser UI for running the scoring pipeline

**Body:**
The pipeline is currently CLI-only. For users who want to score a resume without the terminal, a thin local web UI would help: drag-and-drop the PDF, pick the model/key in a settings panel, and watch the same pipeline output stream live. It would wrap the existing `score.main()` without changing CLI behavior. Would a self-contained, optional Flask UI be welcome? Happy to implement.

---

## PR title

```
feat: add optional Flask web UI with live-streamed scoring output
```

## Summary

Adds an optional browser interface on top of the existing pipeline. It does not change the CLI, the scoring logic, the prompts, or any model behavior. The server simply calls the existing `score.main(pdf_path, api_key, model_name)` and streams its stdout/stderr to the page.

## Motivation

`python score.py <pdf>` is great for developers, but reviewers who just want to score a resume have to use the terminal and edit `.env` to switch models or keys. A small local UI lowers that barrier while reusing the exact same pipeline, so results are identical to the CLI.

## What's included

- `app.py` — a small Flask server:
  - `GET /` serves the UI.
  - `POST /api/upload` accepts a PDF plus model/API-key from the settings panel, starts the pipeline on a background thread.
  - `GET /api/stream/<job_id>` streams pipeline output to the browser over Server-Sent Events, with heartbeats and a clean end-of-stream sentinel.
  - Friendly handling for an invalid/expired Gemini key and for failed evaluations.
- `frontend/` — a no-framework UI (`index.html`, `app.js`, `style.css`): drag-and-drop PDF upload, a settings panel (model + API key, stored client-side), session history, and a live output console.
- `requirements.txt` — adds `flask` (currently imported by the UI but not declared).
- `Start-Hiring-Agent.bat` — a convenient one-click Windows batch script to activate the environment, start the server, and open the browser.

## What's deliberately unchanged

- No change to `score.py` scoring logic, `prompt.py`/`prompts/` templates, `github.py`, `evaluator.py`, or `models.py` behavior.
- The CLI (`python score.py <pdf>`) works exactly as before. The UI is opt-in.
- No new model providers or prompt formatting; provider-agnostic, per CONTRIBUTING.

## How to run

```bash
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:5000, set your model + Gemini key in Settings, drop a PDF
```

## Testing / smoke checks

- PDF to Markdown, section extraction, GitHub enrichment, and evaluation all run through the unchanged `score.main()`; verified the UI output matches a CLI run on the same resume.
- Gemini run (`gemini-2.5-flash`): identical category scores via UI and CLI.
- Verified invalid-key and non-PDF upload paths return clear errors.
- Formatted with Black (`black .`).

## Notes for reviewers

- The server binds to `127.0.0.1` only and is meant for local use.
- Uploads go to a temp dir keyed by job id; nothing is committed.
- If a web UI is out of scope for this project, I'm happy to instead split out just the `requirements.txt` `flask` fix, or move the UI to a `contrib/` or `examples/` folder.

## Checklist

- [ ] Opened/linked a feature-request issue and claimed it
- [ ] Branched off `master` on my fork
- [ ] CLI behavior unchanged
- [ ] `flask` added to `requirements.txt`
- [ ] Formatted with Black
- [ ] Smoke-tested at least one full run (Gemini)
- [ ] Added a screenshot/GIF of the UI to this PR
