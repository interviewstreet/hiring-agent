# Hiring Agent

<p align="center"><strong>Resume-to-Score pipeline</strong> that extracts structured data from PDFs, enriches with GitHub signals, scores against a public rubric, and produces an explainable HTML report.</p>

<p align="center">
  <a href="https://www.python.org/downloads/release/python-3110/">
    <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-blue.svg">
  </a>
  <a href="https://github.com/interviewstreet/hiring-agent/blob/master/LICENSE">
    <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-yellow.svg">
  </a>
</p>

---

## Contents

- [Context and intent](#context-and-intent)
- [Overview](#overview)
- [Pipeline](#pipeline)
- [Installation](#installation)
- [Configuration](#configuration)
  - [LLM and API keys](#llm-and-api-keys)
  - [Feature flags](#feature-flags)
  - [Recommended profiles](#recommended-profiles)
  - [LLM call budget](#llm-call-budget)
- [CLI usage](#cli-usage)
- [Scoring rubric](#scoring-rubric)
- [Outputs](#outputs)
- [Directory layout](#directory-layout)
- [Contributing](#contributing)
- [License](#license)

---

## Context and intent

**What this is not:**

- Not an ATS (Applicant Tracking System)
- Not used to screen HackerRank's open roles
- Not a product available to HackerRank customers

**What it actually is:**

Every year HackerRank receives 50,000–60,000 intern applications. No human can read that many resumes well. This tool was built to *rank* them — helping decide which resumes to read first. Resumes scoring below the cutoff are filtered out, but the cutoff is intentionally set very low so only candidates at the very bottom of the distribution are removed. The vast majority pass through to human review.

The repo ships with `gemma4:latest` as the default because it runs locally on most laptops without a cloud API key. Production evaluations at HackerRank use a top-tier Gemini model. This repo ships a demo config, not the production one.

---

## Overview

Hiring Agent:

1. Converts a resume PDF to Markdown
2. Extracts sectioned JSON (basics, work, education, skills, projects, awards)
3. Runs optional integrity, writing-quality, and blog checks
4. Enriches with GitHub profile and repository signals
5. Evaluates against a fixed Software Intern rubric with fairness constraints
6. Normalizes scores, computes confidence, and writes CSV + HTML report

Run fully local with Ollama, or use Google Gemini via `providers.json`.

---

## Pipeline

```text
PDF
 └─ Stage 0   PDF integrity scan          (ENABLE_PDF_INTEGRITY)
 └─ Stage 1   Section extraction (LLM)
 └─ Stage 1.5 Writing quality review      (ENABLE_WRITING_QUALITY)
 └─ Stage 2   GitHub enrichment
 └─ Stage 2.5 Blog URL fetch               (ENABLE_BLOG_ENRICHMENT)
 └─ Stage 3   Technical evaluation (LLM)
 └─ Stage 3.5 Score validation + confidence (ENSEMBLE_RUNS)
 └─ Stage 4   HTML web report             (ENABLE_WEB_REPORT)
```

Batch ranking (`batch_score.py`) reuses single-resume scoring and adds percentile ranks + cutoff export.

---

## Installation

### Prerequisites

- **Python 3.11+** (see `.python-version`)
- **One LLM backend:**
  - [Ollama](https://ollama.com/) for local models (`ollama serve`)
  - **Google Gemini** — set `GEMINI_API_KEY` in `.env`

### Setup

```bash
git clone https://github.com/interviewstreet/hiring-agent
cd hiring-agent

python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows
# .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
```

Pull a local model (example):

```bash
ollama pull gemma4:latest
```

---

## Configuration

Copy `.env.example` to `.env` and adjust flags. All feature toggles are loaded by `config.py`.

```bash
cp .env.example .env
```

### LLM and API keys

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_MODEL` | `gemma4:latest` | Model name from `providers.json`. Provider (`ollama` / `gemini`) is inferred automatically. |
| `GEMINI_API_KEY` | — | Required when `DEFAULT_MODEL` is a Gemini model. |
| `GITHUB_TOKEN` | — | Optional. Set in your shell to improve GitHub API rate limits. |

Provider mapping lives in `providers.json` — each provider declares `base_url`, optional `api_key_env`, and per-model parameters.

`DEVELOPMENT_MODE` in `config.py` (currently `True`) enables resume/GitHub/blog caching under `cache/` and CSV export to `resume_evaluations.csv`.

---

### Feature flags

#### PDF integrity (Stage 0)

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_PDF_INTEGRITY` | `true` | Scan PDFs for hidden/off-page text before any LLM calls. Pure PyMuPDF — no extra LLM cost. |
| `BLOCK_ON_PDF_INTEGRITY_FAIL` | `false` | When `true`, abort scoring if critical integrity issues are found. Keep `false` globally to avoid false positives on unusual PDF exports. |

#### Score validation (Stage 3.5)

| Variable | Default | Description |
|----------|---------|-------------|
| `ENSEMBLE_RUNS` | `1` | Number of evaluation LLM calls per resume. Set `3` for mean ± std dev confidence bands. Each extra run adds one full evaluation call (3× cost at `3`). |

Enforcement (category caps, bonus ≤ 20, `final_score` in CSV) is always on — not gated by a flag.

#### Writing quality (Stage 1.5)

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_WRITING_QUALITY` | `true` | Run spell-check on raw PDF text. Advisory only — does not change the rubric score. |
| `WRITING_QUALITY_USE_LLM` | `false` | When `true`, add one LLM call for grammar and clarity suggestions. |

#### Blog enrichment (Stage 2.5)

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_BLOG_ENRICHMENT` | `true` | Discover blog URLs from resume profiles and GitHub; fetch page metadata over HTTP. |
| `ENABLE_BLOG_LLM_SCORING` | `false` | When `true`, add one LLM call to score blog post quality (0–10). |

#### Batch ranking (Stage 4 CLI)

| Variable | Default | Description |
|----------|---------|-------------|
| `BATCH_CUTOFF_PERCENTILE` | `15` | Default bottom percentile filtered out by `batch_score.py --cutoff`. A cutoff of `15` removes the bottom 15% of a batch. |

#### Web report

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_WEB_REPORT` | `true` | Generate a standalone HTML report after each `score.py` run. |
| `WEB_REPORT_OUTPUT_DIR` | `reports` | Directory for HTML output (`reports/{Name}_{timestamp}_report.html`). |
| `ENABLE_REPORT_LLM` | `false` | When `true`, add one LLM call for per-bullet commentary and 0–10 point scores in the report. Without this, bullets show section-level grades and rubric evidence only. |

---

### Recommended profiles

**Batch intern screening (default — no extra LLM calls beyond baseline):**

```bash
ENABLE_PDF_INTEGRITY=true
BLOCK_ON_PDF_INTEGRITY_FAIL=false
ENSEMBLE_RUNS=1
ENABLE_WRITING_QUALITY=true
WRITING_QUALITY_USE_LLM=false
ENABLE_BLOG_ENRICHMENT=true
ENABLE_BLOG_LLM_SCORING=false
ENABLE_WEB_REPORT=true
ENABLE_REPORT_LLM=false
```

**High-stakes / audit (borderline candidate or score stability check):**

```bash
ENSEMBLE_RUNS=3
WRITING_QUALITY_USE_LLM=true
ENABLE_BLOG_LLM_SCORING=true
ENABLE_REPORT_LLM=true
```

---

### LLM call budget

Per resume (plus +1 GitHub project-selection call when a GitHub profile is found):

| Profile | Extraction | Writing | Blog | Evaluation | Report | **Total** |
|---------|------------|---------|------|------------|--------|-----------|
| Default recommended | 6 | 0 | 0 | 1 | 0 | **7** |
| Full enrichment | 6 | 1 | 1 | 1 | 1 | **10** |
| Full + ensemble (`ENSEMBLE_RUNS=3`) | 6 | 1 | 1 | 3 | 1 | **12** |

Stages 0 (PDF integrity), 1.5 spell-check, and blog HTTP fetch add no LLM calls.

---

## CLI usage

### Score a single resume

```bash
python score.py path/to/resume.pdf
```

What happens:

1. PDF integrity scan (if enabled)
2. Section extraction → cached to `cache/resumecache_{basename}.json` in dev mode
3. Writing quality review (if enabled)
4. GitHub fetch → cached to `cache/githubcache_{basename}.json`
5. Blog metadata fetch → cached to `cache/blogcache_{basename}.json`
6. Evaluation with score validation and confidence
7. CSV row appended to `resume_evaluations.csv` (dev mode)
8. HTML report written to `reports/` (if enabled)

The terminal prints the report path:

```text
📄 Web report saved: reports/Yash_Suvarna_20260725_190802_report.html
   Open in browser: file:///...
```

### Batch score and rank

```bash
# Score all PDFs in a folder; write ranked CSV
python batch_score.py ./resumes/ --cutoff 15 --output ranked.csv

# Re-rank an existing CSV without re-scoring
python batch_score.py --rank-only resume_evaluations.csv --output ranked.csv
```

| Flag | Description |
|------|-------------|
| `--cutoff` | Bottom percentile to filter (default: `BATCH_CUTOFF_PERCENTILE`) |
| `--output` | Output CSV path (default: `ranked_resumes.csv`) |
| `--rank-only` | Re-rank existing CSV; skip PDF processing |

---

## Scoring rubric

Fixed rubric for a **Software Intern** role at HackerRank. Prompts in `prompts/templates/resume_evaluation_*.jinja`.

| Category | Max | Measures |
|----------|-----|----------|
| Open Source | 35 | Contributions to *other people's* projects — not personal repos alone |
| Self Projects | 30 | Project complexity, impact, documentation |
| Production | 25 | Work/internship experience; startup founder/early engineer weighted higher |
| Technical Skills | 10 | Languages, frameworks, breadth across resume |
| **Category total** | **100** | Sum of the four categories |
| Bonus | +20 max | GSoC, Girl Script Summer of Code, startup roles, portfolio, blogs, etc. |
| Deductions | subtract | Tutorial-only portfolios, broken links, Hacktoberfest-only OSS |

**Fairness:** Scores never use name, gender, school, GPA, or location.

**Final score** = category total + bonus − deductions (capped at 120, floor −20).

The HTML report includes a collapsible **"How scoring works"** section explaining every metric.

---

## Outputs

| Output | Location | When |
|--------|----------|------|
| Terminal summary | stdout | Always |
| CSV row | `resume_evaluations.csv` | `DEVELOPMENT_MODE=True` |
| HTML report | `reports/{name}_{timestamp}_report.html` | `ENABLE_WEB_REPORT=true` |
| Resume cache | `cache/resumecache_*.json` | Dev mode |
| GitHub cache | `cache/githubcache_*.json` | Dev mode |
| Blog cache | `cache/blogcache_*.json` | Dev mode |

CSV columns include `final_score`, `confidence_level`, `score_std_dev`, writing quality fields, PDF integrity, and blog metadata.

---

## Directory layout

```text
.
├── batch_score.py          # Batch score + percentile ranking
├── blog.py                 # Blog URL discovery and fetch
├── config.py               # Env flags + providers loader
├── evaluator.py            # LLM evaluation
├── github.py               # GitHub enrichment
├── pdf_integrity.py        # PDF security scan
├── pdf.py                  # PDF → JSON extraction
├── ranking.py              # Percentile + cutoff helpers
├── score.py                # Main orchestrator
├── score_validation.py     # Score caps, final_score, confidence
├── web_report.py           # HTML report generator
├── writing_quality.py      # Spell check + optional grammar LLM
├── providers.json          # LLM provider config
├── prompts/templates/      # Jinja prompts + resume_report.html.jinja
├── reports/                # Generated HTML reports (gitignored)
├── cache/                  # Dev-mode caches (gitignored)
└── docs/superpowers/plans/ # Implementation plans
```

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). Keep prompts declarative and provider-agnostic. Validate changes with a couple of real resumes under different providers.

---

## License

[MIT](https://github.com/interviewstreet/hiring-agent/blob/master/LICENSE) © HackerRank
