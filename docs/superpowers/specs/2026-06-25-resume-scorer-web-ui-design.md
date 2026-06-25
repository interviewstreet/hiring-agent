# Privacy-first Resume Scorer — Web UI

**Date:** 2026-06-25
**Status:** Approved design, pre-implementation
**Author:** Akash Kalita (`1akashkalita`)
**Target:** Contribution to `interviewstreet/hiring-agent` (web UI under `web/`)

---

## Overview

A browser-based web UI for the existing Hiring Agent resume scorer, deployed on Vercel. It makes the tool accessible to non-developers, adds **trend tracking** so people can see whether their resume is improving over time, and adds a **resume coach** that explains in plain language what's good, what's weak, and what to fix next.

The defining constraint is **privacy**: the app runs entirely in the browser. There is no backend of ours. Resumes and results are stored only in the browser's local cache, and scoring happens via the user's own Google Gemini API key, called directly from the browser.

## Goals

- Give the existing pipeline (PDF → structured resume → GitHub enrichment → scored evaluation) a friendly web interface.
- Default to **Google Gemini**; the user supplies their own API key.
- Store uploaded resumes and their results in the **browser cache only** — fully private, no server, no account.
- **Trends:** let users see their total and per-category scores over time and tell whether they're improving.
- **Coaching:** after scoring, summarize which categories are strong vs. weak and give prioritized, actionable improvement guidance.

## Non-goals (out of scope for v1)

- OCR of image-only / scanned PDFs (we require selectable text).
- Providers other than Gemini (no Ollama in the browser; no OpenAI/etc.).
- Any server-side processing, accounts, or cross-device sync.
- Changing the existing Python tool's behavior.

---

## Key decisions

These were settled during brainstorming:

| Decision | Choice | Rationale |
|---|---|---|
| Where processing happens | **Pure client-side** (browser only) | Strongest privacy: the resume never touches a server we control. Vercel serves static assets only. |
| LLM provider | **Gemini**, bring-your-own key | Matches the original's hosted option; BYO key keeps it private and free for us to host. |
| GitHub enrichment | **Optional**, bring-your-own GitHub token | Preserves the original's strongest signal; a token lifts the 60 req/hr unauthenticated cap to 5000. |
| Trend grouping | **Flat chronological history** + optional resume naming | Simplest base; the optional name lets us draw a per-resume trend line on demand. |
| Improvement summary | **Separate "resume coach" Gemini call** | Richest, most tailored advice; the explanation feature is a headline value of this version. |
| Resume extraction | **Single combined Gemini call** (not the original's 6 per-section calls) | Gemini's context + structured output makes one call reliable; saves the user's quota and latency. |

---

## Architecture

- **Stack:** Next.js (App Router) built as a **static export** (`output: 'export'`), deployed on Vercel as static assets. No API routes, no server runtime — there is no backend, which is what makes the privacy guarantee airtight.
- **Location:** self-contained under `web/` in the repo, with its own `package.json`. No existing files changed except adding `web/`. Vercel project root = `web/`.
- **Language/logic:** the relevant Python logic is ported to TypeScript (see Pipeline). This is a deliberate, accepted cost of the pure-client-side approach — two copies of the scoring rubric and normalization logic to keep roughly in sync with the Python source.

### Pipeline (TypeScript port)

Per scoring run, all in the browser, all with the user's key:

1. **PDF → text** — `pdfjs-dist` extracts selectable text in-browser.
2. **Text → JSON Resume** — **one** Gemini call in native JSON mode (`responseSchema`) returns the full structured resume. The normalization logic from `transform.py` is ported to TS to map loose model output into the canonical shape.
3. **GitHub enrichment (optional)** — if a GitHub token is set: fetch profile + repos, classify open-source vs. self-project, and run the LLM project-selection call. Ported from `github.py`.
4. **Scoring** — one Gemini call returning the `EvaluationData` shape. The fairness-constrained rubric from `resume_evaluation_criteria.jinja` is ported faithfully; category caps (open_source 35, self_projects 30, production 25, technical_skills 10; bonus ≤ 20; total ≤ 120) are enforced client-side like `score.py`.
5. **Coach** — a separate Gemini call producing the prioritized "biggest score left on the table" fixes plus "small boosts" for already-strong categories.

Typical cost: **~3 Gemini calls per run** (4 with GitHub enrichment).

---

## Data model & storage

- **IndexedDB** (via the `idb` library) stores the run history. Each run record:
  - `id`, `createdAt` (timestamp)
  - `fileName`, optional user `label`
  - `parsedResume` (JSON Resume)
  - `evaluation` (scores + evidence + bonus + deductions + key strengths + areas for improvement)
  - `coach` (prioritized fixes + small boosts)
  - `githubSummary` (optional)
  - `pdfBlob` (the original PDF, so a run can be re-viewed)
- **localStorage** stores settings: theme (light/dark), and API keys. A **"remember key on this device"** toggle: when off, keys are kept only for the session (in memory) and not persisted.
- **Trends and diffs** are computed client-side from stored runs (total over time, per-category sparklines, run-to-run score diff).
- **Clear all data** (Settings) wipes IndexedDB + localStorage; per-run delete also supported.

---

## Visual design system

Thesis: **a human document (the resume) measured by a precise machine (the scorer), iterated like code.** The design embodies that tension; the workflow (re-score an improved resume, watch the delta) is treated like a version-controlled changelog.

- **Type:**
  - *Instrument Serif* — human/verdict voice (headlines, the grade verdict, coach suggestions). Used with restraint.
  - *Archivo* — UI and body text.
  - *JetBrains Mono* — all data: scores, deltas, category tags, timestamps, the changelog.
- **Color (light theme):** cool drafting-paper background `#E7EAEE`, ink `#15181D`, hairline `#D3D9DF`, brand **ultramarine-violet** `#3A2DD0`. Semantic colors are **reserved for score meaning** and are deliberately not the brand color: good `#2F7A57` (emerald), needs-work `#BA413B` (clay), in-between `#A9741B` (ochre).
- **Dark theme:** deep blue-ink background `#0F1320` (not flat black), keeping the same brand violet and semantic colors. Toggled via a sun/moon switch; persisted in settings.
- **Signature element — the revision rail:** scored runs rendered as a commit-log-style vertical rail of nodes, each with its total and a colored delta (`▲ +6` / `▼ -3`); selecting two runs surfaces a score diff. This is the memorable element and directly answers "am I improving?"
- **One delta vocabulary everywhere:** point movements and potential coach gains both render as mono `▲ +N` / `▼ -N`, colored by good/bad.
- **Quality floor:** responsive to mobile, visible keyboard focus, `prefers-reduced-motion` respected.

## Screens

1. **Score** — upload (drag-drop PDF), shows key status; runs the pipeline with progress.
2. **Results** — the verdict (serif), the scorecard (total /120 with delta vs. previous; four category rows with bars, status, and per-category deltas), and the **Coach** section: *Biggest score left on the table* (high-impact fixes, full editorial notes) and *Small boosts* (compact one-liners for strong categories).
3. **History & Trends** — summary strip (latest, personal best, net change, run count); total-score-over-time line chart on the drafting grid; per-category trend sparklines; and the run history changelog (name + optional label with inline rename, score, delta, View / Diff actions).
4. **Settings** — Gemini key (required) + optional GitHub token, the "remember key" toggle, theme, and Clear all data.

A persistent **100% PRIVATE** chip opens a privacy explainer modal that is honest about the one nuance: resume text does go to Google Gemini, but via the user's own key, never through a server of ours.

---

## Error handling

- **Missing/invalid Gemini key** → inline error pointing to Settings; pipeline does not start.
- **Gemini 429 / quota** → exponential backoff with jitter (ported from the existing `GeminiProvider`); a clear message if retries are exhausted.
- **Image-only PDF (no extractable text)** → explicit "no selectable text found" message (no OCR in v1).
- **Schema-invalid model output** → validate with Zod, retry once, then surface a readable error with the raw response available.
- **GitHub 404 / 403 / network** → degrade gracefully; scoring proceeds without enrichment, with a note.

## Privacy guarantees (as stated to the user)

1. Everything runs in the browser; no backend of ours handles the resume.
2. Scoring goes straight from the browser to Google Gemini with the user's own key; we never see the key or the resume.
3. Scores and past resumes are saved in the browser's local cache, not a database.
4. Clearing browser data (or Settings → Clear all data) erases everything instantly. No tracking, no sign-in, works offline once loaded.

## Testing

- **Vitest** unit tests on the deterministic logic: the `transform`/normalization port, score capping, run-to-run diff computation, prompt assembly — with the Gemini client mocked.
- One light **Playwright** smoke test: upload a sample PDF with a mocked Gemini response and assert the results render.

---

## Contribution & deployment path

- Work happens on `feat/web-ui` in the fork `1akashkalita/hiring-agent` (`origin`); `upstream` is `interviewstreet/hiring-agent`.
- **Recommended:** open an upstream issue proposing the web UI and get maintainer buy-in before the PR lands, per the repo's `CONTRIBUTING.md`.
- PR is opened from `1akashkalita:feat/web-ui` into `interviewstreet:main`. Keeping all changes under `web/` (no edits to existing files) makes review and acceptance far easier.
- Independent of upstream acceptance, the fork can be deployed to Vercel directly — the app stands alone.

## Risks & open questions

- **Logic duplication:** the scoring rubric and transforms now exist in both Python and TS; they can drift. Mitigation: keep the ported rubric text and category caps in one well-commented module that cites the Python source.
- **Score comparability:** a single extraction call + Gemini (vs. the original's six calls, often local models) may produce somewhat different scores than the Python tool. Acceptable — this is a standalone experience — but worth a note in the UI/README that scores are indicative.
- **Gemini quota:** ~3–4 calls/run can hit free-tier limits on heavy use; the backoff and clear messaging handle this, and it's the user's own key.
- **Maintainer acceptance:** a large unsolicited feature may not be merged; the issue-first step and standalone Vercel deploy de-risk the effort.
