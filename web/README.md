# Hiring Agent — Web

A privacy-first, in-browser resume scorer. PDFs are parsed client-side and
scored via Google Gemini using a key **you** supply at runtime. Nothing is sent
to any server we control: your API key, the resume, and all run history stay in
your browser (localStorage + IndexedDB).

## Install

```bash
cd web
npm install            # also copies the pdfjs worker into public/ via postinstall hooks
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

This app is the `web/` subdirectory of the repo. In the Vercel project:

1. **Root Directory** = `web`
2. **Framework Preset** = Next.js (also pinned in `web/vercel.json`)
3. Build command `npm run build`, Output directory `out` (static export).

No environment variables are required — keys are entered at runtime in the UI.

## A note on scores

Scores are **indicative**. This browser app is a TypeScript port of the Python
CLI tool; prompt rendering, GitHub enrichment, and model behavior can differ, so
a score here may not exactly match the Python pipeline's output. Use it for
relative guidance and trend tracking, not as an absolute hiring signal.
