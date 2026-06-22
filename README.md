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

## Overview

Hiring Agent parses a resume PDF to Markdown, extracts sectioned JSON using a local or hosted LLM, augments the data with GitHub profile and repository signals, then produces an objective evaluation with category scores, evidence, bonus points, and deductions. It defaults to fully local **Ollama** and can also run with **Google Gemini** or, with no API key, through an already-authenticated local **Claude Code CLI** or **Codex CLI**.

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

- **One LLM backend** (any one of them)

  - **Ollama** for local models
    Install from the [official site](https://ollama.com/), then run `ollama serve`.
  - **Google Gemini** if you have an API key, get it from [here](https://aistudio.google.com/api-keys).
  - **Claude Code CLI** (no API key) - uses your existing Claude Code
    subscription / session. Install from [claude.com/claude-code](https://claude.com/claude-code),
    then run `claude` once and sign in. Verify with `claude --version`.
  - **Codex CLI** (no API key) - uses your existing Codex session. Verify with
    `codex --version` and sign in with `codex login` if needed.

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
$ ollama pull gemma3:4b
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

| Variable                      | Values                                                | Description                                                                  |
| ----------------------------- | ----------------------------------------------------- | --------------------------------------------------------------------------- |
| `LLM_PROVIDER`                | `ollama`, `gemini`, `claude_code`, or `codex`         | Chooses the provider. CLI providers are forced when set, regardless of model. |
| `DEFAULT_MODEL`               | e.g. `gemma3:4b`, `gemini-2.5-pro`, `claude-code`, or `codex-cli` | Model name passed to the provider. Use `claude-code` or `codex-cli` for CLI mode. |
| `CLAUDE_CODE_COMMAND`         | optional, default `claude`                            | Command or full path to the Claude Code CLI.                                |
| `CLAUDE_CODE_TIMEOUT_SECONDS` | optional, default `300`                               | Per-call timeout for the Claude Code CLI.                                    |
| `CLAUDE_CODE_MODEL`           | optional, e.g. `sonnet`                               | Pin a specific model for nested calls. Empty = your session default.        |
| `CODEX_COMMAND`               | optional, default `codex`                             | Command or full path to the Codex CLI.                                      |
| `CODEX_TIMEOUT_SECONDS`       | optional, default `300`                               | Per-call timeout for the Codex CLI.                                         |
| `CODEX_MODEL`                 | optional                                              | Pin a specific Codex model for nested calls. Empty = Codex CLI default.     |
| `GEMINI_API_KEY`              | string                                                | Required when `LLM_PROVIDER=gemini`.                                         |
| `GITHUB_TOKEN`                | optional                                              | Inherits from your shell environment, improves GitHub API rate limits.      |

Provider mapping lives in `prompt.py` and `models.py`. The `config.py` file has a single flag:

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

- `evaluator.py` uses templates that encode fairness and scoring rules.
- Scores include `open_source`, `self_projects`, `production`, and `technical_skills`, plus bonus and deductions, then an explanation for evidence.

</details>

<details>
<summary><b>5) Output and CSV export</b></summary>

- `score.py` prints a readable summary to stdout.
- When `DEVELOPMENT_MODE=True` it creates or appends a `resume_evaluations.csv` with key fields, and caches intermediate JSON under `cache/`.

</details>

---

## CLI usage

### End to end scoring

Provide a path to a resume PDF.

```bash
$ python score.py /path/to/resume.pdf
```

> On systems where `python` is not on `PATH`, use `python3` instead:
>
> ```bash
> $ python3 score.py /path/to/resume.pdf
> ```

#### Run with Claude Code (no API key)

Set these values in `.env`:

```bash
LLM_PROVIDER=claude_code
DEFAULT_MODEL=claude-code
CLAUDE_CODE_COMMAND=claude
CLAUDE_CODE_TIMEOUT_SECONDS=300
```

Then run:

```bash
$ claude --version            # confirm the CLI is installed and signed in
$ python3 score.py /path/to/resume.pdf
```

Each pipeline run makes **multiple** LLM calls per resume (one per resume
section, GitHub project selection, and the final evaluation), and every call
shells out to `claude`. Expect it to be **slower** than Ollama and to consume
Claude Code usage accordingly. Pin a cheaper model with `CLAUDE_CODE_MODEL`
(for example `sonnet`) to reduce cost.

#### Run with Codex (no API key)

Set these values in `.env`:

```bash
LLM_PROVIDER=codex
DEFAULT_MODEL=codex-cli
CODEX_COMMAND=codex
CODEX_TIMEOUT_SECONDS=300
# CODEX_MODEL=
```

Then run:

```bash
$ codex --version             # confirm the CLI is installed
$ codex login                 # sign in if needed
$ python3 score.py /path/to/resume.pdf
```

Codex mode uses the same shared CLI provider wrapper as Claude Code mode, but
builds Codex-specific commands with `codex exec`, `--ephemeral`, read-only
sandboxing, and `--output-schema` for structured calls. Leave `CODEX_MODEL`
unset to use the Codex CLI's configured default model.

What happens:

1. If development mode is on, the PDF extraction result is cached to `cache/resumecache_<basename>.json`.
2. If a GitHub profile is found in the resume, repositories are fetched and cached to `cache/githubcache_<basename>.json`.
3. The evaluator prints a report and, in development mode, appends a CSV row to `resume_evaluations.csv`.

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
│       ├── resume_evaluation_criteria.jinja
│       ├── resume_evaluation_system_message.jinja
│       ├── skills.jinja
│       ├── system_message.jinja
│       └── work.jinja
├── pymupdf_rag.py
├── requirements.txt
├── score.py
└── transform.py
```

---

## Provider details

### Claude Code (no API key)

- Set `LLM_PROVIDER=claude_code` and `DEFAULT_MODEL=claude-code`
- Requires the `claude` CLI installed and authenticated; no `ANTHROPIC_API_KEY`
  or any other key is used
- `models.CliLLMProvider` shells out to `claude -p` in non-interactive print
  mode with all built-in tools disabled (`--tools ""`) and project config
  isolated (`--safe-mode`), so the nested Claude only answers the prompt; it
  never edits files, runs commands, or acts as a recursive coding agent
- System messages are passed through `--system-prompt`; JSON schemas
  (`kwargs["format"]`) are passed through Claude Code's native `--json-schema`
  flag; the CLI's stdout is adapted to the unified
  `{"message": {"content": ...}}` shape
- Tune with `CLAUDE_CODE_COMMAND`, `CLAUDE_CODE_TIMEOUT_SECONDS`, and the
  optional `CLAUDE_CODE_MODEL`

### Codex CLI (no API key)

- Set `LLM_PROVIDER=codex` and `DEFAULT_MODEL=codex-cli`
- Requires the `codex` CLI installed and authenticated with `codex login`; no
  separate API key is required
- `models.CliLLMProvider` shells out to `codex exec` with `--ephemeral`,
  `--ignore-rules`, `--ignore-user-config`, and read-only sandboxing, so each
  nested call behaves like a constrained text-generation step
- JSON schemas (`kwargs["format"]`) are written to a temporary schema file and
  passed through Codex's native `--output-schema` flag
- Tune with `CODEX_COMMAND`, `CODEX_TIMEOUT_SECONDS`, and the optional
  `CODEX_MODEL`

### Ollama

- Set `LLM_PROVIDER=ollama`
- Set `DEFAULT_MODEL` to any pulled model, for example `gemma3:4b`
- The provider wrapper in `models.OllamaProvider` calls `ollama.chat`

### Gemini

- Set `LLM_PROVIDER=gemini`
- Set `DEFAULT_MODEL` to a supported Gemini model, for example `gemini-2.0-flash`
- Provide `GEMINI_API_KEY`
- The wrapper in `models.GeminiProvider` adapts responses to a unified format

---

## Contributing

Please read the [CONTRIBUTING.md](./CONTRIBUTING.md) for detailed guidelines on filing issues, proposing changes, and submitting pull requests. Key principles include:

- Keep prompts declarative and provider-agnostic.
- Validate changes with a couple of real resumes under different providers.
- Add or adjust unit-free smoke tests that call each stage with minimal inputs.

---


## License

[MIT](https://github.com/interviewstreet/hiring-agent/blob/master/LICENSE) © HackerRank
