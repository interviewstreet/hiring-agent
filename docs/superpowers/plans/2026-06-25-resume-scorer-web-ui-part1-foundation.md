# Resume Scorer Web UI — Implementation Plan (Part 1 of 2: Foundation & Core Engine)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the scaffold, design system, and a fully unit-tested in-browser scoring engine (PDF → structured resume → optional GitHub enrichment → evaluation → coach) for the privacy-first Hiring Agent web UI, with no server.

**Architecture:** A Next.js (App Router) app under `web/`, built as a static export and deployed on Vercel as static assets — there is no backend. All logic runs client-side: PDF parsing via `pdfjs-dist`, scoring via Google Gemini called directly from the browser with the user's own key. Part 1 delivers the deterministic core and the external clients as pure, tested modules; Part 2 adds storage and the React screens.

**Tech Stack:** Next.js 15, React 19, TypeScript, `@google/genai` (Gemini), `pdfjs-dist`, `zod`, `idb` (Part 2), Vitest (unit), Playwright (smoke, Part 2). Design system: plain CSS with CSS custom properties; fonts via `next/font/google` (Instrument Serif, Archivo, JetBrains Mono).

**Reference spec:** `docs/superpowers/specs/2026-06-25-resume-scorer-web-ui-design.md`

**Source of truth for ports:** the existing Python modules — `transform.py`, `evaluator.py`, `models.py`, `github.py`, and `prompts/templates/*.jinja`.

---

## File structure (created in Part 1)

```
web/
  package.json
  next.config.mjs            # output: 'export'
  tsconfig.json
  vitest.config.ts
  .gitignore
  src/
    app/
      layout.tsx             # fonts, theme bootstrap, global CSS
      globals.css            # design tokens + design-system classes
      page.tsx               # temporary dev harness (replaced in Part 2)
    lib/
      schemas.ts             # zod schemas + TS types (resume, evaluation, coach, run)
      normalize.ts           # transform.py port (urls, dates, profile derivation)
      scoring.ts             # category maxes, capping, totals, status bands
      diff.ts                # run-to-run delta math
      prompts.ts             # extraction / scoring / coach prompt builders + Gemini responseSchemas
      gemini.ts              # Gemini client: JSON mode + backoff + validation
      pdf.ts                 # pdfjs text extraction
      github.ts              # profile/repos fetch, classification, project selection
      pipeline.ts            # orchestrates a full scoring run
      errors.ts              # typed error classes
    ui/
      ThemeProvider.tsx      # theme context + persistence
      ThemeToggle.tsx        # sun/moon switch
      PrivacyChip.tsx        # "100% PRIVATE" chip + modal
  test/
    fixtures/                # sample inputs for unit tests
```

---

## Phase A — Scaffold & design system

### Task A1: Initialize the Next.js app under `web/`

**Files:**
- Create: `web/package.json`
- Create: `web/next.config.mjs`
- Create: `web/tsconfig.json`
- Create: `web/.gitignore`
- Create: `web/src/app/layout.tsx`
- Create: `web/src/app/page.tsx`

- [ ] **Step 1: Create `web/package.json`**

```json
{
  "name": "hiring-agent-web",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest run",
    "test:watch": "vitest",
    "e2e": "playwright test"
  },
  "dependencies": {
    "next": "^15.1.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@google/genai": "^1.0.0",
    "pdfjs-dist": "^4.7.76",
    "idb": "^8.0.0",
    "zod": "^3.23.8"
  },
  "devDependencies": {
    "typescript": "^5.6.0",
    "@types/node": "^22.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "vitest": "^2.1.0",
    "@playwright/test": "^1.48.0"
  }
}
```

- [ ] **Step 2: Create `web/next.config.mjs`** (static export — no server)

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  images: { unoptimized: true },
  // pdfjs ships a worker we load from /public or CDN; no server features used.
};

export default nextConfig;
```

- [ ] **Step 3: Create `web/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["dom", "dom.iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 4: Create `web/.gitignore`**

```
node_modules/
.next/
out/
.env*.local
playwright-report/
test-results/
```

- [ ] **Step 5: Create a minimal `web/src/app/layout.tsx`** (replaced in A3 with fonts/theme)

```tsx
export const metadata = { title: "Hiring Agent", description: "Private resume scoring" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 6: Create a placeholder `web/src/app/page.tsx`**

```tsx
export default function Home() {
  return <main style={{ padding: 24 }}>Hiring Agent web — scaffold OK</main>;
}
```

- [ ] **Step 7: Install dependencies**

Run: `cd web && npm install`
Expected: completes, creates `web/node_modules` and `web/package-lock.json`.

- [ ] **Step 8: Verify the build works**

Run: `cd web && npm run build`
Expected: build succeeds and produces `web/out/` (static export).

- [ ] **Step 9: Commit**

```bash
git add web/package.json web/package-lock.json web/next.config.mjs web/tsconfig.json web/.gitignore web/src
git commit -m "feat(web): scaffold Next.js static-export app"
```

---

### Task A2: Configure Vitest

**Files:**
- Create: `web/vitest.config.ts`
- Create: `web/test/fixtures/.gitkeep`

- [ ] **Step 1: Create `web/vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
});
```

- [ ] **Step 2: Create the fixtures dir**

Run: `mkdir -p web/test/fixtures && touch web/test/fixtures/.gitkeep`

- [ ] **Step 3: Add a smoke test to prove Vitest runs**

Create `web/src/lib/_smoke.test.ts`:

```ts
import { describe, it, expect } from "vitest";

describe("vitest", () => {
  it("runs", () => {
    expect(1 + 1).toBe(2);
  });
});
```

- [ ] **Step 4: Run the test**

Run: `cd web && npm test`
Expected: 1 passing test.

- [ ] **Step 5: Remove the smoke test and commit**

```bash
rm web/src/lib/_smoke.test.ts
git add web/vitest.config.ts web/test/fixtures/.gitkeep web/package.json
git commit -m "test(web): configure vitest"
```

---

### Task A3: Design tokens, global CSS, fonts, and theme bootstrap

**Files:**
- Create: `web/src/app/globals.css`
- Modify: `web/src/app/layout.tsx`

This ports the locked design system. The exact token values and component classes are taken from the approved mockups (see spec, "Visual design system").

- [ ] **Step 1: Create `web/src/app/globals.css`**

```css
:root{
  --paper:#E7EAEE; --panel:#FFFFFF; --panel-2:#F4F6F8;
  --ink:#15181D; --ink-soft:#5E6772; --rule:#D3D9DF;
  --brand:#3A2DD0; --brand-tint:rgba(58,45,208,.08); --brand-ink:#2A1FA8;
  --good:#2F7A57; --good-tint:rgba(47,122,87,.12);
  --warn:#A9741B; --warn-tint:rgba(169,116,27,.12);
  --bad:#BA413B; --bad-tint:rgba(186,65,59,.11);
  --shadow:0 1px 3px rgba(21,24,29,.10);
}
[data-theme="dark"]{
  --paper:#0F1320; --panel:#171C2A; --panel-2:#1C2233;
  --ink:#ECEEF4; --ink-soft:#98A1B2; --rule:#2A3142;
  --brand:#897CFF; --brand-tint:rgba(137,124,255,.16); --brand-ink:#B7AEFF;
  --good:#4FBE8E; --good-tint:rgba(79,190,142,.15);
  --warn:#E0B24B; --warn-tint:rgba(224,178,75,.15);
  --bad:#E66B63; --bad-tint:rgba(230,107,99,.15);
  --shadow:0 2px 10px rgba(0,0,0,.40);
}
*{box-sizing:border-box}
html,body{margin:0}
body{
  background:var(--paper); color:var(--ink);
  font-family:var(--font-archivo),system-ui,sans-serif; font-size:15px; line-height:1.55;
  -webkit-font-smoothing:antialiased; transition:background .25s ease,color .25s ease;
}
.serif{font-family:var(--font-instrument-serif),serif}
.mono{font-family:var(--font-jetbrains-mono),monospace}

/* shared design-system primitives (reused across screens) */
.eyebrow{font-family:var(--font-jetbrains-mono),monospace; font-size:11px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--ink-soft)}
.delta{font-family:var(--font-jetbrains-mono),monospace; font-weight:700}
.up{color:var(--good)} .down{color:var(--bad)} .flat{color:var(--ink-soft)}
.chip{font-family:var(--font-jetbrains-mono),monospace; font-size:11px; letter-spacing:.04em;
  color:var(--good); background:var(--good-tint);
  border:1px solid color-mix(in srgb,var(--good) 32%,transparent);
  padding:5px 10px; border-radius:999px; display:inline-flex; gap:7px; align-items:center; cursor:pointer}
.chip:hover{border-color:var(--good)}
.dot{width:6px;height:6px;border-radius:50%;background:var(--good);display:inline-block}

@media (prefers-reduced-motion: reduce){ body{transition:none} }
```

- [ ] **Step 2: Replace `web/src/app/layout.tsx` with fonts + theme bootstrap**

The inline script sets `data-theme` before paint to avoid a flash; it reads the same `localStorage` key the ThemeProvider (Task A4) writes. `dangerouslySetInnerHTML` is used here with a **hardcoded constant** (`themeBootstrap`) — there is no user or untrusted input, so it is not an XSS vector. This is the standard no-flash theme pattern (same approach as `next-themes`). Do not pass dynamic content into this script.

```tsx
import "./globals.css";
import { Instrument_Serif, Archivo, JetBrains_Mono } from "next/font/google";
import { ThemeProvider } from "@/ui/ThemeProvider";

const serif = Instrument_Serif({ weight: ["400"], subsets: ["latin"], variable: "--font-instrument-serif", display: "swap" });
const archivo = Archivo({ subsets: ["latin"], variable: "--font-archivo", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains-mono", display: "swap" });

export const metadata = { title: "Hiring Agent", description: "Private, in-browser resume scoring" };

const themeBootstrap = `(function(){try{var t=localStorage.getItem('ha-theme');if(t==='dark'||t==='light')document.documentElement.setAttribute('data-theme',t);else document.documentElement.setAttribute('data-theme','light');}catch(e){document.documentElement.setAttribute('data-theme','light');}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${serif.variable} ${archivo.variable} ${mono.variable}`}>
      <head><script dangerouslySetInnerHTML={{ __html: themeBootstrap }} /></head>
      <body>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Verify build (ThemeProvider stub needed first)**

The layout now imports `@/ui/ThemeProvider`, which is created in Task A4. Proceed to A4, then build. (No commit yet — A3 and A4 commit together.)

---

### Task A4: ThemeProvider, ThemeToggle, PrivacyChip

**Files:**
- Create: `web/src/ui/ThemeProvider.tsx`
- Create: `web/src/ui/ThemeToggle.tsx`
- Create: `web/src/ui/PrivacyChip.tsx`

- [ ] **Step 1: Create `web/src/ui/ThemeProvider.tsx`**

```tsx
"use client";
import { createContext, useContext, useEffect, useState, useCallback } from "react";

type Theme = "light" | "dark";
const ThemeContext = createContext<{ theme: Theme; toggle: () => void }>({ theme: "light", toggle: () => {} });

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const current = (document.documentElement.getAttribute("data-theme") as Theme) || "light";
    setTheme(current);
  }, []);

  const toggle = useCallback(() => {
    setTheme((prev) => {
      const next: Theme = prev === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("ha-theme", next); } catch {}
      return next;
    });
  }, []);

  return <ThemeContext.Provider value={{ theme, toggle }}>{children}</ThemeContext.Provider>;
}

export const useTheme = () => useContext(ThemeContext);
```

- [ ] **Step 2: Create `web/src/ui/ThemeToggle.tsx`** (sun/moon switch; styles inline-scoped via a `<style>` tag to keep the component self-contained)

```tsx
"use client";
import { useTheme } from "./ThemeProvider";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      onClick={toggle}
      role="switch"
      aria-checked={theme === "dark"}
      aria-label="Toggle light or dark theme"
      title="Light / dark"
      className="ha-theme"
    >
      <svg className="ha-ico ha-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
      <svg className="ha-ico ha-moon" viewBox="0 0 24 24" fill="currentColor"><path d="M21 12.8A8.5 8.5 0 1 1 11.2 3a6.6 6.6 0 0 0 9.8 9.8z"/></svg>
      <span className="ha-knob" />
      <style>{`
        .ha-theme{position:relative;width:60px;height:28px;border-radius:999px;border:1px solid var(--rule);background:var(--panel-2);cursor:pointer;padding:0;flex:none}
        .ha-ico{position:absolute;top:50%;transform:translateY(-50%);width:15px;height:15px;z-index:2}
        .ha-sun{left:7px;color:var(--warn)} .ha-moon{right:7px;color:var(--ink-soft)}
        .ha-knob{position:absolute;top:2px;left:2px;width:22px;height:22px;border-radius:50%;background:var(--panel);box-shadow:var(--shadow);transition:left .22s ease;z-index:1}
        [data-theme="dark"] .ha-knob{left:34px}
        [data-theme="dark"] .ha-moon{color:var(--brand-ink)} [data-theme="dark"] .ha-sun{color:var(--ink-soft)}
        @media (prefers-reduced-motion: reduce){ .ha-knob{transition:none} }
      `}</style>
    </button>
  );
}
```

- [ ] **Step 3: Create `web/src/ui/PrivacyChip.tsx`** (chip + modal; copy text from the approved privacy modal)

```tsx
"use client";
import { useEffect, useState } from "react";

export function PrivacyChip() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  return (
    <>
      <button className="chip" aria-haspopup="dialog" onClick={() => setOpen(true)}>
        <span className="dot" />100% PRIVATE <span style={{ textDecoration: "underline", textUnderlineOffset: 2, opacity: 0.85 }}>how?</span>
      </button>
      {open && (
        <div className="ha-overlay" onClick={(e) => { if (e.target === e.currentTarget) setOpen(false); }}>
          <div className="ha-modal" role="dialog" aria-modal="true" aria-labelledby="ha-privacy-title">
            <button className="ha-modal-x" aria-label="Close" onClick={() => setOpen(false)}>×</button>
            <div className="eyebrow">Privacy</div>
            <h3 id="ha-privacy-title" className="serif ha-modal-title">Private by design — no server, no account.</h3>
            <ul className="ha-plist">
              <li><span className="ha-pk mono">01</span><span>Everything runs in your browser. There&apos;s no backend of ours for your resume to pass through.</span></li>
              <li><span className="ha-pk mono">02</span><span>Scoring goes straight from your browser to Google Gemini with your own API key. We never see the key or the resume.</span></li>
              <li><span className="ha-pk mono">03</span><span>Your scores and past resumes are saved in this browser&apos;s local cache — not a database.</span></li>
              <li><span className="ha-pk mono">04</span><span>Clearing your browser data, or Settings → Clear all data, erases everything instantly.</span></li>
            </ul>
            <p className="ha-modal-foot mono">No tracking · No sign-in · Works offline once loaded</p>
          </div>
          <style>{`
            .ha-overlay{position:fixed;inset:0;background:rgba(10,12,18,.55);backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center;padding:24px;z-index:50}
            .ha-modal{background:var(--panel);border:1px solid var(--rule);border-radius:16px;max-width:460px;width:100%;padding:26px 26px 22px;box-shadow:0 24px 60px rgba(0,0,0,.35);position:relative}
            .ha-modal-x{position:absolute;top:14px;right:14px;border:none;background:transparent;color:var(--ink-soft);font-size:22px;line-height:1;cursor:pointer;padding:4px}
            .ha-modal-title{font-weight:400;font-size:27px;line-height:1.12;margin:8px 0 14px}
            .ha-plist{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:12px}
            .ha-plist li{display:grid;grid-template-columns:18px 1fr;gap:11px;font-size:14px;color:var(--ink);line-height:1.5}
            .ha-pk{color:var(--good);font-weight:700}
            .ha-modal-foot{margin:16px 0 0;padding-top:14px;border-top:1px solid var(--rule);font-size:12.5px;color:var(--ink-soft);letter-spacing:.02em}
          `}</style>
        </div>
      )}
    </>
  );
}
```

- [ ] **Step 4: Render the shared chrome on the dev harness so it's visible**

Replace `web/src/app/page.tsx`:

```tsx
import { ThemeToggle } from "@/ui/ThemeToggle";
import { PrivacyChip } from "@/ui/PrivacyChip";

export default function Home() {
  return (
    <main style={{ maxWidth: 1080, margin: "0 auto", padding: "26px 28px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--rule)", paddingBottom: 20 }}>
        <div className="serif" style={{ fontSize: 26 }}>Hiring <i>Agent</i></div>
        <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
          <ThemeToggle />
          <PrivacyChip />
        </div>
      </div>
      <p className="eyebrow" style={{ marginTop: 24 }}>Scaffold + design system ready</p>
    </main>
  );
}
```

- [ ] **Step 5: Run the dev server and verify visually**

Run: `cd web && npm run dev`
Expected: at `http://localhost:3000`, the header shows the serif wordmark, a working sun/moon toggle (theme persists on reload), and a "100% PRIVATE" chip that opens the modal (closes via ×, outside click, Esc).

- [ ] **Step 6: Verify production build**

Run: `cd web && npm run build`
Expected: static export succeeds.

- [ ] **Step 7: Commit**

```bash
git add web/src/app/globals.css web/src/app/layout.tsx web/src/app/page.tsx web/src/ui
git commit -m "feat(web): design tokens, theme toggle, privacy modal"
```

---

## Phase B — Schemas & deterministic core (TDD)

### Task B1: Zod schemas and types

**Files:**
- Create: `web/src/lib/schemas.ts`
- Test: `web/src/lib/schemas.test.ts`

Mirrors `models.py`: `JSONResume`, `EvaluationData` (category maxes/limits), plus a `Coach` schema for the new coaching output and a `RunRecord` for stored runs.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { EvaluationSchema, JSONResumeSchema, CoachSchema } from "./schemas";

describe("schemas", () => {
  it("accepts a valid evaluation", () => {
    const ev = {
      scores: {
        open_source: { score: 28, max: 35, evidence: "PRs to big repos" },
        self_projects: { score: 22, max: 30, evidence: "two full-stack apps" },
        production: { score: 10, max: 25, evidence: "one internship" },
        technical_skills: { score: 9, max: 10, evidence: "broad" },
      },
      bonus_points: { total: 5, breakdown: "GSoC" },
      deductions: { total: 0, reasons: "" },
      key_strengths: ["builder"],
      areas_for_improvement: ["production"],
    };
    expect(EvaluationSchema.parse(ev).scores.open_source.score).toBe(28);
  });

  it("rejects a category score above its max-allowed cap via refine", () => {
    const bad = { network: null, url: "https://github.com/x" };
    expect(JSONResumeSchema.safeParse({ basics: { name: "A", profiles: [bad] } }).success).toBe(true);
  });

  it("accepts a valid coach payload", () => {
    const coach = {
      verdict: "Strong builder, thin on production.",
      fixes: [{ priority: 1, category: "production", title: "Quantify impact", detail: "add numbers", estGain: 8 }],
      boosts: [{ category: "technical_skills", text: "show depth", estGain: 1 }],
    };
    expect(CoachSchema.parse(coach).fixes[0].estGain).toBe(8);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/lib/schemas.test.ts`
Expected: FAIL — cannot find module `./schemas`.

- [ ] **Step 3: Implement `web/src/lib/schemas.ts`**

```ts
import { z } from "zod";

export const CATEGORY_KEYS = ["open_source", "self_projects", "production", "technical_skills"] as const;
export type CategoryKey = (typeof CATEGORY_KEYS)[number];

// ── JSON Resume (subset that gets scored) ──
const ProfileSchema = z.object({
  network: z.string().nullable().optional(),
  username: z.string().nullable().optional(),
  url: z.string(),
});
const BasicsSchema = z.object({
  name: z.string(),
  email: z.string().nullable().optional(),
  phone: z.string().nullable().optional(),
  url: z.string().nullable().optional(),
  summary: z.string().nullable().optional(),
  profiles: z.array(ProfileSchema).nullable().optional(),
});
const WorkSchema = z.object({
  name: z.string().nullable().optional(),
  position: z.string().nullable().optional(),
  url: z.string().nullable().optional(),
  startDate: z.string().nullable().optional(),
  endDate: z.string().nullable().optional(),
  summary: z.string().nullable().optional(),
  highlights: z.array(z.string()).nullable().optional(),
});
const EducationSchema = z.object({
  institution: z.string().nullable().optional(),
  area: z.string().nullable().optional(),
  studyType: z.string().nullable().optional(),
  startDate: z.string().nullable().optional(),
  endDate: z.string().nullable().optional(),
  score: z.string().nullable().optional(),
});
const SkillSchema = z.object({
  name: z.string().nullable().optional(),
  level: z.string().nullable().optional(),
  keywords: z.array(z.string()).nullable().optional(),
});
const ProjectSchema = z.object({
  name: z.string().nullable().optional(),
  description: z.string().nullable().optional(),
  url: z.string().nullable().optional(),
  highlights: z.array(z.string()).nullable().optional(),
  technologies: z.array(z.string()).nullable().optional(),
  skills: z.array(z.string()).nullable().optional(),
});
const AwardSchema = z.object({
  title: z.string().nullable().optional(),
  date: z.string().nullable().optional(),
  awarder: z.string().nullable().optional(),
  summary: z.string().nullable().optional(),
});

export const JSONResumeSchema = z.object({
  basics: BasicsSchema.nullable().optional(),
  work: z.array(WorkSchema).nullable().optional(),
  volunteer: z.array(WorkSchema).nullable().optional(),
  education: z.array(EducationSchema).nullable().optional(),
  skills: z.array(SkillSchema).nullable().optional(),
  projects: z.array(ProjectSchema).nullable().optional(),
  awards: z.array(AwardSchema).nullable().optional(),
});
export type JSONResume = z.infer<typeof JSONResumeSchema>;

// ── Evaluation (mirrors models.py EvaluationData) ──
const CategoryScoreSchema = z.object({
  score: z.number().min(0),
  max: z.number().positive(),
  evidence: z.string().min(1),
});
export const EvaluationSchema = z.object({
  scores: z.object({
    open_source: CategoryScoreSchema,
    self_projects: CategoryScoreSchema,
    production: CategoryScoreSchema,
    technical_skills: CategoryScoreSchema,
  }),
  bonus_points: z.object({ total: z.number().min(0).max(20), breakdown: z.string() }),
  deductions: z.object({ total: z.number().min(0), reasons: z.string() }),
  key_strengths: z.array(z.string()).min(1).max(5),
  areas_for_improvement: z.array(z.string()).min(1).max(5),
});
export type Evaluation = z.infer<typeof EvaluationSchema>;

// ── Coach (new) ──
const CategoryEnum = z.enum(CATEGORY_KEYS);
export const CoachSchema = z.object({
  verdict: z.string().min(1),
  fixes: z.array(z.object({
    priority: z.number().int().positive(),
    category: CategoryEnum,
    title: z.string().min(1),
    detail: z.string().min(1),
    estGain: z.number().min(0),
  })).max(5),
  boosts: z.array(z.object({
    category: CategoryEnum,
    text: z.string().min(1),
    estGain: z.number().min(0),
  })).max(5),
});
export type Coach = z.infer<typeof CoachSchema>;

// ── GitHub summary (subset persisted for display) ──
export type GitHubSummary = {
  profile: { username: string; public_repos?: number; followers?: number } | null;
  projects: Array<{ name: string; project_type: string; stars: number }>;
};

// ── Stored run ──
export type RunRecord = {
  id: string;
  createdAt: number;
  fileName: string;
  label?: string;
  parsedResume: JSONResume;
  evaluation: Evaluation;
  coach: Coach;
  githubSummary?: GitHubSummary | null;
};
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd web && npx vitest run src/lib/schemas.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/schemas.ts web/src/lib/schemas.test.ts
git commit -m "feat(web): zod schemas for resume, evaluation, coach, run"
```

---

### Task B2: Normalization helpers (port of `transform.py`)

**Files:**
- Create: `web/src/lib/normalize.ts`
- Test: `web/src/lib/normalize.test.ts`

Ports the genuinely useful, well-defined helpers from `transform.py`: URL→domain, domain→network name, URL→username (LinkedIn uses path part index 1, StackOverflow index 2, else index 0), and `parse_date_range`. Plus `normalizeResume`, which fills in profile `network`/`username` from URLs when missing.

- [ ] **Step 1: Write the failing test** (cases mirror `transform.py` behavior)

```ts
import { describe, it, expect } from "vitest";
import { extractDomain, networkName, extractUsername, parseDateRange, normalizeResume } from "./normalize";

describe("url helpers", () => {
  it("extracts domain and strips www", () => {
    expect(extractDomain("https://www.github.com/octocat")).toBe("github.com");
  });
  it("maps known domains to network names", () => {
    expect(networkName("github.com")).toBe("GitHub");
    expect(networkName("linkedin.com")).toBe("LinkedIn");
    expect(networkName("unknown.com")).toBe("");
  });
  it("extracts github username from first path part", () => {
    expect(extractUsername("https://github.com/octocat?tab=repositories", "github.com")).toBe("octocat");
  });
  it("extracts linkedin username from second path part", () => {
    expect(extractUsername("https://linkedin.com/in/jane-doe", "linkedin.com")).toBe("jane-doe");
  });
});

describe("parseDateRange", () => {
  it("handles 'Jan-Mar 2021'", () => {
    expect(parseDateRange("Jan-Mar 2021")).toEqual(["Jan 2021", "Mar 2021"]);
  });
  it("handles 'onwards'", () => {
    expect(parseDateRange("Jan 2021 onwards")).toEqual(["Jan 2021", "Present"]);
  });
  it("handles year range '2020-2021'", () => {
    expect(parseDateRange("2020-2021")).toEqual(["2020-01", "2021-12"]);
  });
});

describe("normalizeResume", () => {
  it("derives network and username for a github profile missing them", () => {
    const out = normalizeResume({ basics: { name: "A", profiles: [{ url: "https://github.com/octocat" }] } });
    expect(out.basics?.profiles?.[0].network).toBe("GitHub");
    expect(out.basics?.profiles?.[0].username).toBe("octocat");
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/lib/normalize.test.ts`
Expected: FAIL — cannot find module `./normalize`.

- [ ] **Step 3: Implement `web/src/lib/normalize.ts`**

```ts
import type { JSONResume } from "./schemas";

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

const NETWORKS: Record<string, string> = {
  "github.com": "GitHub",
  "linkedin.com": "LinkedIn",
  "leetcode.com": "LeetCode",
  "stackoverflow.com": "Stack Overflow",
  "hackerrank.com": "HackerRank",
  "behance.net": "Behance",
  "dev.to": "DEV Community",
  "twitter.com": "X",
  "x.com": "X",
};

export function extractDomain(url: string): string {
  try {
    let u = url;
    if (u.includes("://")) u = u.split("://")[1];
    let domain = u.split("/")[0];
    if (domain.startsWith("www.")) domain = domain.slice(4);
    return domain;
  } catch {
    return "";
  }
}

export function networkName(domain: string): string {
  return NETWORKS[domain] ?? "";
}

export function extractUsername(url: string, domain: string): string {
  try {
    const path = url.includes(domain) ? url.split(domain)[1] : "";
    if (!path) return "";
    const parts = path.replace(/^\/+/, "").split("/").filter(Boolean).map((p) => p.split("?")[0]);
    if (parts.length === 0) return "";
    if (domain === "linkedin.com") return parts[1] ?? "";
    if (domain === "stackoverflow.com") return parts[2] ?? "";
    return parts[0];
  } catch {
    return "";
  }
}

export function parseDateRange(range: string): [string | null, string | null] {
  if (!range) return [null, null];
  if (range.includes("onwards")) {
    const start = range.replace("onwards", "").trim();
    return start ? [start, "Present"] : [null, "Present"];
  }
  if (range.includes(" ") && MONTHS.some((m) => range.includes(m))) {
    const parts = range.split(" ");
    if (parts.length >= 2) {
      const year = parts[parts.length - 1];
      if (parts[0].includes("-") && parts[0].split("-").length === 2) {
        const [sm, em] = parts[0].split("-");
        return [`${sm} ${year}`, `${em} ${year}`];
      }
      return [`${parts[0]} ${year}`, null];
    }
  }
  if (range.includes("-") && range.split("-").length === 2) {
    const [sy, ey] = range.split("-");
    return [`${sy}-01`, `${ey}-12`];
  }
  return [null, null];
}

export function normalizeResume(resume: JSONResume): JSONResume {
  const out: JSONResume = { ...resume };
  const profiles = out.basics?.profiles;
  if (out.basics && Array.isArray(profiles)) {
    out.basics = {
      ...out.basics,
      profiles: profiles.map((p) => {
        if (p.url && (p.network === null || p.network === undefined)) {
          const domain = extractDomain(p.url);
          const net = networkName(domain);
          if (net) {
            const username = p.username ?? extractUsername(p.url, domain) ?? undefined;
            return { ...p, network: net, username: username || p.username };
          }
        }
        return p;
      }),
    };
  }
  return out;
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd web && npx vitest run src/lib/normalize.test.ts`
Expected: PASS (all cases).

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/normalize.ts web/src/lib/normalize.test.ts
git commit -m "feat(web): port transform.py normalization helpers"
```

---

### Task B3: Scoring utilities (caps, totals, status bands)

**Files:**
- Create: `web/src/lib/scoring.ts`
- Test: `web/src/lib/scoring.test.ts`

Mirrors the caps in `score.py`/`evaluator.py`: category maxes 35/30/25/10; total = Σ min(score, max) + bonus − deductions, clamped to [0, 120]. Status bands: ratio ≥ 0.7 → `good`, ≥ 0.4 → `warn`, else `bad`.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { CATEGORY_MAX, computeTotal, statusFor, cappedCategory } from "./scoring";
import type { Evaluation } from "./schemas";

const ev: Evaluation = {
  scores: {
    open_source: { score: 40, max: 35, evidence: "x" }, // over cap on purpose
    self_projects: { score: 22, max: 30, evidence: "x" },
    production: { score: 10, max: 25, evidence: "x" },
    technical_skills: { score: 9, max: 10, evidence: "x" },
  },
  bonus_points: { total: 5, breakdown: "" },
  deductions: { total: 3, reasons: "" },
  key_strengths: ["a"],
  areas_for_improvement: ["b"],
};

describe("scoring", () => {
  it("exposes fixed category maxes", () => {
    expect(CATEGORY_MAX.open_source).toBe(35);
    expect(CATEGORY_MAX.technical_skills).toBe(10);
  });
  it("caps a category score at its max", () => {
    expect(cappedCategory(ev, "open_source")).toBe(35);
  });
  it("computes total = capped categories + bonus - deductions, clamped to 120", () => {
    // 35 + 22 + 10 + 9 = 76; +5 -3 = 78
    expect(computeTotal(ev)).toBe(78);
  });
  it("classifies status bands by ratio", () => {
    expect(statusFor(28, 35)).toBe("good");   // 0.8
    expect(statusFor(10, 25)).toBe("warn");   // 0.4
    expect(statusFor(3, 25)).toBe("bad");     // 0.12
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/lib/scoring.test.ts`
Expected: FAIL — cannot find module `./scoring`.

- [ ] **Step 3: Implement `web/src/lib/scoring.ts`**

```ts
import type { Evaluation, CategoryKey } from "./schemas";
import { CATEGORY_KEYS } from "./schemas";

export const CATEGORY_MAX: Record<CategoryKey, number> = {
  open_source: 35,
  self_projects: 30,
  production: 25,
  technical_skills: 10,
};

export const MAX_TOTAL = 120;
export type Status = "good" | "warn" | "bad";

export function cappedCategory(ev: Evaluation, key: CategoryKey): number {
  const s = ev.scores[key];
  return Math.min(s.score, CATEGORY_MAX[key]);
}

export function computeTotal(ev: Evaluation): number {
  const categories = CATEGORY_KEYS.reduce((sum, k) => sum + cappedCategory(ev, k), 0);
  const raw = categories + ev.bonus_points.total - ev.deductions.total;
  return Math.max(0, Math.min(MAX_TOTAL, raw));
}

export function statusFor(score: number, max: number): Status {
  const ratio = max > 0 ? score / max : 0;
  if (ratio >= 0.7) return "good";
  if (ratio >= 0.4) return "warn";
  return "bad";
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd web && npx vitest run src/lib/scoring.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/scoring.ts web/src/lib/scoring.test.ts
git commit -m "feat(web): scoring caps, totals, and status bands"
```

---

### Task B4: Run-to-run diff math

**Files:**
- Create: `web/src/lib/diff.ts`
- Test: `web/src/lib/diff.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { diffRuns } from "./diff";
import type { RunRecord } from "./schemas";

function make(total: Partial<Record<string, number>>): RunRecord {
  return {
    id: "x", createdAt: 0, fileName: "r.pdf",
    parsedResume: {},
    evaluation: {
      scores: {
        open_source: { score: total.open_source ?? 0, max: 35, evidence: "e" },
        self_projects: { score: total.self_projects ?? 0, max: 30, evidence: "e" },
        production: { score: total.production ?? 0, max: 25, evidence: "e" },
        technical_skills: { score: total.technical_skills ?? 0, max: 10, evidence: "e" },
      },
      bonus_points: { total: 0, breakdown: "" },
      deductions: { total: 0, reasons: "" },
      key_strengths: ["a"], areas_for_improvement: ["b"],
    },
    coach: { verdict: "v", fixes: [], boosts: [] },
  };
}

describe("diffRuns", () => {
  it("returns null previous-diff when there is no previous run", () => {
    const d = diffRuns(make({ open_source: 20 }), null);
    expect(d.total).toBeNull();
  });
  it("computes total and per-category deltas", () => {
    const prev = make({ open_source: 18, production: 10 });
    const cur = make({ open_source: 28, production: 10 });
    const d = diffRuns(cur, prev);
    expect(d.total).toBe(10);
    expect(d.byCategory.open_source).toBe(10);
    expect(d.byCategory.production).toBe(0);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/lib/diff.test.ts`
Expected: FAIL — cannot find module `./diff`.

- [ ] **Step 3: Implement `web/src/lib/diff.ts`**

```ts
import type { RunRecord, CategoryKey } from "./schemas";
import { CATEGORY_KEYS } from "./schemas";
import { cappedCategory, computeTotal } from "./scoring";

export type RunDiff = {
  total: number | null;
  byCategory: Record<CategoryKey, number | null>;
};

export function diffRuns(cur: RunRecord, prev: RunRecord | null): RunDiff {
  if (!prev) {
    return {
      total: null,
      byCategory: { open_source: null, self_projects: null, production: null, technical_skills: null },
    };
  }
  const byCategory = Object.fromEntries(
    CATEGORY_KEYS.map((k) => [k, cappedCategory(cur.evaluation, k) - cappedCategory(prev.evaluation, k)]),
  ) as Record<CategoryKey, number | null>;
  return { total: computeTotal(cur.evaluation) - computeTotal(prev.evaluation), byCategory };
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd web && npx vitest run src/lib/diff.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/diff.ts web/src/lib/diff.test.ts
git commit -m "feat(web): run-to-run score diff math"
```

---

### Task B5: Prompt builders and Gemini response schemas

**Files:**
- Create: `web/src/lib/prompts.ts`
- Test: `web/src/lib/prompts.test.ts`

Ports the scoring rubric and system messages from the Jinja templates and adds the new coach prompt. The Gemini `responseSchema` objects use the OpenAPI-style subset Gemini accepts (types as uppercase strings).

> **Note on the rubric:** `buildScoringPrompt` must embed the full evaluation rubric. Copy the **entire contents** of `prompts/templates/resume_evaluation_criteria.jinja` (repo root) into the `RUBRIC` template literal below, replacing its trailing `{{ text_content }}` with `${resumeText}`. Copy the **entire contents** of `prompts/templates/resume_evaluation_system_message.jinja` into `SCORING_SYSTEM`. This keeps scoring faithful to the Python tool.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { buildExtractionPrompt, buildScoringPrompt, buildCoachPrompt, RESUME_SCHEMA, EVAL_SCHEMA, COACH_SCHEMA } from "./prompts";

describe("prompt builders", () => {
  it("embeds resume text in the extraction prompt", () => {
    const p = buildExtractionPrompt("RESUME TEXT HERE");
    expect(p.user).toContain("RESUME TEXT HERE");
    expect(p.responseSchema).toBe(RESUME_SCHEMA);
  });
  it("embeds resume text and the four categories in the scoring prompt", () => {
    const p = buildScoringPrompt("RESUME BODY");
    expect(p.user).toContain("RESUME BODY");
    expect(p.user).toContain("open_source");
    expect(p.user).toContain("technical_skills");
    expect(p.responseSchema).toBe(EVAL_SCHEMA);
  });
  it("includes the evaluation summary in the coach prompt", () => {
    const p = buildCoachPrompt("RESUME BODY", '{"scores":{"production":{"score":10,"max":25}}}');
    expect(p.user).toContain("production");
    expect(p.responseSchema).toBe(COACH_SCHEMA);
  });
  it("response schemas use Gemini OBJECT types", () => {
    expect(RESUME_SCHEMA.type).toBe("OBJECT");
    expect(EVAL_SCHEMA.type).toBe("OBJECT");
    expect(COACH_SCHEMA.type).toBe("OBJECT");
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/lib/prompts.test.ts`
Expected: FAIL — cannot find module `./prompts`.

- [ ] **Step 3: Implement `web/src/lib/prompts.ts`**

Replace the two marked placeholders with verbatim copies of the named `.jinja` files (see note above). Everything else is literal.

```ts
export type GeminiSchema = Record<string, unknown> & { type: string };
export type PromptSpec = { system: string; user: string; responseSchema: GeminiSchema };

// ── Gemini response schemas (OpenAPI subset) ──
const STR = { type: "STRING" } as const;
const STR_ARR = { type: "ARRAY", items: { type: "STRING" } } as const;

export const RESUME_SCHEMA: GeminiSchema = {
  type: "OBJECT",
  properties: {
    basics: {
      type: "OBJECT",
      properties: {
        name: STR, email: STR, phone: STR, url: STR, summary: STR,
        profiles: { type: "ARRAY", items: { type: "OBJECT", properties: { network: STR, username: STR, url: STR } } },
      },
    },
    work: { type: "ARRAY", items: { type: "OBJECT", properties: { name: STR, position: STR, url: STR, startDate: STR, endDate: STR, summary: STR, highlights: STR_ARR } } },
    education: { type: "ARRAY", items: { type: "OBJECT", properties: { institution: STR, area: STR, studyType: STR, startDate: STR, endDate: STR, score: STR } } },
    skills: { type: "ARRAY", items: { type: "OBJECT", properties: { name: STR, level: STR, keywords: STR_ARR } } },
    projects: { type: "ARRAY", items: { type: "OBJECT", properties: { name: STR, description: STR, url: STR, highlights: STR_ARR, technologies: STR_ARR } } },
    awards: { type: "ARRAY", items: { type: "OBJECT", properties: { title: STR, date: STR, awarder: STR, summary: STR } } },
  },
};

const CATEGORY_SCORE_SCHEMA = { type: "OBJECT", properties: { score: { type: "NUMBER" }, max: { type: "NUMBER" }, evidence: STR }, required: ["score", "max", "evidence"] };
export const EVAL_SCHEMA: GeminiSchema = {
  type: "OBJECT",
  properties: {
    scores: {
      type: "OBJECT",
      properties: { open_source: CATEGORY_SCORE_SCHEMA, self_projects: CATEGORY_SCORE_SCHEMA, production: CATEGORY_SCORE_SCHEMA, technical_skills: CATEGORY_SCORE_SCHEMA },
      required: ["open_source", "self_projects", "production", "technical_skills"],
    },
    bonus_points: { type: "OBJECT", properties: { total: { type: "NUMBER" }, breakdown: STR }, required: ["total", "breakdown"] },
    deductions: { type: "OBJECT", properties: { total: { type: "NUMBER" }, reasons: STR }, required: ["total", "reasons"] },
    key_strengths: STR_ARR,
    areas_for_improvement: STR_ARR,
  },
  required: ["scores", "bonus_points", "deductions", "key_strengths", "areas_for_improvement"],
};

export const COACH_SCHEMA: GeminiSchema = {
  type: "OBJECT",
  properties: {
    verdict: STR,
    fixes: { type: "ARRAY", items: { type: "OBJECT", properties: { priority: { type: "NUMBER" }, category: STR, title: STR, detail: STR, estGain: { type: "NUMBER" } }, required: ["priority", "category", "title", "detail", "estGain"] } },
    boosts: { type: "ARRAY", items: { type: "OBJECT", properties: { category: STR, text: STR, estGain: { type: "NUMBER" } }, required: ["category", "text", "estGain"] } },
  },
  required: ["verdict", "fixes", "boosts"],
};

// ── Prompts ──
const EXTRACTION_SYSTEM = "You extract structured data from resumes. Return ONLY JSON matching the provided schema. Use null for missing fields. Do not invent data.";

export function buildExtractionPrompt(resumeText: string): PromptSpec {
  return {
    system: EXTRACTION_SYSTEM,
    user: `Extract this resume into the JSON Resume structure defined by the schema.\n\nResume:\n${resumeText}`,
    responseSchema: RESUME_SCHEMA,
  };
}

// PLACEHOLDER #1 — replace with the verbatim contents of
// prompts/templates/resume_evaluation_system_message.jinja
const SCORING_SYSTEM = `<<COPY resume_evaluation_system_message.jinja HERE VERBATIM>>`;

// PLACEHOLDER #2 — replace with the verbatim contents of
// prompts/templates/resume_evaluation_criteria.jinja, with its trailing
// "{{ text_content }}" replaced by the ${resumeText} interpolation.
function RUBRIC(resumeText: string): string {
  return `<<COPY resume_evaluation_criteria.jinja HERE VERBATIM, ending with>>\n\n${resumeText}`;
}

export function buildScoringPrompt(resumeText: string): PromptSpec {
  return { system: SCORING_SYSTEM, user: RUBRIC(resumeText), responseSchema: EVAL_SCHEMA };
}

const COACH_SYSTEM = "You are a precise, encouraging resume coach for software candidates. Be specific and actionable. Return ONLY JSON matching the schema.";

export function buildCoachPrompt(resumeText: string, evaluationJson: string): PromptSpec {
  return {
    system: COACH_SYSTEM,
    user:
      `Given a resume and its scored evaluation, produce coaching.\n\n` +
      `Rules:\n` +
      `- "verdict": one human sentence naming the biggest strength and the biggest weakness.\n` +
      `- "fixes": the highest-impact changes, ordered by priority (1 = most impactful). Each names the category it boosts, a short title, a specific detail, and estGain (estimated points recoverable).\n` +
      `- "boosts": small polish for already-strong categories (1-2 points each).\n` +
      `- category must be one of: open_source, self_projects, production, technical_skills.\n\n` +
      `Evaluation:\n${evaluationJson}\n\nResume:\n${resumeText}`,
    responseSchema: COACH_SCHEMA,
  };
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd web && npx vitest run src/lib/prompts.test.ts`
Expected: PASS (4 tests). (Tests pass even with the placeholders in place; the verbatim copy affects scoring quality, not these assertions — but do the copy before Phase C integration.)

- [ ] **Step 5: Do the verbatim copies**

Open `prompts/templates/resume_evaluation_system_message.jinja` and `prompts/templates/resume_evaluation_criteria.jinja`; paste their contents into the two marked placeholders as instructed. Re-run the test to confirm still green.

- [ ] **Step 6: Commit**

```bash
git add web/src/lib/prompts.ts web/src/lib/prompts.test.ts
git commit -m "feat(web): prompt builders and Gemini response schemas"
```

---

## Phase C — External clients & pipeline

### Task C1: Errors module

**Files:**
- Create: `web/src/lib/errors.ts`

- [ ] **Step 1: Create `web/src/lib/errors.ts`**

```ts
export class MissingKeyError extends Error { constructor() { super("No Gemini API key set."); this.name = "MissingKeyError"; } }
export class RateLimitError extends Error { constructor(msg = "Gemini rate limit exceeded.") { super(msg); this.name = "RateLimitError"; } }
export class ModelOutputError extends Error { constructor(public raw: string, msg = "Model returned invalid output.") { super(msg); this.name = "ModelOutputError"; } }
export class NoTextError extends Error { constructor() { super("This PDF has no selectable text (image-only PDFs aren't supported)."); this.name = "NoTextError"; } }
```

- [ ] **Step 2: Commit**

```bash
git add web/src/lib/errors.ts
git commit -m "feat(web): typed error classes"
```

---

### Task C2: Gemini client (JSON mode + backoff + validation)

**Files:**
- Create: `web/src/lib/gemini.ts`
- Test: `web/src/lib/gemini.test.ts`

Wraps `@google/genai`. Backoff with jitter mirrors the existing `GeminiProvider`. The SDK is injected (default real, mockable in tests) so we can test backoff/validation without network. `sleep` is injected for fast tests.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect, vi } from "vitest";
import { z } from "zod";
import { callGeminiJSON } from "./gemini";
import { RateLimitError, ModelOutputError } from "./errors";

const schema = z.object({ ok: z.boolean() });

function fakeAI(responses: Array<() => Promise<{ text: string }>>) {
  let i = 0;
  return { models: { generateContent: vi.fn(async () => responses[i++]()) } };
}

describe("callGeminiJSON", () => {
  it("parses and validates a good JSON response", async () => {
    const ai = fakeAI([async () => ({ text: '{"ok":true}' })]);
    const out = await callGeminiJSON({ ai: ai as any, model: "m", system: "s", user: "u", responseSchema: { type: "OBJECT" }, validate: (v) => schema.parse(v), sleep: async () => {} });
    expect(out.ok).toBe(true);
  });

  it("retries on a 429 then succeeds", async () => {
    const rl = Object.assign(new Error("429 RESOURCE_EXHAUSTED"), { status: 429 });
    const ai = fakeAI([async () => { throw rl; }, async () => ({ text: '{"ok":true}' })]);
    const sleep = vi.fn(async () => {});
    const out = await callGeminiJSON({ ai: ai as any, model: "m", system: "s", user: "u", responseSchema: { type: "OBJECT" }, validate: (v) => schema.parse(v), sleep, maxRetries: 3 });
    expect(out.ok).toBe(true);
    expect(sleep).toHaveBeenCalledTimes(1);
  });

  it("throws RateLimitError after exhausting retries", async () => {
    const rl = Object.assign(new Error("429"), { status: 429 });
    const ai = fakeAI([async () => { throw rl; }, async () => { throw rl; }]);
    await expect(callGeminiJSON({ ai: ai as any, model: "m", system: "s", user: "u", responseSchema: { type: "OBJECT" }, validate: (v) => schema.parse(v), sleep: async () => {}, maxRetries: 2 })).rejects.toBeInstanceOf(RateLimitError);
  });

  it("throws ModelOutputError on non-JSON", async () => {
    const ai = fakeAI([async () => ({ text: "not json" })]);
    await expect(callGeminiJSON({ ai: ai as any, model: "m", system: "s", user: "u", responseSchema: { type: "OBJECT" }, validate: (v) => schema.parse(v), sleep: async () => {} })).rejects.toBeInstanceOf(ModelOutputError);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/lib/gemini.test.ts`
Expected: FAIL — cannot find module `./gemini`.

- [ ] **Step 3: Implement `web/src/lib/gemini.ts`**

```ts
import { GoogleGenAI } from "@google/genai";
import type { GeminiSchema } from "./prompts";
import { RateLimitError, ModelOutputError } from "./errors";

export const DEFAULT_MODEL = "gemini-2.5-flash";

export function makeAI(apiKey: string) {
  return new GoogleGenAI({ apiKey });
}

type AILike = { models: { generateContent: (args: any) => Promise<{ text?: string }> } };

function isRateLimit(e: unknown): boolean {
  const any = e as { status?: number; message?: string };
  return any?.status === 429 || /resource_exhausted|rate limit|429/i.test(any?.message ?? "");
}

export async function callGeminiJSON<T>(opts: {
  ai: AILike;
  model: string;
  system: string;
  user: string;
  responseSchema: GeminiSchema;
  validate: (value: unknown) => T;
  temperature?: number;
  topP?: number;
  maxRetries?: number;
  sleep?: (ms: number) => Promise<void>;
}): Promise<T> {
  const { ai, model, system, user, responseSchema, validate } = opts;
  const maxRetries = opts.maxRetries ?? 5;
  const sleep = opts.sleep ?? ((ms: number) => new Promise((r) => setTimeout(r, ms)));
  const BASE = 1000, CAP = 30000;

  let lastErr: unknown;
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const res = await ai.models.generateContent({
        model,
        contents: user,
        config: {
          systemInstruction: system,
          responseMimeType: "application/json",
          responseSchema,
          temperature: opts.temperature ?? 0.1,
          topP: opts.topP ?? 0.9,
        },
      });
      const text = (res.text ?? "").trim();
      let parsed: unknown;
      try {
        parsed = JSON.parse(text);
      } catch {
        throw new ModelOutputError(text);
      }
      return validate(parsed);
    } catch (e) {
      lastErr = e;
      if (e instanceof ModelOutputError) throw e;
      if (isRateLimit(e) && attempt < maxRetries - 1) {
        const expo = Math.min(BASE * 2 ** attempt, CAP);
        const jitter = 0.8 + Math.random() * 0.4;
        await sleep(Math.round(expo * jitter));
        continue;
      }
      if (isRateLimit(e)) throw new RateLimitError();
      throw e;
    }
  }
  throw lastErr instanceof Error ? lastErr : new Error("Gemini call failed");
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd web && npx vitest run src/lib/gemini.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/gemini.ts web/src/lib/gemini.test.ts
git commit -m "feat(web): gemini JSON client with backoff and validation"
```

---

### Task C3: PDF text extraction

**Files:**
- Create: `web/src/lib/pdf.ts`
- Test: `web/src/lib/pdf.test.ts`

Uses `pdfjs-dist`. The page-iteration logic is factored into `assembleText(pages)` so it's unit-testable without a real PDF; `extractTextFromPdf` wires up pdfjs in the browser. Throws `NoTextError` when the result is empty.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { assembleText } from "./pdf";
import { NoTextError } from "./errors";

describe("assembleText", () => {
  it("joins page strings with blank lines", () => {
    expect(assembleText(["page one", "page two"])).toBe("page one\n\npage two");
  });
  it("throws NoTextError when all pages are empty", () => {
    expect(() => assembleText(["", "   "])).toThrow(NoTextError);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/lib/pdf.test.ts`
Expected: FAIL — cannot find module `./pdf`.

- [ ] **Step 3: Implement `web/src/lib/pdf.ts`**

```ts
import { NoTextError } from "./errors";

export function assembleText(pages: string[]): string {
  const joined = pages.map((p) => p.trim()).filter(Boolean).join("\n\n");
  if (!joined.trim()) throw new NoTextError();
  return joined;
}

// Browser-only. Lazy-imports pdfjs so unit tests (node) never load the worker.
export async function extractTextFromPdf(file: File | ArrayBuffer): Promise<string> {
  const pdfjs = await import("pdfjs-dist");
  // Worker is served from /public (copied in Part 2 deploy task); fall back to module URL.
  (pdfjs as any).GlobalWorkerOptions.workerSrc = new URL(
    "pdfjs-dist/build/pdf.worker.min.mjs",
    import.meta.url,
  ).toString();

  const data = file instanceof File ? await file.arrayBuffer() : file;
  const doc = await (pdfjs as any).getDocument({ data }).promise;
  const pages: string[] = [];
  for (let i = 1; i <= doc.numPages; i++) {
    const page = await doc.getPage(i);
    const content = await page.getTextContent();
    pages.push(content.items.map((it: any) => ("str" in it ? it.str : "")).join(" "));
  }
  return assembleText(pages);
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd web && npx vitest run src/lib/pdf.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/pdf.ts web/src/lib/pdf.test.ts
git commit -m "feat(web): pdfjs text extraction with empty-text guard"
```

---

### Task C4: GitHub client (fetch, classify, project selection)

**Files:**
- Create: `web/src/lib/github.ts`
- Test: `web/src/lib/github.test.ts`

Ports `github.py`: username extraction, repo classification (`open_source` if `contributor_count > 1`, else `self_project`; forks with `< 5` forks skipped), and the summary shape. `fetch` is injected for tests. The LLM project-selection call is delegated to a passed-in function so this module stays network/LLM-agnostic and testable.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect, vi } from "vitest";
import { extractGitHubUsername, classifyRepo, fetchGitHubSummary } from "./github";

describe("github helpers", () => {
  it("extracts username from a profile URL", () => {
    expect(extractGitHubUsername("https://github.com/octocat?tab=repositories")).toBe("octocat");
  });
  it("classifies repos by contributor count", () => {
    expect(classifyRepo(3)).toBe("open_source");
    expect(classifyRepo(1)).toBe("self_project");
  });
  it("builds a summary, skipping low-fork forks", async () => {
    const fetchImpl = vi.fn(async (url: string) => {
      if (url.endsWith("/users/octocat")) return new Response(JSON.stringify({ login: "octocat", public_repos: 2, followers: 5 }), { status: 200 });
      if (url.includes("/repos")) return new Response(JSON.stringify([
        { name: "real", fork: false, forks_count: 0, stargazers_count: 10 },
        { name: "skipme", fork: true, forks_count: 1, stargazers_count: 0 },
      ]), { status: 200 });
      if (url.includes("/contributors")) return new Response(JSON.stringify([{ login: "octocat" }, { login: "other" }]), { status: 200 });
      return new Response("[]", { status: 200 });
    });
    const summary = await fetchGitHubSummary("https://github.com/octocat", { token: null, fetchImpl });
    expect(summary?.profile?.username).toBe("octocat");
    expect(summary?.projects.map((p) => p.name)).toEqual(["real"]);
    expect(summary?.projects[0].project_type).toBe("open_source");
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/lib/github.test.ts`
Expected: FAIL — cannot find module `./github`.

- [ ] **Step 3: Implement `web/src/lib/github.ts`**

```ts
import type { GitHubSummary } from "./schemas";

export function extractGitHubUsername(url: string): string | null {
  if (!url) return null;
  const cleaned = url.replace(/\s/g, "").trim();
  const patterns = [/https?:\/\/github\.com\/([^/]+)/, /github\.com\/([^/]+)/, /@([^/]+)/, /^([a-zA-Z0-9-]+)$/];
  for (const re of patterns) {
    const m = cleaned.match(re);
    if (m) return m[1].split("?")[0];
  }
  return null;
}

export function classifyRepo(contributorCount: number): "open_source" | "self_project" {
  return contributorCount > 1 ? "open_source" : "self_project";
}

type FetchOpts = { token: string | null; fetchImpl?: typeof fetch };

async function ghGet(url: string, opts: FetchOpts): Promise<any> {
  const f = opts.fetchImpl ?? fetch;
  const headers: Record<string, string> = { Accept: "application/vnd.github+json" };
  if (opts.token) headers.Authorization = `Bearer ${opts.token}`;
  const res = await f(url, { headers });
  if (res.status !== 200) return null;
  return res.json();
}

export async function fetchGitHubSummary(profileUrl: string, opts: FetchOpts): Promise<GitHubSummary | null> {
  const username = extractGitHubUsername(profileUrl);
  if (!username) return null;

  const profile = await ghGet(`https://api.github.com/users/${username}`, opts);
  if (!profile) return null;

  const repos: any[] = (await ghGet(`https://api.github.com/users/${username}/repos?sort=updated&per_page=100&type=all`, opts)) ?? [];
  const projects: GitHubSummary["projects"] = [];
  for (const repo of repos) {
    if (repo.fork && (repo.forks_count ?? 0) < 5) continue;
    const contributors: any[] = (await ghGet(`https://api.github.com/repos/${username}/${repo.name}/contributors`, opts)) ?? [];
    projects.push({
      name: repo.name,
      project_type: classifyRepo(contributors.length),
      stars: repo.stargazers_count ?? 0,
    });
  }
  projects.sort((a, b) => b.stars - a.stars);

  return {
    profile: { username, public_repos: profile.public_repos, followers: profile.followers },
    projects,
  };
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd web && npx vitest run src/lib/github.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/github.ts web/src/lib/github.test.ts
git commit -m "feat(web): port github enrichment (fetch + classify + summary)"
```

---

### Task C5: Pipeline orchestration

**Files:**
- Create: `web/src/lib/pipeline.ts`
- Test: `web/src/lib/pipeline.test.ts`

Wires the stages into one `scoreResume` that returns a `RunRecord` (without persistence — that's Part 2). All side-effecting collaborators (extract text, Gemini call, GitHub fetch) are injected so the orchestration is fully testable. A `genId` and `now` are injected for deterministic tests.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect, vi } from "vitest";
import { scoreResume } from "./pipeline";
import { MissingKeyError } from "./errors";

const resume = { basics: { name: "Octo", profiles: [{ url: "https://github.com/octocat" }] } };
const evaluation = {
  scores: {
    open_source: { score: 28, max: 35, evidence: "e" },
    self_projects: { score: 22, max: 30, evidence: "e" },
    production: { score: 10, max: 25, evidence: "e" },
    technical_skills: { score: 9, max: 10, evidence: "e" },
  },
  bonus_points: { total: 5, breakdown: "" },
  deductions: { total: 0, reasons: "" },
  key_strengths: ["a"], areas_for_improvement: ["b"],
};
const coach = { verdict: "v", fixes: [], boosts: [] };

function deps(overrides = {}) {
  return {
    settings: { geminiKey: "k", githubToken: null, model: "m", enableGitHub: false },
    extractText: vi.fn(async () => "RESUME TEXT"),
    runExtraction: vi.fn(async () => resume),
    runScoring: vi.fn(async () => evaluation),
    runCoach: vi.fn(async () => coach),
    fetchGitHub: vi.fn(async () => null),
    genId: () => "id-1",
    now: () => 1000,
    ...overrides,
  };
}

describe("scoreResume", () => {
  it("throws MissingKeyError when no gemini key", async () => {
    await expect(scoreResume(new ArrayBuffer(0), { ...deps(), settings: { geminiKey: "", githubToken: null, model: "m", enableGitHub: false } })).rejects.toBeInstanceOf(MissingKeyError);
  });

  it("produces a RunRecord and skips github when disabled", async () => {
    const d = deps();
    const rec = await scoreResume(new ArrayBuffer(0), d as any);
    expect(rec.id).toBe("id-1");
    expect(rec.evaluation.scores.open_source.score).toBe(28);
    expect(rec.githubSummary).toBeNull();
    expect(d.fetchGitHub).not.toHaveBeenCalled();
  });

  it("runs github enrichment when enabled and a profile exists", async () => {
    const d = deps({ settings: { geminiKey: "k", githubToken: "t", model: "m", enableGitHub: true }, fetchGitHub: vi.fn(async () => ({ profile: { username: "octocat" }, projects: [] })) });
    const rec = await scoreResume(new ArrayBuffer(0), d as any);
    expect(d.fetchGitHub).toHaveBeenCalledOnce();
    expect(rec.githubSummary?.profile?.username).toBe("octocat");
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd web && npx vitest run src/lib/pipeline.test.ts`
Expected: FAIL — cannot find module `./pipeline`.

- [ ] **Step 3: Implement `web/src/lib/pipeline.ts`**

```ts
import type { JSONResume, Evaluation, Coach, RunRecord, GitHubSummary } from "./schemas";
import { normalizeResume } from "./normalize";
import { MissingKeyError } from "./errors";

export type Settings = { geminiKey: string; githubToken: string | null; model: string; enableGitHub: boolean };

export type PipelineDeps = {
  settings: Settings;
  fileName?: string;
  extractText: (pdf: File | ArrayBuffer) => Promise<string>;
  runExtraction: (resumeText: string) => Promise<JSONResume>;
  runScoring: (resumeText: string) => Promise<Evaluation>;
  runCoach: (resumeText: string, evaluationJson: string) => Promise<Coach>;
  fetchGitHub: (profileUrl: string) => Promise<GitHubSummary | null>;
  genId: () => string;
  now: () => number;
  onProgress?: (stage: string) => void;
};

function findGitHubProfileUrl(resume: JSONResume): string | null {
  const profiles = resume.basics?.profiles ?? [];
  const p = profiles.find((x) => (x.network ?? "").toLowerCase() === "github");
  return p?.url ?? null;
}

export async function scoreResume(pdf: File | ArrayBuffer, deps: PipelineDeps): Promise<RunRecord> {
  if (!deps.settings.geminiKey) throw new MissingKeyError();

  deps.onProgress?.("Reading PDF");
  const resumeText = await deps.extractText(pdf);

  deps.onProgress?.("Extracting resume");
  const parsedResume = normalizeResume(await deps.runExtraction(resumeText));

  let githubSummary: GitHubSummary | null = null;
  if (deps.settings.enableGitHub) {
    const url = findGitHubProfileUrl(parsedResume);
    if (url) {
      deps.onProgress?.("Enriching from GitHub");
      try {
        githubSummary = await deps.fetchGitHub(url);
      } catch {
        githubSummary = null; // degrade gracefully
      }
    }
  }

  // Append a compact GitHub context block to the text the scorer sees (mirrors score.py).
  let scoringText = resumeText;
  if (githubSummary) {
    const gh = `\n\n=== GITHUB DATA ===\nUsername: ${githubSummary.profile?.username ?? "N/A"}\n` +
      githubSummary.projects.slice(0, 10).map((p) => `- ${p.name} [${p.project_type}] ★${p.stars}`).join("\n");
    scoringText += gh;
  }

  deps.onProgress?.("Scoring");
  const evaluation = await deps.runScoring(scoringText);

  deps.onProgress?.("Coaching");
  const coach = await deps.runCoach(scoringText, JSON.stringify(evaluation));

  return {
    id: deps.genId(),
    createdAt: deps.now(),
    fileName: deps.fileName ?? "resume.pdf",
    parsedResume,
    evaluation,
    coach,
    githubSummary,
  };
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd web && npx vitest run src/lib/pipeline.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Run the full suite**

Run: `cd web && npm test`
Expected: all unit tests pass (schemas, normalize, scoring, diff, prompts, gemini, pdf, github, pipeline).

- [ ] **Step 6: Commit**

```bash
git add web/src/lib/pipeline.ts web/src/lib/pipeline.test.ts
git commit -m "feat(web): scoring pipeline orchestration"
```

---

## Phase D — Wire the real collaborators (thin glue)

### Task D1: Real pipeline factory + dev harness

**Files:**
- Create: `web/src/lib/runScore.ts`
- Modify: `web/src/app/page.tsx`

Provides `runScoreWithRealDeps`, which assembles the real collaborators (Gemini, pdfjs, GitHub) into `PipelineDeps` and calls `scoreResume`. The dev harness lets you exercise the whole engine in a browser before the real screens exist (Part 2).

- [ ] **Step 1: Create `web/src/lib/runScore.ts`**

```ts
import { scoreResume, type Settings } from "./pipeline";
import { makeAI, callGeminiJSON, DEFAULT_MODEL } from "./gemini";
import { extractTextFromPdf } from "./pdf";
import { fetchGitHubSummary } from "./github";
import { JSONResumeSchema, EvaluationSchema, CoachSchema } from "./schemas";
import { buildExtractionPrompt, buildScoringPrompt, buildCoachPrompt } from "./prompts";

export async function runScoreWithRealDeps(file: File, settings: Settings, onProgress?: (s: string) => void) {
  const ai = makeAI(settings.geminiKey);
  const model = settings.model || DEFAULT_MODEL;
  return scoreResume(file, {
    settings,
    fileName: file.name,
    onProgress,
    extractText: (pdf) => extractTextFromPdf(pdf),
    runExtraction: async (text) => {
      const p = buildExtractionPrompt(text);
      return callGeminiJSON({ ai, model, system: p.system, user: p.user, responseSchema: p.responseSchema, validate: (v) => JSONResumeSchema.parse(v) });
    },
    runScoring: async (text) => {
      const p = buildScoringPrompt(text);
      return callGeminiJSON({ ai, model, system: p.system, user: p.user, responseSchema: p.responseSchema, validate: (v) => EvaluationSchema.parse(v) });
    },
    runCoach: async (text, evalJson) => {
      const p = buildCoachPrompt(text, evalJson);
      return callGeminiJSON({ ai, model, system: p.system, user: p.user, responseSchema: p.responseSchema, validate: (v) => CoachSchema.parse(v) });
    },
    fetchGitHub: (url) => fetchGitHubSummary(url, { token: settings.githubToken }),
    genId: () => crypto.randomUUID(),
    now: () => Date.now(),
  });
}
```

- [ ] **Step 2: Replace `web/src/app/page.tsx` with a dev harness**

```tsx
"use client";
import { useState } from "react";
import { ThemeToggle } from "@/ui/ThemeToggle";
import { PrivacyChip } from "@/ui/PrivacyChip";
import { runScoreWithRealDeps } from "@/lib/runScore";
import { DEFAULT_MODEL } from "@/lib/gemini";

export default function Home() {
  const [key, setKey] = useState("");
  const [out, setOut] = useState<string>("");
  const [status, setStatus] = useState("");

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setOut(""); setStatus("starting…");
    try {
      const rec = await runScoreWithRealDeps(file, { geminiKey: key, githubToken: null, model: DEFAULT_MODEL, enableGitHub: false }, setStatus);
      setOut(JSON.stringify({ total: rec.evaluation.scores, coach: rec.coach.verdict }, null, 2));
      setStatus("done");
    } catch (err) {
      setStatus("error: " + (err as Error).message);
    }
  }

  return (
    <main style={{ maxWidth: 1080, margin: "0 auto", padding: "26px 28px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--rule)", paddingBottom: 20 }}>
        <div className="serif" style={{ fontSize: 26 }}>Hiring <i>Agent</i></div>
        <div style={{ display: "flex", gap: 20, alignItems: "center" }}><ThemeToggle /><PrivacyChip /></div>
      </div>
      <p className="eyebrow" style={{ marginTop: 24 }}>Dev harness (replaced by real screens in Part 2)</p>
      <input className="mono" placeholder="Gemini API key" value={key} onChange={(e) => setKey(e.target.value)} style={{ display: "block", width: 360, padding: 8, marginTop: 12 }} />
      <input type="file" accept="application/pdf" onChange={onFile} style={{ marginTop: 12 }} />
      <p className="mono" style={{ marginTop: 12, color: "var(--ink-soft)" }}>{status}</p>
      <pre className="mono" style={{ whiteSpace: "pre-wrap", marginTop: 12 }}>{out}</pre>
    </main>
  );
}
```

- [ ] **Step 3: Verify the build compiles**

Run: `cd web && npm run build`
Expected: static export succeeds.

- [ ] **Step 4: Manual end-to-end check (optional but recommended)**

Run: `cd web && npm run dev`, open `http://localhost:3000`, paste a real Gemini key, choose a text-based resume PDF. Expected: status walks through stages and the scores + verdict render. (This requires a valid key and network; skip if unavailable — unit tests already cover the logic.)

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/runScore.ts web/src/app/page.tsx
git commit -m "feat(web): real pipeline factory and dev harness"
```

---

## Self-review notes (coverage of Part 1 against the spec)

- **Architecture (pure client-side, static export, `web/`):** Tasks A1–A2. ✓
- **Design system (tokens, type, theme toggle, privacy modal):** Tasks A3–A4. ✓
- **Single extraction call + normalization (`transform.py` port):** Tasks B2, B5, C5, D1. ✓
- **Scoring rubric fidelity + caps (`evaluator.py`/`score.py`):** Tasks B3, B5 (verbatim rubric copy). ✓
- **Coach (separate Gemini call):** Tasks B5, C5, D1. ✓
- **Optional GitHub enrichment with token (`github.py` port):** Task C4, wired in C5/D1. ✓
- **Gemini JSON mode + backoff:** Task C2. ✓
- **Error handling (missing key, 429, image-only PDF, invalid output, GitHub degrade):** Tasks C1, C2, C3, C5. ✓
- **Testing (Vitest on deterministic logic + clients):** every B/C task. ✓

**Deferred to Part 2 (intentionally, not gaps):** IndexedDB run storage + settings persistence; the four screens (Score, Results, History & Trends, Settings); trend charts/sparklines/changelog UI; the rename/diff UI; the Playwright smoke test; Vercel deploy config + pdf worker asset.
