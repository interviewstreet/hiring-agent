# Hiring Agent

<p align="center"><strong>Resume-to-Score pipeline</strong> that extracts structured data from PDFs, enriches with GitHub signals, and outputs a fair, explainable evaluation.</p>

<p align="center">
  <a href="https://www.python.org/downloads/release/python-3110/">
    <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-blue.svg">
  </a>
  <a href="https://github.com/interviewstreet/hiring-agent/blob/master/LICENSE">
    <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-yellow.svg">
  </a>
  <a href="https://github.com/psf/black">
    <img alt="Code style: Black" src="https://img.shields.io/badge/code%20style-Black-000000.svg">
  </a>
</p>

---

## Contents

- [Context and intent](#context-and-intent)
- [Coverage](#coverage)
- [Overview](#overview)
- [Architecture](#architecture)
- [Installation and Setup](#installation-and-setup)
  - [Prerequisites](#prerequisites)
  - [Quick setup with pip](#quick-setup-with-pip)
  - [Ollama models](#ollama-models)
- [Configuration](#configuration)
- [How it works](#how-it-works)
- [CLI usage](#cli-usage)
- [Directory layout](#directory-layout)
- [Provider details](#provider-details)
- [Contributing](#contributing)
- [License](#license)

---

## Context and intent

This project got a lot of attention recently, and some of the discussion surfaced misconceptions worth addressing directly.

**What this is not:**
- Not an ATS (Applicant Tracking System)
- Not used to screen HackerRank's open roles
- Not a product available to HackerRank customers

**What it actually is:**

Every year HackerRank receives 50,000–60,000 intern applications. No human can read that many resumes well. This tool was built to *rank* them — helping decide which resumes to read first. Resumes scoring below the cutoff are filtered out, but the cutoff is intentionally set very low so only candidates at the very bottom of the distribution are removed. The vast majority pass through to human review, where the real decisions are made.

Since this was built, HackerRank has also shipped [AI Interviewer (Chakra)](https://www.hackerrank.com/products/ai-interviewer/) to automate the first round of interviews — so candidates are no longer assessed on their resume alone.

**On the default model:**

This fork defaults to `google/gemini-3.1-pro-preview` through OpenRouter, with `google/gemini-3.8-flash` as an alternative. Both use JSON Schema structured output. Pro is a preview model; compare repeated runs before relying on scores.

Upstream defaults to the local `gemma4:latest` demo model. Actual intern resumes at HackerRank are evaluated using a top-tier Gemini model; upstream does not disclose the exact production model or configuration.

---

## Coverage

Articles and discussions that have shaped how we think about improving this project:

| Article | Key takeaway |
|---|---|
| [HackerRank open sourced its ATS. My resume scored 90/100. Oh wait 74/100. No — 88/100. Actually 83/100.](https://danunparsed.com/p/hackerrank-open-source-ats) — *Dan Kinsky* | Deep statistical analysis of score variance across 100 runs of the same resume. Isolates which categories are stable (technical skills) vs. noisy (project quality judgments). Points to LLM non-determinism as the root cause. |
| [The Score Depends on the Roll of the Dice](https://pinggy.io/blog/hackerrank_open_source_ats_inconsistent_scoring/) — *Pinggy Blog* | Reproduces the variance findings and surfaces a security issue: invisible text embedded in PDFs can inflate scores significantly. |
| [The Hiring Rubric Inside](https://byteiota.com/hackerrank-ats-open-source-the-hiring-rubric-inside/) — *ByteIota* | Breaks down the scoring weights and argues that a GitHub-centric rubric disadvantages engineers whose work is in private enterprise repos. Also notes the signal degradation risk as candidates optimize for the now-public rubric. |
| [Analyzing resume scoring consistency](https://dev.to/mgobea/hackerrank-open-sourced-its-ats-analyzing-resume-scoring-consistency-1j5d) — *Mariano Gobea Alcoba, DEV Community* | Proposes concrete fixes: standardized data formats, versioned evaluation models, ensemble scoring, and explainability layers to reduce variance and make the system more robust. |
| [AI-Powered Pipeline for Explainable Resume Scoring](https://aitoolly.com/ai-news/article/2026-06-26-interviewstreet-unveils-hiring-agent-an-ai-powered-pipeline-for-explainable-resume-scoring-and-githu) — *AIToolly* | Covers the launch and highlights the transparency argument — making scoring logic public allows scrutiny that proprietary ATS systems never face. |
| [Hacker News discussion](https://news.ycombinator.com/item?id=48713832) | 200+ comment thread covering LLM determinism, GDPR Article 22 implications, and the broader ethics of automated resume filtering. |

**Video coverage**

- [HackerRank Open-Sourced Their ATS?](https://www.youtube.com/shorts/0OP2bhYZQfc) — YouTube Short
- [HackerRank Open-Sourced ATS Tool for selecting Resume](https://www.youtube.com/shorts/UnHGC1Ywhys) — YouTube Short
- [HackerRank Custom ATS Released! Get Your Resume Score & Beat ATS Filters](https://www.youtube.com/watch?v=tQSve-xx4_8) — full walkthrough video

**Community tools built on this repo**

- [Resume Reality Check](https://resume-reality-check-seven.vercel.app/) — hosted tool that lets candidates score their own resume against the same rubric

---

## Overview

Hiring Agent parses a resume PDF to Markdown, extracts sectioned JSON using a local or hosted LLM, augments the data with GitHub profile and repository signals, then produces an objective evaluation with category scores, evidence, bonus points, and deductions. You can use Gemini through OpenRouter (the default in this fork), run fully local with Ollama, or use the other providers listed in `providers.json`.

---

## Architecture

<table>
<tr>
<td>

**Flow**

1. `pymupdf_rag.py` converts PDF pages to Markdown-like text.
2. `pdf.py` calls the LLM per section using Jinja templates under `prompts/templates`.
3. `github.py` fetches profile and repos, classifies projects, and asks the LLM to select the top 7.
4. `evaluator.py` runs a strict-scored evaluation with fairness constraints.
5. `score.py` orchestrates everything end to end and writes CSV when development mode is on.

</td>
<td>

**Key modules**

- `models.py`
  Pydantic schemas and LLM provider interfaces.

- `llm_utils.py`
  Provider initialization and response cleanup.

- `transform.py`
  Normalization from loose LLM JSON to JSON Resume style.

- `prompts/`
  All Jinja templates for extraction and scoring.

</td>
</tr>
</table>

---

## Installation and Setup

### Prerequisites

- **Python 3.11+**

  The repository pins `.python-version` to 3.11.13.

- **One LLM backend**

  - **OpenRouter** (default in this fork) with an exported `OPENROUTER_API_KEY`.
  - **Ollama** for local models
    Install from the [official site](https://ollama.com/), then run `ollama serve`.
  - **Google Gemini** if you have an API key, get it from [here](https://aistudio.google.com/api-keys).

### Quick setup with pip

```bash
$ git clone https://github.com/interviewstreet/hiring-agent
$ cd hiring-agent

$ python -m venv .venv
# Linux or macOS
$ source .venv/bin/activate
# Windows
# .venv\Scripts\activate

$ pip install -r requirements.txt
```

### Ollama Models

Pull the model you want to use. For example:

```bash
$ ollama pull gemma4:latest
```

If you want different results, you can pull other models such as:

```bash
# For higher system configuration
$ ollama pull gemma3:12b

# For lower system configuration
$ ollama pull gemma3:1b
```

---

## Configuration

Copy the template and set your environment variables.

```bash
$ cp .env.example .env
```

**Environment variables**

| Variable         | Values                                      | Description                                                            |
| ---------------- | ------------------------------------------- | ---------------------------------------------------------------------- |
| `DEFAULT_MODEL`  | for example `google/gemini-3.1-pro-preview`, `google/gemini-3.8-flash`, or `gemma4:latest` | Model to use; must exist in `providers.json` — the provider is inferred from which provider lists it. Defaults to `google/gemini-3.1-pro-preview` in this fork. |
| `OPENROUTER_API_KEY` | exported shell variable | Required for OpenRouter models. Reuse the shell key used by Pi; no need to copy it into this repo. |
| `GEMINI_API_KEY` | string                                      | Required when using a Gemini model.                                   |
| `OPENAI_API_KEY` | string                                      | Required when using an OpenAI model.                                  |
| `GITHUB_TOKEN`   | optional                                    | Inherits from your shell environment, improves GitHub API rate limits. |

Provider mapping lives in `providers.json` — each provider declares its `base_url`, an optional API-key env var, and per-model parameters; `config.py` loads it and resolves the provider for a model. `config.py` also has a flag:

```python
# config.py
DEVELOPMENT_MODE = True  # enables caching and CSV export
```

You can leave it on during iteration. See the next section for details.

---

## How it works

<details>
<summary><b>1) PDF extraction</b></summary>

- `pymupdf_rag.py` and `pdf.py` read the PDF using PyMuPDF and convert pages to Markdown-like text.
- The `to_markdown` routine handles headings, links, tables, and basic formatting.

</details>

<details>
<summary><b>2) Section parsing with templates</b></summary>

- `prompts/templates/*.jinja` define strict instructions for each section
  Basics, Work, Education, Skills, Projects, Awards.
- `pdf.PDFHandler` calls the LLM per section and assembles a `JSONResume` object (see `models.py`).

</details>

<details>
<summary><b>3) GitHub enrichment</b></summary>

- `github.py` extracts a username from the resume profiles, fetches profile and repos, and classifies each project.
- It asks the LLM to select exactly 7 unique projects with a minimum author commit threshold, favoring meaningful contributions.

</details>

<details>
<summary><b>4) Evaluation</b></summary>

- `evaluator.py` scores the resume against the **role** selected on the command line.
- Each role lives in `roles/<role_name>/` and defines its own scoring categories and weights in `role.json`, plus its own `criteria.jinja` and `system_message.jinja` prompts (encoding fairness and scoring rules).
- The shipped `software_engineering_intern` role scores `open_source`, `self_projects`, `production`, `technical_skills`, and `ai_fluency`, plus bonus and deductions, with evidence for each. Other roles can define entirely different categories.
- The intern role defines `bonus_rules` in `role.json`. The LLM returns evidence and allowed point values for each named bonus; Python calculates the total and itemized explanation. For HackerRank Orchestrate, the model supplies the best rank from awards and its points; Python validates +4 for ranks 1–100, +3 for 101–200, +1 for 201–500, and 0 otherwise, once per candidate. All bonuses share the 20-point cap. Roles without `bonus_rules` keep the original total-and-breakdown response format. Evidence interpretation still depends on the LLM.
- This fork adds a `senior_software_engineer` role. It scores `impact_ownership` (30), `technical_depth` (25), `leadership` (20), `communication_community` (15), and `ai_fluency` (10) out of 100, with up to 10 bonus points (founder, early-stage engineer, open-source maintainer, patents or publications) and at most 5 points of deductions. Its prompts tell the model to ignore total years of experience, career gaps, and employer prestige, and not to penalize a lack of public code outside `communication_community`.
- `tests/test_roles.py` checks that every role's prompts restate the category limits, bonus cap, and bonus keys from its `role.json`.

</details>

<details>
<summary><b>5) Output and CSV export</b></summary>

- `score.py` prints a readable summary to stdout.
- When `DEVELOPMENT_MODE=True` it creates or appends a per-role `resume_evaluations_<role>.csv` with key fields (columns follow the role's categories), and caches intermediate JSON under `cache/`.

</details>

---

## CLI usage

### End to end scoring

Provide a path to a resume PDF and the role to score against. `--role` is the
name of a directory under `roles/` and is **required**.

```bash
$ python score.py ./resume/sample.pdf --role software_engineering_intern
```

What happens:

1. If development mode is on, the PDF extraction result is cached to `cache/resumecache_<basename>.json`.
2. If a GitHub profile is found in the resume, repositories are fetched and cached to `cache/githubcache_<basename>.json`.
3. The evaluator scores the resume against the selected role, prints a report and, in development mode, appends a CSV row to `resume_evaluations_<role>.csv`.

### Roles

A role bundles its rubric in `roles/<role_name>/`:

```text
roles/software_engineering_intern/
├── role.json           # categories, weights (max), bonus_max, score bounds, position_title
├── criteria.jinja      # evaluation criteria prompt (receives {{ text_content }})
└── system_message.jinja
```

`role.json` drives the scoring schema, the printed report, the CSV columns, and
the score caps — so each role can score against its own categories and weights.

To add a role, scaffold one with basic template files and then edit them:

```bash
$ python score.py --init-role backend_engineer
# edit roles/backend_engineer/{role.json,criteria.jinja,system_message.jinja}
$ python score.py ./resume/sample.pdf --role backend_engineer
```

`--init-role` creates the role directory with placeholder categories and prompts
(it only scaffolds; it does not score a resume). You can also copy an existing
role directory instead.

---

## Directory layout

```text
.
├── .env.example
├── .python-version
├── config.py
├── evaluator.py
├── github.py
├── llm_utils.py
├── models.py
├── pdf.py
├── prompt.py
├── prompts/
│   ├── template_manager.py
│   └── templates/
│       ├── awards.jinja
│       ├── basics.jinja
│       ├── education.jinja
│       ├── github_project_selection.jinja
│       ├── projects.jinja
│       ├── skills.jinja
│       ├── system_message.jinja
│       └── work.jinja
├── providers.json
├── pymupdf_rag.py
├── requirements.txt
├── roles.py
├── roles/
│   └── software_engineering_intern/
│       ├── role.json
│       ├── criteria.jinja
│       └── system_message.jinja
├── score.py
└── transform.py
```

---

## Provider details

### OpenRouter (default)

- Endpoint: `https://openrouter.ai/api/v1`, using the existing `models.OpenAICompatibleProvider`.
- Default: `google/gemini-3.1-pro-preview`; alternative: `google/gemini-3.8-flash`.
- Both models use `json_schema` structured output and temperature `0.1`.
- Authentication reads `OPENROUTER_API_KEY` from the process environment. If your shell already exports it for Pi, run this project from that shell; do not put the key into tracked files.
- An untracked `.env` is optional. Exported shell variables take precedence over `.env` values.
- Model IDs with the `google/` prefix select OpenRouter; unprefixed IDs such as `gemini-3.8-flash` select the direct Google provider and require `GEMINI_API_KEY` instead.

```bash
# With dependencies installed and OPENROUTER_API_KEY exported:
python score.py /path/to/resume.pdf

# Compare against Flash without changing the default:
DEFAULT_MODEL=google/gemini-3.8-flash python score.py /path/to/resume.pdf

# Optional explicit Pro selection:
DEFAULT_MODEL=google/gemini-3.1-pro-preview python score.py /path/to/resume.pdf
```

Check configuration and request construction without model calls or real credentials:

```bash
python -m unittest discover -s tests -v
```

### Ollama

- Set `DEFAULT_MODEL` to any pulled model listed in `providers.json`, for example `gemma4:latest`
- Requests go through `models.OpenAICompatibleProvider` against Ollama's OpenAI-compatible endpoint (`http://localhost:11434/v1`)

### Gemini

- Set `DEFAULT_MODEL` to a Gemini model listed in `providers.json`, for example `gemini-3.8-flash`
- Provide `GEMINI_API_KEY`
- The same `models.OpenAICompatibleProvider` wrapper is used, pointed at Gemini's OpenAI-compatible endpoint

### OpenAI

- Set `DEFAULT_MODEL` to an OpenAI model listed in `providers.json`, for example `gpt-6-luna`
- Provide `OPENAI_API_KEY`
- Requests use OpenAI Chat Completions with JSON Schema structured output

---

## Contributing

Please read the [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed guidelines on filing issues, proposing changes, and submitting pull requests. Key principles include:

- Keep prompts declarative and provider-agnostic.
- Validate changes with a couple of real resumes under different providers.
- Add or adjust unit-free smoke tests that call each stage with minimal inputs.

---


## License

[MIT](https://github.com/interviewstreet/hiring-agent/blob/master/LICENSE) © HackerRank
