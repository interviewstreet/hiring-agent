# Hiring Agent — Web UI

A **privacy-first, in-browser resume scorer**. Upload a resume PDF and get an
explainable, fairness-constrained score, a plain-language coach, and trend
tracking over time — all running entirely in your browser. Your resume and your
API key never touch a server we control.

> **Live demo:** **https://web-eight-black-28.vercel.app**

---

## What this is (and why it exists)

The original [Hiring Agent](../README.md) is a Python **CLI** resume-to-score
pipeline. This fork adds a **browser front-end** for it so non-developers can use
the tool without installing Python, Ollama, or anything else — while keeping the
strongest possible privacy guarantee.

The defining constraint is **privacy**: the app is a **static site** (no backend
of ours). PDF parsing happens client-side with `pdfjs-dist`; scoring happens via
**Google Gemini, called directly from your browser with your own API key**. Your
resume, your key, and your entire run history stay on your device
(`localStorage` + `IndexedDB`).

It also adds two things the CLI doesn't have:

- **Trend tracking** — re-score an improved resume and watch the delta, like a
  version-controlled changelog of your career.
- **A resume coach** — a separate, tailored pass that says, in plain language,
  what's strong, what's weak, and the highest-impact fixes ("biggest score left
  on the table").

---

## Screens

### Score → Results
Drop a PDF; the pipeline runs in-browser and produces an editorial scorecard —
a verdict, the total out of 120 with a delta versus your previous run, four
fairness-constrained category scores with evidence, and the coach's prioritized
fixes. A "revision rail" on the left tracks every past run.

![Results screen](docs/screenshots/02-results.png)

### History & Trends
Your score over time, per-category sparklines, a summary strip (latest /
personal best / net change / runs), and a changelog of every run with inline
rename, View, Diff, and Delete.

![History and trends screen](docs/screenshots/03-history.png)

### Score & Diff
Upload by drag-and-drop, and compare any two runs category-by-category.

| Score | Diff |
|---|---|
| ![Score screen](docs/screenshots/01-score.png) | ![Diff screen](docs/screenshots/04-diff.png) |

### Settings & dark mode
Bring-your-own keys (kept in-session by default; opt in to remember them),
optional GitHub enrichment, theme, and one-click "Clear all data." The whole app
supports light and dark.

| Settings | Results (dark) |
|---|---|
| ![Settings screen](docs/screenshots/05-settings.png) | ![Results dark](docs/screenshots/06-results-dark.png) |

---

## What this fork changes

Everything new lives under **`web/`** — **no existing Python files are modified**,
so the CLI behaves exactly as before.

- **New:** a Next.js 15 (App Router) **static-export** app under `web/`.
- **Ported to TypeScript** from the Python source: the JSON-Resume normalization
  (`transform.py` → `normalize.ts`), the scoring caps/bands (`scoring.ts`), the
  run-to-run diff math, the fairness-constrained rubric and prompts, the Gemini
  client (with backoff), and the GitHub enrichment.
- **New capabilities:** browser storage of runs (IndexedDB), trend charts &
  per-category sparklines, run-to-run diffing, and the resume coach.
- **Design system:** plain CSS custom properties; Instrument Serif / Archivo /
  JetBrains Mono; light + dark themes; keyboard-focus and reduced-motion support.
- **Tested:** Vitest unit tests for all deterministic logic and clients; a
  Playwright smoke test that drives upload → (stubbed Gemini) → results.

---

## Privacy guarantees

1. Everything runs in your browser — there is no backend of ours for your resume
   to pass through. Vercel serves static assets only.
2. Scoring goes **straight from your browser to Google Gemini** with your own
   key. We never see the key or the resume.
3. Scores and past resumes are saved in this browser's local cache, not a
   database. **Settings → Clear all data** erases everything instantly.
4. No tracking, no sign-in; works offline once loaded.

---

## Install

```bash
cd web
npm install            # deps only — the pdfjs worker is copied on predev/prebuild/pree2e
```

## Keys are entered at runtime, not via env vars

There are **no** `GEMINI_API_KEY` / `GITHUB_TOKEN` build-time env vars. Open
**Settings** in the running app and paste your keys there:

- **Gemini API key** (required) — used for resume extraction, scoring, and coaching.
- **GitHub token** (optional) — raises the GitHub API rate limit when GitHub
  enrichment is enabled.

By default keys live only in memory for the session. Tick **Remember keys** to
persist them to this browser's `localStorage`. "Clear all data" wipes keys,
settings, and run history (theme preference is preserved).

## Develop

```bash
cd web
npm run dev            # http://localhost:3000
```

## Build (static export)

```bash
cd web
npm run build          # produces ./out (output: "export")
```

The pdfjs web worker is copied to `public/pdf.worker.min.mjs` automatically by
`scripts/copy-pdf-worker.mjs` (run on `predev` / `prebuild`). If you ever see a
"worker" error, run `npm run copy:pdf-worker` and rebuild.

## Test

```bash
cd web
npm run test                                   # Vitest unit tests
npx playwright install --with-deps chromium    # one-time
npm run e2e                                     # Playwright smoke (stubbed Gemini)
```

## Deploy to Vercel

A production build is **live at https://web-eight-black-28.vercel.app**.

This app is the `web/` subdirectory of the repo. The settings are pinned in
[`web/vercel.json`](vercel.json):

1. **Root Directory** = `web`
2. **Framework Preset** = Other (`"framework": null`) — it's a Next.js **static
   export**, served as plain static assets, not a Next.js server.
3. Build command `npm run build`, Output directory `out`, with `cleanUrls` on so
   `/results`, `/history`, etc. resolve to their exported `.html` files.

No environment variables are required — keys are entered at runtime in the UI.

## A note on scores

Scores are **indicative**. This browser app is a TypeScript port of the Python
CLI tool; prompt rendering, GitHub enrichment, and model behavior can differ, so
a score here may not exactly match the Python pipeline's output. Use it for
relative guidance and trend tracking, not as an absolute hiring signal.
