# Running Hiring Agent with Claude Code as the LLM

No API key needed. This guide uses the `claude` CLI you already have installed.

---

## Prerequisites

- Python 3.11+
- Claude Code installed and logged in (`claude` command works in your terminal)
- A resume PDF to evaluate

---

## Step 1 — Install dependencies

```bash
pip install -r requirements.txt
```

---

## Step 2 — Create your `.env` file

Copy the example and set the Claude Code provider:

```bash
cp .env.example .env
```

Then open `.env` and set it to exactly this:

```
LLM_PROVIDER=claude_code
DEFAULT_MODEL=claude-code
GEMINI_API_KEY=
```

Optionally add a GitHub token to avoid rate limiting when the resume has a GitHub profile:

```
GITHUB_TOKEN=your_github_pat_here
```

---

## Step 3 — Verify the Claude CLI works

Run this in your terminal to confirm the `claude` binary is reachable:

```bash
claude -p "say hello"
```

You should get a short reply. If you get `command not found`, Claude Code is not on your PATH — restart your terminal or reinstall Claude Code.

---

## Step 4 — Run the evaluator

```bash
python score.py path/to/resume.pdf
```

Example:

```bash
python score.py resumes/john_doe.pdf
```

---

## What happens when you run it

1. **PDF → Markdown** — the resume is parsed page by page
2. **Section extraction** — the Claude CLI is called once per resume section (basics, work, education, skills, projects, awards) to extract structured JSON
3. **GitHub enrichment** — if a GitHub URL is found in the resume, repos are fetched and scored
4. **Evaluation** — a fairness-constrained score is produced (max 120 pts)
5. **Output** — a readable report is printed to your terminal

Since `DEVELOPMENT_MODE = True` in `config.py`:
- Intermediate results are cached in `cache/` — subsequent runs on the same PDF are much faster
- A row is appended to `resume_evaluations.csv` after each run

---

## Scoring breakdown

| Category         | Max pts |
|------------------|---------|
| Open source      | 35      |
| Self projects    | 30      |
| Production work  | 25      |
| Technical skills | 10      |
| Bonus            | 20      |
| **Total**        | **120** |

Deductions apply for tutorial-only projects, missing links, or Hacktoberfest-only contributions.

---

## Tips

**Speed up re-runs** — caching is on by default. Delete files in `cache/` to force a fresh extraction.

**Turn off caching** — set `DEVELOPMENT_MODE = False` in `config.py` if you want a clean run every time without CSV export either.

**The LLM is called many times per resume** — each section is a separate `claude -p` call, so a full evaluation takes a few minutes. This is normal.

**Claude Code must stay logged in** — if your session expires, run `claude` interactively once to re-authenticate, then re-run the evaluator.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `command not found: claude` | Restart terminal; reinstall Claude Code if needed |
| `RuntimeError: Claude Code CLI returned exit code 1` | Run `claude -p "test"` manually to check your login status |
| JSON parse errors in output | Usually a one-off; delete the cached file and re-run — the extraction will retry |
| GitHub rate limit warnings | Add `GITHUB_TOKEN=<your_pat>` to `.env` |
