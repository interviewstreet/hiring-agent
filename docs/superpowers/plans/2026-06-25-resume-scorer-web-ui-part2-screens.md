# Resume Scorer Web UI — Implementation Plan (Part 2 of 2: Screens, Storage & Deploy)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the finished, tested Part 1 engine into the actual product — four screens (Score, Results, History & Trends, Settings) backed by browser-only IndexedDB storage, plus a Playwright smoke test and Vercel deploy — fulfilling the privacy-first web UI design spec.

**Architecture:** A Next.js (App Router) static export under `web/`, all client-rendered. Part 1 already provides the deterministic core (`scoring`, `diff`, `normalize`, `schemas`) and the external clients (`gemini`, `pdf`, `github`, `pipeline`, `runScore`); Part 2 adds a persistence layer (`store.ts` over IndexedDB via `idb`, `settings.ts` over `localStorage`), pure trend/chart math (`trends.ts`), a shared app shell + routing, the four screens as components under `web/src/ui/screens/`, and the deploy glue. Run records live in IndexedDB; settings/keys in `localStorage` (or session-only memory when "remember keys" is off). Each scoring run navigates Score → Results via `?run=<id>`.

**Tech Stack:** Next.js 15, React 19, TypeScript, `idb` (IndexedDB), `pdfjs-dist`, `@google/genai` (Gemini), `zod`, hand-rolled SVG charts (no chart dep), Vitest + `fake-indexeddb` (unit), Playwright (smoke). Design system: plain CSS custom properties + `next/font/google` (Instrument Serif, Archivo, JetBrains Mono), reusing the Part 1 tokens and the v5 Results / Trends mockups as the visual contract.

---

## Prerequisites & state

Part 1 is complete and green (`cd web && npx vitest run` → 47 passing). `idb` and `@playwright/test` are already declared in `web/package.json` (unused until this plan). This plan only adds new files under `web/` and edits a small number of Part 1 files (`schemas.ts`, `scoring.ts`, `layout.tsx`, `page.tsx`); no Python or other existing files change.

## File structure (created / modified in Part 2)

```
web/
  package.json                 # MODIFY: add fake-indexeddb (+ pdfkit for the fixture generator) devDeps
  next.config.mjs              # (unchanged; output:'export' already set)
  vercel.json                  # CREATE: Vercel static deploy config (root = web/)
  README.md                    # CREATE: setup / run / deploy / "scores are indicative" note
  playwright.config.ts         # CREATE: e2e config (webServer + chromium)
  public/
    pdf.worker.min.mjs         # CREATE (deploy asset): pdf.js worker copied for static export
  e2e/
    smoke.spec.ts              # CREATE: upload → mocked-Gemini → Results renders
  test/fixtures/
    make-sample-pdf.mjs        # CREATE: one-shot generator for the sample resume PDF
    sample-resume.pdf          # CREATE (generated): text-based fixture for the smoke test
  src/
    app/
      layout.tsx               # MODIFY: wrap children in <SettingsProvider> (inside ThemeProvider)
      page.tsx                 # REPLACE: dev harness → Score route
      results/page.tsx         # CREATE: Results route (Suspense + ?run)
      diff/page.tsx            # CREATE: Diff route (?a&b)
      history/page.tsx         # CREATE: History & Trends route
      settings/page.tsx        # CREATE: Settings route
      globals.css              # MODIFY: shared shell classes (.wrap/.top/.mark/.nav/...)
    lib/
      schemas.ts               # MODIFY: RunRecord.pdfBlob?, StoredSettings type
      scoring.ts               # MODIFY: statusLabel(status)
      store.ts                 # CREATE: IndexedDB run storage (idb)
      settings.ts              # CREATE: localStorage + session-memory settings
      trends.ts                # CREATE: pure series / summary / chart-path math
      errorMessage.ts          # CREATE: error → friendly copy (pure)
      *.test.ts                # CREATE: store / settings / trends / errorMessage / scoring tests
    ui/
      SettingsProvider.tsx     # CREATE: settings context (useSettings)
      AppShell.tsx             # CREATE: top bar + nav + theme + privacy shell
      Delta.tsx (+ test)       # CREATE: ▲/▼/— delta vocabulary
      Dropzone.tsx             # CREATE: drag-drop PDF input
      CategoryRow.tsx          # CREATE: one scorecard row (bar + status + delta)
      RevisionRail.tsx         # CREATE: commit-log revision rail
      CoachSection.tsx         # CREATE: fixes + small boosts
      TotalChart.tsx           # CREATE: SVG total-over-time chart
      Sparkline.tsx            # CREATE: SVG per-category sparkline
      HistoryTable.tsx         # CREATE: changelog table (rename/view/diff/delete)
      screens/
        ScoreScreen.tsx        # CREATE (stub in G, real in H)
        ResultsScreen.tsx      # CREATE (stub in G, real in I)
        DiffScreen.tsx         # CREATE (stub in G, real in I)
        HistoryScreen.tsx      # CREATE (stub in G, real in J)
        SettingsScreen.tsx     # CREATE (stub in G, real in K)
```

**Phase order (each phase is independently committable, every commit builds green):**
`E` Storage & settings → `F` Trend/chart math → `G` App shell & routing (stubs) → `H` Score → `I` Results + Diff → `J` History & Trends → `K` Settings → `L` Playwright + deploy.

---


## Phase E — Storage & settings foundation

This phase delivers the client-side persistence and settings substrate the rest of the UI builds on: an IndexedDB-backed run store (`store.ts`), a localStorage-with-session-fallback settings module (`settings.ts`), a React `SettingsProvider` context wired into the root layout, and the schema additions (`RunRecord.pdfBlob`, `StoredSettings`) the contract requires. All persistence logic is browser-safe (guarded `localStorage`/`indexedDB` access) and fully test-driven with Vitest using `fake-indexeddb/auto` (store) and a `jsdom` environment (settings).

### Task 1: Add test/dev dependencies

**Files:**
- Modify: `web/package.json` (lines 24–31, `devDependencies` block)

- [ ] **Step 1: Add `fake-indexeddb` and `jsdom` to devDependencies.** `store.test.ts` imports `fake-indexeddb/auto`; `settings.test.ts` runs under the `jsdom` environment (the repo's `vitest.config.ts` defaults to `environment: "node"`, so `jsdom` must be installed for the per-file `// @vitest-environment jsdom` pragma to resolve). Replace the `devDependencies` block:

```json
  "devDependencies": {
    "typescript": "^5.6.0",
    "@types/node": "^22.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "vitest": "^2.1.0",
    "@playwright/test": "^1.48.0",
    "fake-indexeddb": "^6.0.0",
    "jsdom": "^25.0.0"
  }
```

- [ ] **Step 2: Install (manual, not committed).** Run: `cd web && npm install`. This updates `package-lock.json` and `node_modules` (node_modules is gitignored; do not commit it).
- [ ] **Step 3: Commit the manifest + lockfile.** Run:

```bash
git add web/package.json web/package-lock.json
git commit -m "chore(web): add fake-indexeddb and jsdom dev deps for store/settings tests"
```

### Task 2: Extend schemas — `RunRecord.pdfBlob` and `StoredSettings`

**Files:**
- Modify: `web/src/lib/schemas.ts` (lines 113–123, the `RunRecord` type block at end of file)

- [ ] **Step 1: Add `pdfBlob` to `RunRecord` and append `StoredSettings`.** These are types only — no test. Replace the trailing `RunRecord` block:

```ts
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
  pdfBlob?: Blob | null;
};

// ── Persisted settings (UI-facing superset of pipeline Settings) ──
export type StoredSettings = {
  geminiKey: string;
  githubToken: string;
  model: string;
  enableGitHub: boolean;
  rememberKeys: boolean;
};
```

- [ ] **Step 2: Type-check.** Run: `cd web && npx tsc --noEmit`. Expected: PASS (no errors).
- [ ] **Step 3: Commit.** Run:

```bash
git add web/src/lib/schemas.ts
git commit -m "feat(web): add RunRecord.pdfBlob and StoredSettings type"
```

### Task 3: IndexedDB run store (`store.ts`) — TDD

**Files:**
- Create: `web/src/lib/store.ts`
- Test: `web/src/lib/store.test.ts`

- [ ] **Step 1: Write the failing test.** Create `web/src/lib/store.test.ts`:

```ts
import "fake-indexeddb/auto";
import { beforeEach, describe, expect, it } from "vitest";
import {
  saveRun,
  listRuns,
  getRun,
  deleteRun,
  renameRun,
  clearAllRuns,
} from "./store";
import type { RunRecord } from "./schemas";

function makeRun(id: string, createdAt: number): RunRecord {
  return {
    id,
    createdAt,
    fileName: `${id}.pdf`,
    parsedResume: {},
    evaluation: {
      scores: {
        open_source: { score: 0, max: 35, evidence: "x" },
        self_projects: { score: 0, max: 30, evidence: "x" },
        production: { score: 0, max: 25, evidence: "x" },
        technical_skills: { score: 0, max: 10, evidence: "x" },
      },
      bonus_points: { total: 0, breakdown: "" },
      deductions: { total: 0, reasons: "" },
      key_strengths: ["a"],
      areas_for_improvement: ["b"],
    },
    coach: { verdict: "ok", fixes: [], boosts: [] },
  };
}

describe("store", () => {
  beforeEach(async () => {
    await clearAllRuns();
  });

  it("save then getRun round-trips", async () => {
    const run = makeRun("r1", 100);
    await saveRun(run);
    const got = await getRun("r1");
    expect(got).toEqual(run);
  });

  it("getRun returns undefined for missing id", async () => {
    expect(await getRun("nope")).toBeUndefined();
  });

  it("listRuns returns ascending by createdAt", async () => {
    await saveRun(makeRun("b", 200));
    await saveRun(makeRun("a", 100));
    await saveRun(makeRun("c", 300));
    const ids = (await listRuns()).map((r) => r.id);
    expect(ids).toEqual(["a", "b", "c"]);
  });

  it("renameRun sets label", async () => {
    await saveRun(makeRun("r1", 100));
    await renameRun("r1", "My resume v2");
    expect((await getRun("r1"))?.label).toBe("My resume v2");
  });

  it("renameRun is a no-op for missing id", async () => {
    await renameRun("missing", "x");
    expect(await getRun("missing")).toBeUndefined();
  });

  it("deleteRun removes a run", async () => {
    await saveRun(makeRun("r1", 100));
    await deleteRun("r1");
    expect(await getRun("r1")).toBeUndefined();
  });

  it("clearAllRuns empties the store", async () => {
    await saveRun(makeRun("a", 100));
    await saveRun(makeRun("b", 200));
    await clearAllRuns();
    expect(await listRuns()).toEqual([]);
  });
});
```

- [ ] **Step 2: Run the test (expect failure).** Run: `cd web && npx vitest run src/lib/store.test.ts`. Expected: FAIL — `store.ts` does not exist (module resolution error).
- [ ] **Step 3: Implement `store.ts`.** Create `web/src/lib/store.ts`:

```ts
import { openDB, type IDBPDatabase } from "idb";
import type { RunRecord } from "./schemas";

const DB_NAME = "hiring-agent";
const DB_VERSION = 1;
const STORE = "runs";
const INDEX = "by-createdAt";

let dbPromise: Promise<IDBPDatabase> | null = null;

function getDB(): Promise<IDBPDatabase> {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(STORE)) {
          const store = db.createObjectStore(STORE, { keyPath: "id" });
          store.createIndex(INDEX, "createdAt");
        }
      },
    });
  }
  return dbPromise;
}

export async function saveRun(rec: RunRecord): Promise<void> {
  const db = await getDB();
  await db.put(STORE, rec);
}

export async function listRuns(): Promise<RunRecord[]> {
  const db = await getDB();
  return (await db.getAllFromIndex(STORE, INDEX)) as RunRecord[];
}

export async function getRun(id: string): Promise<RunRecord | undefined> {
  const db = await getDB();
  return (await db.get(STORE, id)) as RunRecord | undefined;
}

export async function deleteRun(id: string): Promise<void> {
  const db = await getDB();
  await db.delete(STORE, id);
}

export async function renameRun(id: string, label: string): Promise<void> {
  const db = await getDB();
  const rec = (await db.get(STORE, id)) as RunRecord | undefined;
  if (!rec) return;
  rec.label = label;
  await db.put(STORE, rec);
}

export async function clearAllRuns(): Promise<void> {
  const db = await getDB();
  await db.clear(STORE);
}
```

- [ ] **Step 4: Run the test (expect pass).** Run: `cd web && npx vitest run src/lib/store.test.ts`. Expected: PASS — all 7 cases green (`getAllFromIndex` yields ascending `createdAt` order).
- [ ] **Step 5: Commit.** Run:

```bash
git add web/src/lib/store.ts web/src/lib/store.test.ts
git commit -m "feat(web): IndexedDB run store with TDD coverage"
```

### Task 4: Settings module (`settings.ts`) — TDD

**Files:**
- Create: `web/src/lib/settings.ts`
- Test: `web/src/lib/settings.test.ts`

- [ ] **Step 1: Write the failing test.** Create `web/src/lib/settings.test.ts` (uses `jsdom` for a real `localStorage`; mocks `./store` so `clearAllData` does not touch IndexedDB):

```ts
// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DEFAULT_MODEL } from "./gemini";
import {
  loadSettings,
  persistSettings,
  toPipelineSettings,
  clearAllData,
} from "./settings";
import { clearAllRuns } from "./store";
import type { StoredSettings } from "./schemas";

vi.mock("./store", () => ({ clearAllRuns: vi.fn(async () => {}) }));

function base(overrides: Partial<StoredSettings> = {}): StoredSettings {
  return {
    geminiKey: "",
    githubToken: "",
    model: DEFAULT_MODEL,
    enableGitHub: false,
    rememberKeys: false,
    ...overrides,
  };
}

beforeEach(() => {
  localStorage.clear();
  // Reset the module-level session object to empty, then clear LS again.
  persistSettings(base());
  localStorage.clear();
  vi.clearAllMocks();
});

describe("settings", () => {
  it("returns defaults when storage is empty", () => {
    expect(loadSettings()).toEqual({
      geminiKey: "",
      githubToken: "",
      model: DEFAULT_MODEL,
      enableGitHub: false,
      rememberKeys: false,
    });
  });

  it("persists keys to localStorage when rememberKeys is true", () => {
    persistSettings(
      base({
        geminiKey: "sk-abc",
        githubToken: "ghp_xyz",
        model: "gemini-2.5-pro",
        enableGitHub: true,
        rememberKeys: true,
      }),
    );
    expect(localStorage.getItem("ha-gemini-key")).toBe("sk-abc");
    expect(localStorage.getItem("ha-github-token")).toBe("ghp_xyz");
    expect(localStorage.getItem("ha-remember-keys")).toBe("true");
    expect(localStorage.getItem("ha-model")).toBe("gemini-2.5-pro");
    expect(localStorage.getItem("ha-enable-github")).toBe("true");
    expect(loadSettings().geminiKey).toBe("sk-abc");
  });

  it("does NOT persist keys when rememberKeys is false but keeps them in session", () => {
    persistSettings(base({ geminiKey: "sk-session", githubToken: "ghp_session", rememberKeys: false }));
    expect(localStorage.getItem("ha-gemini-key")).toBeNull();
    expect(localStorage.getItem("ha-github-token")).toBeNull();
    // Non-key prefs are still written.
    expect(localStorage.getItem("ha-remember-keys")).toBe("false");
    // loadSettings falls back to the in-memory session keys.
    const loaded = loadSettings();
    expect(loaded.geminiKey).toBe("sk-session");
    expect(loaded.githubToken).toBe("ghp_session");
  });

  it("removes previously persisted keys when toggling rememberKeys off", () => {
    persistSettings(base({ geminiKey: "sk-1", githubToken: "ghp_1", rememberKeys: true }));
    expect(localStorage.getItem("ha-gemini-key")).toBe("sk-1");
    persistSettings(base({ geminiKey: "sk-1", githubToken: "ghp_1", rememberKeys: false }));
    expect(localStorage.getItem("ha-gemini-key")).toBeNull();
    expect(localStorage.getItem("ha-github-token")).toBeNull();
    expect(loadSettings().geminiKey).toBe("sk-1");
  });

  it("toPipelineSettings maps empty githubToken to null and passes model/enableGitHub", () => {
    const out = toPipelineSettings(
      base({ geminiKey: "k", githubToken: "", model: "m", enableGitHub: true }),
    );
    expect(out).toEqual({ geminiKey: "k", githubToken: null, model: "m", enableGitHub: true });
  });

  it("toPipelineSettings passes through a non-empty githubToken", () => {
    const out = toPipelineSettings(base({ githubToken: "ghp_z" }));
    expect(out.githubToken).toBe("ghp_z");
  });

  it("clearAllData clears ha-* keys except ha-theme and calls clearAllRuns", async () => {
    localStorage.setItem("ha-theme", "dark");
    persistSettings(base({ geminiKey: "sk", githubToken: "tok", rememberKeys: true }));
    expect(localStorage.getItem("ha-gemini-key")).toBe("sk");

    await clearAllData();

    expect(localStorage.getItem("ha-gemini-key")).toBeNull();
    expect(localStorage.getItem("ha-github-token")).toBeNull();
    expect(localStorage.getItem("ha-remember-keys")).toBeNull();
    expect(localStorage.getItem("ha-theme")).toBe("dark");
    expect(clearAllRuns).toHaveBeenCalledTimes(1);
    // Session keys are reset, so defaults come back.
    expect(loadSettings().geminiKey).toBe("");
  });
});
```

- [ ] **Step 2: Run the test (expect failure).** Run: `cd web && npx vitest run src/lib/settings.test.ts`. Expected: FAIL — `settings.ts` does not exist.
- [ ] **Step 3: Implement `settings.ts`.** Create `web/src/lib/settings.ts`:

```ts
import type { Settings } from "./pipeline";
import type { StoredSettings } from "./schemas";
import { DEFAULT_MODEL } from "./gemini";
import { clearAllRuns } from "./store";

const LS_REMEMBER = "ha-remember-keys";
const LS_GEMINI = "ha-gemini-key";
const LS_GITHUB = "ha-github-token";
const LS_MODEL = "ha-model";
const LS_ENABLE_GH = "ha-enable-github";

// In-memory fallback for secrets when the user opts out of persistence.
const session: { geminiKey: string; githubToken: string } = {
  geminiKey: "",
  githubToken: "",
};

function lsGet(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}
function lsSet(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {}
}
function lsRemove(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch {}
}

export function loadSettings(): StoredSettings {
  const rememberKeys = lsGet(LS_REMEMBER) === "true";
  const model = lsGet(LS_MODEL) ?? DEFAULT_MODEL;
  const enableGitHub = lsGet(LS_ENABLE_GH) === "true";
  const geminiKey = lsGet(LS_GEMINI) ?? session.geminiKey;
  const githubToken = lsGet(LS_GITHUB) ?? session.githubToken;
  return { geminiKey, githubToken, model, enableGitHub, rememberKeys };
}

export function persistSettings(s: StoredSettings): void {
  lsSet(LS_REMEMBER, s.rememberKeys ? "true" : "false");
  lsSet(LS_MODEL, s.model);
  lsSet(LS_ENABLE_GH, s.enableGitHub ? "true" : "false");

  // Keys always live in the session object; they additionally persist to
  // localStorage only when the user opted in.
  session.geminiKey = s.geminiKey;
  session.githubToken = s.githubToken;

  if (s.rememberKeys) {
    lsSet(LS_GEMINI, s.geminiKey);
    lsSet(LS_GITHUB, s.githubToken);
  } else {
    lsRemove(LS_GEMINI);
    lsRemove(LS_GITHUB);
  }
}

export function toPipelineSettings(s: StoredSettings): Settings {
  return {
    geminiKey: s.geminiKey,
    githubToken: s.githubToken === "" ? null : s.githubToken,
    model: s.model,
    enableGitHub: s.enableGitHub,
  };
}

export async function clearAllData(): Promise<void> {
  try {
    const toRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith("ha-") && k !== "ha-theme") toRemove.push(k);
    }
    for (const k of toRemove) localStorage.removeItem(k);
  } catch {}
  session.geminiKey = "";
  session.githubToken = "";
  await clearAllRuns();
}
```

- [ ] **Step 4: Run the test (expect pass).** Run: `cd web && npx vitest run src/lib/settings.test.ts`. Expected: PASS — all cases green.
- [ ] **Step 5: Run the full unit suite as a guard.** Run: `cd web && npm run test`. Expected: PASS — store + settings + existing Part 1 tests all green.
- [ ] **Step 6: Commit.** Run:

```bash
git add web/src/lib/settings.ts web/src/lib/settings.test.ts
git commit -m "feat(web): settings module with localStorage persistence and session fallback"
```

### Task 5: SettingsProvider context + layout wiring

**Files:**
- Create: `web/src/ui/SettingsProvider.tsx`
- Modify: `web/src/app/layout.tsx` (lines 3, 18 — import and provider wrap)

- [ ] **Step 1: Create the context provider.** Create `web/src/ui/SettingsProvider.tsx`:

```tsx
"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { StoredSettings } from "@/lib/schemas";
import { loadSettings, persistSettings } from "@/lib/settings";
import { DEFAULT_MODEL } from "@/lib/gemini";

type SettingsContextValue = {
  settings: StoredSettings;
  update: (patch: Partial<StoredSettings>) => void;
  hasKey: boolean;
};

const DEFAULTS: StoredSettings = {
  geminiKey: "",
  githubToken: "",
  model: DEFAULT_MODEL,
  enableGitHub: false,
  rememberKeys: false,
};

const SettingsContext = createContext<SettingsContextValue>({
  settings: DEFAULTS,
  update: () => {},
  hasKey: false,
});

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<StoredSettings>(DEFAULTS);

  useEffect(() => {
    setSettings(loadSettings());
  }, []);

  const update = useCallback((patch: Partial<StoredSettings>) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      persistSettings(next);
      return next;
    });
  }, []);

  return (
    <SettingsContext.Provider value={{ settings, update, hasKey: settings.geminiKey.length > 0 }}>
      {children}
    </SettingsContext.Provider>
  );
}

export const useSettings = () => useContext(SettingsContext);
```

- [ ] **Step 2: Import the provider in `layout.tsx`.** Add the import beneath the existing `ThemeProvider` import (currently line 3):

```tsx
import { ThemeProvider } from "@/ui/ThemeProvider";
import { SettingsProvider } from "@/ui/SettingsProvider";
```

- [ ] **Step 3: Wrap children with `SettingsProvider` INSIDE `ThemeProvider`.** Replace the body `<ThemeProvider>{children}</ThemeProvider>` (currently line 18):

```tsx
      <body>
        <ThemeProvider>
          <SettingsProvider>{children}</SettingsProvider>
        </ThemeProvider>
      </body>
```

- [ ] **Step 4: Type-check.** Run: `cd web && npx tsc --noEmit`. Expected: PASS.
- [ ] **Step 5: Verify the static export build.** Run: `cd web && npm run build`. Expected: static export succeeds (no SSR errors from the new client provider).
- [ ] **Step 6: Commit.** Run:

```bash
git add web/src/ui/SettingsProvider.tsx web/src/app/layout.tsx
git commit -m "feat(web): SettingsProvider context wired into root layout"
```


## Phase F — Trend & chart math (pure, TDD)

This phase delivers the pure, fully-tested math behind the Trends screen plus a shared status label used across the report and history UIs. It adds `statusLabel(s: Status)` to `scoring.ts` and creates `trends.ts` with the series builders (`totalSeries`, `categorySeries`), aggregate stats (`summaryStats`), and SVG path generators (`buildLinePath`, `buildSparkPath`). Every export is a deterministic pure function with no IndexedDB, DOM, or React dependency, so each is locked down with exact-number Vitest assertions. No UI is touched here — later phases consume these helpers.

### Task 1: Add `statusLabel` to scoring.ts

**Files:**
- Modify: `web/src/lib/scoring.ts` (append after `statusFor`, lines 28-33)
- Test: `web/src/lib/scoring.test.ts` (extend existing suite)

- [ ] **Step 1: Write the failing test.** Append these cases inside the existing `describe("scoring", ...)` block in `web/src/lib/scoring.test.ts`, and add `statusLabel` to the import on line 2.

  Change the import line:
  ```ts
  import { CATEGORY_MAX, computeTotal, statusFor, cappedCategory, statusLabel } from "./scoring";
  ```

  Add before the closing `});` of the describe block:
  ```ts
  it("maps each status to its human label", () => {
    expect(statusLabel("good")).toBe("Strong");
    expect(statusLabel("warn")).toBe("Needs work");
    expect(statusLabel("bad")).toBe("Weak");
  });
  ```

- [ ] **Step 2: Run it — expect FAIL.** Run: `cd web && npx vitest run src/lib/scoring.test.ts`. Expected: FAIL (TypeScript/import error — `statusLabel` is not exported from `./scoring`).

- [ ] **Step 3: Implement the minimal code.** Append to `web/src/lib/scoring.ts` after the `statusFor` function (after line 33):
  ```ts

  export function statusLabel(s: Status): string {
    switch (s) {
      case "good":
        return "Strong";
      case "warn":
        return "Needs work";
      case "bad":
        return "Weak";
    }
  }
  ```

- [ ] **Step 4: Run it — expect PASS.** Run: `cd web && npx vitest run src/lib/scoring.test.ts`. Expected: PASS (all existing cases plus the new label case).

- [ ] **Step 5: Commit.**
  ```bash
  git add web/src/lib/scoring.ts web/src/lib/scoring.test.ts
  git commit -m "feat(web): add statusLabel(status) helper to scoring"
  ```

### Task 2: Create trends.ts (series + stats + path builders)

**Files:**
- Create: `web/src/lib/trends.ts`
- Test: `web/src/lib/trends.test.ts`

- [ ] **Step 1: Write the failing test.** Create `web/src/lib/trends.test.ts` with minimal-but-valid `RunRecord` fixtures and hand-computed expectations. The coordinate math is worked out in comments so the assertions are exact.
  ```ts
  import { describe, it, expect } from "vitest";
  import type { Evaluation, JSONResume, RunRecord } from "./schemas";
  import {
    totalSeries,
    categorySeries,
    summaryStats,
    buildLinePath,
    buildSparkPath,
  } from "./trends";

  function makeEval(parts: {
    open_source: number;
    self_projects: number;
    production: number;
    technical_skills: number;
    bonus?: number;
    deductions?: number;
  }): Evaluation {
    return {
      scores: {
        open_source: { score: parts.open_source, max: 35, evidence: "x" },
        self_projects: { score: parts.self_projects, max: 30, evidence: "x" },
        production: { score: parts.production, max: 25, evidence: "x" },
        technical_skills: { score: parts.technical_skills, max: 10, evidence: "x" },
      },
      bonus_points: { total: parts.bonus ?? 0, breakdown: "" },
      deductions: { total: parts.deductions ?? 0, reasons: "" },
      key_strengths: ["a"],
      areas_for_improvement: ["b"],
    };
  }

  function makeRun(
    id: string,
    createdAt: number,
    ev: Evaluation,
    extra?: Partial<RunRecord>
  ): RunRecord {
    return {
      id,
      createdAt,
      fileName: `${id}.pdf`,
      parsedResume: {} as JSONResume,
      evaluation: ev,
      coach: { verdict: "", fixes: [], boosts: [] },
      ...extra,
    };
  }

  // Totals (capped categories + bonus - deductions, clamped 0..120):
  //   A: 35 + 30 + 25 + 10           = 100
  //   B: 10 + 10 + 10 +  5           =  35
  //   C: 20 + 15 + 10 +  8 + 2 bonus =  55
  const runA = makeRun(
    "a",
    300,
    makeEval({ open_source: 35, self_projects: 30, production: 25, technical_skills: 10 }),
    { label: "Alpha" }
  );
  const runB = makeRun(
    "b",
    100,
    makeEval({ open_source: 10, self_projects: 10, production: 10, technical_skills: 5 })
  );
  const runC = makeRun(
    "c",
    200,
    makeEval({ open_source: 20, self_projects: 15, production: 10, technical_skills: 8, bonus: 2 })
  );
  // Deliberately unsorted input — helpers must sort ascending by createdAt.
  const runs = [runA, runB, runC];

  describe("totalSeries", () => {
    it("returns points sorted ascending by createdAt with label fallback and total", () => {
      expect(totalSeries(runs)).toEqual([
        { id: "b", createdAt: 100, label: "b.pdf", total: 35 },
        { id: "c", createdAt: 200, label: "c.pdf", total: 55 },
        { id: "a", createdAt: 300, label: "Alpha", total: 100 },
      ]);
    });
    it("returns [] for no runs", () => {
      expect(totalSeries([])).toEqual([]);
    });
  });

  describe("categorySeries", () => {
    it("returns capped category values ascending by createdAt", () => {
      expect(categorySeries(runs, "open_source")).toEqual([10, 20, 35]);
      expect(categorySeries(runs, "technical_skills")).toEqual([5, 8, 10]);
    });
    it("returns [] for no runs", () => {
      expect(categorySeries([], "open_source")).toEqual([]);
    });
  });

  describe("summaryStats", () => {
    it("aggregates latest/personalBest/netChange/runCount/first/last", () => {
      // totals ascending: [35, 55, 100]
      expect(summaryStats(runs)).toEqual({
        latest: 100,
        personalBest: 100,
        netChange: 65, // 100 - 35
        runCount: 3,
        firstAt: 100,
        lastAt: 300,
      });
    });
    it("is zero/null-safe on empty", () => {
      expect(summaryStats([])).toEqual({
        latest: 0,
        personalBest: 0,
        netChange: 0,
        runCount: 0,
        firstAt: null,
        lastAt: null,
      });
    });
  });

  describe("buildLinePath", () => {
    it("maps values to evenly spaced points with padded x and maxY-scaled y", () => {
      // w=100 h=100 pad=10 maxY=120; innerW=80 over 2 gaps => step 40 => x: 10,50,90
      // y = h - pad - (v/maxY)*(h-2*pad) = 90 - (v/120)*80
      //   v=0   -> 90
      //   v=60  -> 90 - 40 = 50
      //   v=120 -> 90 - 80 = 10
      const out = buildLinePath([0, 60, 120], { w: 100, h: 100, pad: 10, maxY: 120 });
      expect(out.points).toEqual([
        { x: 10, y: 90 },
        { x: 50, y: 50 },
        { x: 90, y: 10 },
      ]);
      expect(out.line).toBe("M10 90 L50 50 L90 10");
      expect(out.area).toBe("M10 90 L50 50 L90 10 L90 90 L10 90 Z");
    });
    it("centers a single point at w/2", () => {
      // x = 50; y = 90 - (42/120)*80 = 90 - 28 = 62
      const out = buildLinePath([42], { w: 100, h: 100, pad: 10, maxY: 120 });
      expect(out.points).toEqual([{ x: 50, y: 62 }]);
      expect(out.line).toBe("M50 62");
      expect(out.area).toBe("M50 62 L50 90 L50 90 Z");
    });
    it("returns empty strings and [] for no values", () => {
      expect(buildLinePath([], { w: 100, h: 100, pad: 10, maxY: 120 })).toEqual({
        line: "",
        area: "",
        points: [],
      });
    });
  });

  describe("buildSparkPath", () => {
    it("normalizes to min..max with vertical padding", () => {
      // w=100 h=50; min=0 max=10; padY=5; innerH=40
      // x: 0,100 ; y = (h - padY) - ((v-min)/(max-min))*(h-2*padY) = 45 - (v/10)*40
      //   v=0  -> 45 ; v=10 -> 5
      const out = buildSparkPath([0, 10], { w: 100, h: 50 });
      expect(out.line).toBe("M0 45 L100 5");
      expect(out.area).toBe("M0 45 L100 5 L100 50 L0 50 Z");
    });
    it("draws a mid-line for a flat series", () => {
      // min==max => y = h/2 = 25 ; x: 0,50,100
      const out = buildSparkPath([10, 10, 10], { w: 100, h: 50 });
      expect(out.line).toBe("M0 25 L50 25 L100 25");
      expect(out.area).toBe("M0 25 L50 25 L100 25 L100 50 L0 50 Z");
    });
    it("returns empty strings for no values", () => {
      expect(buildSparkPath([], { w: 100, h: 50 })).toEqual({ line: "", area: "" });
    });
  });
  ```

- [ ] **Step 2: Run it — expect FAIL.** Run: `cd web && npx vitest run src/lib/trends.test.ts`. Expected: FAIL (cannot resolve `./trends` — the module does not exist yet).

- [ ] **Step 3: Implement the minimal code.** Create `web/src/lib/trends.ts`:
  ```ts
  /**
   * Pure math for the Trends screen: per-run series, aggregate stats, and SVG
   * path builders. No DOM/IndexedDB/React — everything here is deterministic and
   * unit-tested. Totals/caps come from scoring.ts so trend numbers match the
   * rest of the UI exactly.
   */
  import type { RunRecord, CategoryKey } from "./schemas";
  import { computeTotal, cappedCategory } from "./scoring";

  export type SeriesPoint = {
    id: string;
    createdAt: number;
    label: string;
    total: number;
  };

  function byCreatedAtAsc(runs: RunRecord[]): RunRecord[] {
    return [...runs].sort((a, b) => a.createdAt - b.createdAt);
  }

  // Render path coordinates as clean strings (drop float noise like 49.99999).
  function fmt(n: number): string {
    return Number.isInteger(n) ? String(n) : String(Math.round(n * 1000) / 1000);
  }

  export function totalSeries(runs: RunRecord[]): SeriesPoint[] {
    return byCreatedAtAsc(runs).map((r) => ({
      id: r.id,
      createdAt: r.createdAt,
      label: r.label || r.fileName,
      total: computeTotal(r.evaluation),
    }));
  }

  export function categorySeries(runs: RunRecord[], key: CategoryKey): number[] {
    return byCreatedAtAsc(runs).map((r) => cappedCategory(r.evaluation, key));
  }

  export type TrendSummary = {
    latest: number;
    personalBest: number;
    netChange: number;
    runCount: number;
    firstAt: number | null;
    lastAt: number | null;
  };

  export function summaryStats(runs: RunRecord[]): TrendSummary {
    if (runs.length === 0) {
      return {
        latest: 0,
        personalBest: 0,
        netChange: 0,
        runCount: 0,
        firstAt: null,
        lastAt: null,
      };
    }
    const sorted = byCreatedAtAsc(runs);
    const totals = sorted.map((r) => computeTotal(r.evaluation));
    const first = totals[0];
    const last = totals[totals.length - 1];
    return {
      latest: last,
      personalBest: Math.max(...totals),
      netChange: last - first,
      runCount: sorted.length,
      firstAt: sorted[0].createdAt,
      lastAt: sorted[sorted.length - 1].createdAt,
    };
  }

  export function buildLinePath(
    values: number[],
    opts: { w: number; h: number; pad: number; maxY: number }
  ): { line: string; area: string; points: { x: number; y: number }[] } {
    const { w, h, pad, maxY } = opts;
    if (values.length === 0) return { line: "", area: "", points: [] };

    const innerH = h - 2 * pad;
    const n = values.length;
    const xFor = (i: number): number => (n === 1 ? w / 2 : pad + (i * (w - 2 * pad)) / (n - 1));
    const yFor = (v: number): number => h - pad - (maxY > 0 ? v / maxY : 0) * innerH;

    const points = values.map((v, i) => ({ x: xFor(i), y: yFor(v) }));
    const line = points
      .map((p, i) => `${i === 0 ? "M" : "L"}${fmt(p.x)} ${fmt(p.y)}`)
      .join(" ");

    const baseY = h - pad;
    const first = points[0];
    const last = points[points.length - 1];
    const area = `${line} L${fmt(last.x)} ${fmt(baseY)} L${fmt(first.x)} ${fmt(baseY)} Z`;

    return { line, area, points };
  }

  export function buildSparkPath(
    values: number[],
    opts: { w: number; h: number }
  ): { line: string; area: string } {
    const { w, h } = opts;
    if (values.length === 0) return { line: "", area: "" };

    const padY = h * 0.1;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const n = values.length;
    const xFor = (i: number): number => (n === 1 ? w / 2 : (i * w) / (n - 1));
    const yFor = (v: number): number => {
      if (max === min) return h / 2; // flat series => mid-line
      return h - padY - ((v - min) / (max - min)) * (h - 2 * padY);
    };

    const points = values.map((v, i) => ({ x: xFor(i), y: yFor(v) }));
    const line = points
      .map((p, i) => `${i === 0 ? "M" : "L"}${fmt(p.x)} ${fmt(p.y)}`)
      .join(" ");

    const first = points[0];
    const last = points[points.length - 1];
    const area = `${line} L${fmt(last.x)} ${fmt(h)} L${fmt(first.x)} ${fmt(h)} Z`;

    return { line, area };
  }
  ```

- [ ] **Step 4: Run it — expect PASS.** Run: `cd web && npx vitest run src/lib/trends.test.ts`. Expected: PASS (all `totalSeries`, `categorySeries`, `summaryStats`, `buildLinePath`, `buildSparkPath` cases green).

- [ ] **Step 5: Run the full suite — expect PASS.** Run: `cd web && npm run test`. Expected: PASS (scoring + trends + all existing Part 1 tests; no regressions).

- [ ] **Step 6: Commit.**
  ```bash
  git add web/src/lib/trends.ts web/src/lib/trends.test.ts
  git commit -m "feat(web): add pure trend series + chart path math"
  ```


## Phase G — App shell, navigation & routing

This phase lays the structural skeleton every later screen drops into: a tested `Delta` presentational component, the shared top-bar/nav shell classes in `globals.css`, the `AppShell` component with active-tab state via `next/link`, five placeholder screen stubs, and the five App Router route files (`/`, `/results`, `/diff`, `/history`, `/settings`) configured for static export. The existing dev-harness `page.tsx` is replaced. By the end, `npm run build` produces a green static export emitting all five routes, ready for later phases to fill in each screen. Delta is the only practically unit-testable unit here, so it is built TDD-first; the remaining CSS/component/route work is verified by a successful build.

### Task 1: Delta presentational component (TDD)

**Files:**
- Create: `web/src/ui/Delta.tsx`
- Test: `web/src/ui/Delta.test.tsx`

`Delta` renders a `<span class="delta ...">` whose modifier class and text encode a signed numeric change. Per the shared contract: class `up` when `value>0`, `down` when `value<0`, `flat` when `value===0` or `value===null`; text `"—"` for null, `"▲ +N"` for positive, `"▼ -N"` for negative (using `Math.abs`), `"— 0"` for zero; append `" " + suffix` when `suffix` is provided. The repo's Vitest config uses `environment: "node"` with no jsdom/testing-library, so the test renders to a static HTML string via `react-dom/server`'s `renderToStaticMarkup` and asserts on class + text content.

- [ ] **Step 1: Write the failing test.** Create `web/src/ui/Delta.test.tsx`:

```tsx
import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { Delta } from "./Delta";

describe("Delta", () => {
  it("renders a negative value as down with ▼ and abs magnitude", () => {
    const html = renderToStaticMarkup(<Delta value={-3} />);
    expect(html).toContain("delta");
    expect(html).toContain("down");
    expect(html).toContain("▼ -3");
    expect(html).not.toContain("up");
    expect(html).not.toContain("flat");
  });

  it("renders zero as flat with the '— 0' label", () => {
    const html = renderToStaticMarkup(<Delta value={0} />);
    expect(html).toContain("flat");
    expect(html).toContain("— 0");
  });

  it("renders a positive value as up with ▲ and a plus sign", () => {
    const html = renderToStaticMarkup(<Delta value={5} />);
    expect(html).toContain("up");
    expect(html).toContain("▲ +5");
  });

  it("renders null as flat with an em dash and no number", () => {
    const html = renderToStaticMarkup(<Delta value={null} />);
    expect(html).toContain("flat");
    expect(html).toContain("—");
    expect(html).not.toContain("+");
    expect(html).not.toContain("0");
  });

  it("appends the suffix when provided", () => {
    const html = renderToStaticMarkup(<Delta value={5} suffix="vs prev" />);
    expect(html).toContain("▲ +5 vs prev");
  });
});
```

- [ ] **Step 2: Run the test, expect failure.** Run: `cd web && npx vitest run src/ui/Delta.test.tsx` — Expected: FAIL (module `./Delta` does not exist / `Delta` is not exported).

- [ ] **Step 3: Implement the component.** Create `web/src/ui/Delta.tsx`:

```tsx
export function Delta({ value, suffix }: { value: number | null; suffix?: string }) {
  const cls = value === null ? "flat" : value > 0 ? "up" : value < 0 ? "down" : "flat";
  let text: string;
  if (value === null) text = "—";
  else if (value > 0) text = `▲ +${value}`;
  else if (value < 0) text = `▼ -${Math.abs(value)}`;
  else text = "— 0";
  if (suffix) text += ` ${suffix}`;
  return <span className={`delta ${cls}`}>{text}</span>;
}
```

- [ ] **Step 4: Run the test, expect pass.** Run: `cd web && npx vitest run src/ui/Delta.test.tsx` — Expected: PASS (5 tests).

- [ ] **Step 5: Commit.**

```bash
git add web/src/ui/Delta.tsx web/src/ui/Delta.test.tsx
git commit -m "feat(web): add Delta component with TDD coverage"
```

### Task 2: Shared shell classes in globals.css

**Files:**
- Modify: `web/src/app/globals.css` (append after line 40, before/after the final `@media` block)

Add only shell-level shared classes adapted from the mockup `.top` structure in `results-direction-v5.html` (lines 36–43): `.wrap`, `.top`, `.mark` (+ `.mark b`), `.nav`, `.nav a`, `.nav .on`. The `.chip`, `.dot`, `.delta`, `.up/.down/.flat`, `.eyebrow`, `.serif`, `.mono` classes already exist in `globals.css` (lines 26–38) and the theme-toggle styles live in `ThemeToggle.tsx` — do not duplicate them. Nav items are `next/link` anchors, so `.nav a` needs `text-decoration:none` and inherited sizing; the active link gets `.on`.

- [ ] **Step 1: Append the shell classes.** Edit `web/src/app/globals.css`, inserting the following block immediately before the final `@media (prefers-reduced-motion: reduce){ body{transition:none} }` line:

```css
/* app shell */
.wrap{max-width:1080px; margin:0 auto; padding:26px 28px 60px}
.top{display:flex; align-items:center; justify-content:space-between;
  padding-bottom:20px; border-bottom:1px solid var(--rule)}
.mark{font-family:var(--font-instrument-serif),serif; font-size:26px; letter-spacing:.2px}
.mark b{font-style:italic; font-weight:400}
.nav{display:flex; gap:20px; align-items:center; font-size:13px; color:var(--ink-soft)}
.nav a{color:var(--ink-soft); text-decoration:none}
.nav a:hover{color:var(--ink)}
.nav a:focus-visible{outline:2px solid var(--brand); outline-offset:3px; border-radius:4px}
.nav .on{color:var(--ink); font-weight:600}
@media(max-width:760px){ .nav{gap:14px} }
```

- [ ] **Step 2: Build-verify.** Run: `cd web && npm run build` — Expected: static export succeeds (CSS is valid, no build errors).

- [ ] **Step 3: Commit.**

```bash
git add web/src/app/globals.css
git commit -m "feat(web): add shared app-shell classes to globals.css"
```

### Task 3: AppShell component

**Files:**
- Create: `web/src/ui/AppShell.tsx`

`AppShell({active, children})` renders the top bar mirroring the mockup `.top` structure (lines 165–178 of `results-direction-v5.html`): the serif mark `Hiring <b>Agent</b>`, a `.nav` with three `next/link` links (Score → `/`, "History & Trends" → `/history`, Settings → `/settings`) where the link matching `active` gets the `.on` class, followed by `<ThemeToggle/>` and `<PrivacyChip/>`; then `<main>{children}</main>` — a single `.wrap` container wraps the whole shell (top bar + content), so `main` itself takes no class (avoids a doubled max-width container). Per the contract, `active` is `"score" | "history" | "settings"`, and the results/diff routes pass `active="score"`. Imports use the real exports from `@/ui/ThemeToggle` and `@/ui/PrivacyChip`. No unit test (no extracted pure helper); verified by build.

- [ ] **Step 1: Implement AppShell.** Create `web/src/ui/AppShell.tsx`:

```tsx
"use client";
import Link from "next/link";
import { ThemeToggle } from "@/ui/ThemeToggle";
import { PrivacyChip } from "@/ui/PrivacyChip";

export function AppShell({
  active,
  children,
}: {
  active: "score" | "history" | "settings";
  children: React.ReactNode;
}) {
  return (
    <div className="wrap">
      <div className="top">
        <div className="mark serif">
          Hiring <b>Agent</b>
        </div>
        <div className="nav">
          <Link href="/" className={active === "score" ? "on" : undefined}>
            Score
          </Link>
          <Link href="/history" className={active === "history" ? "on" : undefined}>
            History &amp; Trends
          </Link>
          <Link href="/settings" className={active === "settings" ? "on" : undefined}>
            Settings
          </Link>
          <ThemeToggle />
          <PrivacyChip />
        </div>
      </div>
      <main>{children}</main>
    </div>
  );
}
```

- [ ] **Step 2: Build-verify.** Run: `cd web && npm run build` — Expected: static export succeeds (note: a route still renders the old dev harness; that is replaced in Task 5, so a successful build here only proves AppShell type-checks. It is not yet imported by any route).

- [ ] **Step 3: Commit.**

```bash
git add web/src/ui/AppShell.tsx
git commit -m "feat(web): add AppShell top bar and tab navigation"
```

### Task 4: Screen placeholder stubs

**Files:**
- Create: `web/src/ui/screens/ScoreScreen.tsx`
- Create: `web/src/ui/screens/ResultsScreen.tsx`
- Create: `web/src/ui/screens/DiffScreen.tsx`
- Create: `web/src/ui/screens/HistoryScreen.tsx`
- Create: `web/src/ui/screens/SettingsScreen.tsx`

Each screen is a thin `"use client"` placeholder returning a single `.eyebrow` line naming the screen, so the routes compile. Later phases replace each body. No unit tests (no pure helpers); verified by build.

- [ ] **Step 1: Create ScoreScreen stub.** Create `web/src/ui/screens/ScoreScreen.tsx`:

```tsx
"use client";

export function ScoreScreen() {
  return <p className="eyebrow">Score screen</p>;
}
```

- [ ] **Step 2: Create ResultsScreen stub.** Create `web/src/ui/screens/ResultsScreen.tsx`:

```tsx
"use client";

export function ResultsScreen() {
  return <p className="eyebrow">Results screen</p>;
}
```

- [ ] **Step 3: Create DiffScreen stub.** Create `web/src/ui/screens/DiffScreen.tsx`:

```tsx
"use client";

export function DiffScreen() {
  return <p className="eyebrow">Diff screen</p>;
}
```

- [ ] **Step 4: Create HistoryScreen stub.** Create `web/src/ui/screens/HistoryScreen.tsx`:

```tsx
"use client";

export function HistoryScreen() {
  return <p className="eyebrow">History &amp; Trends screen</p>;
}
```

- [ ] **Step 5: Create SettingsScreen stub.** Create `web/src/ui/screens/SettingsScreen.tsx`:

```tsx
"use client";

export function SettingsScreen() {
  return <p className="eyebrow">Settings screen</p>;
}
```

- [ ] **Step 6: Build-verify.** Run: `cd web && npm run build` — Expected: static export succeeds (stubs type-check; not yet imported by routes).

- [ ] **Step 7: Commit.**

```bash
git add web/src/ui/screens/ScoreScreen.tsx web/src/ui/screens/ResultsScreen.tsx web/src/ui/screens/DiffScreen.tsx web/src/ui/screens/HistoryScreen.tsx web/src/ui/screens/SettingsScreen.tsx
git commit -m "feat(web): add placeholder screen stubs for routing"
```

### Task 5: Route files (replace dev harness, wire AppShell + screens)

**Files:**
- Modify (replace entirely): `web/src/app/page.tsx`
- Create: `web/src/app/results/page.tsx`
- Create: `web/src/app/diff/page.tsx`
- Create: `web/src/app/history/page.tsx`
- Create: `web/src/app/settings/page.tsx`

Each route file is a thin `"use client"` wrapper rendering `<AppShell active=...>{<Screen/>}</AppShell>`. The `/` route uses `active="score"` with `ScoreScreen` and replaces the existing dev harness. `/results` wraps `ResultsScreen` in `<Suspense>` (it reads `useSearchParams` in a later phase) with `active="score"`. `/diff` uses `DiffScreen` with `active="score"`. `/history` uses `HistoryScreen` with `active="history"`. `/settings` uses `SettingsScreen` with `active="settings"`. With `next.config` `output: "export"`, the build emits `/`, `/results`, `/diff`, `/history`, `/settings`. Verified by build.

- [ ] **Step 1: Replace the dev-harness page.tsx with the Score route.** Overwrite `web/src/app/page.tsx` entirely:

```tsx
"use client";
import { AppShell } from "@/ui/AppShell";
import { ScoreScreen } from "@/ui/screens/ScoreScreen";

export default function Page() {
  return (
    <AppShell active="score">
      <ScoreScreen />
    </AppShell>
  );
}
```

- [ ] **Step 2: Create the Results route.** Create `web/src/app/results/page.tsx`:

```tsx
"use client";
import { Suspense } from "react";
import { AppShell } from "@/ui/AppShell";
import { ResultsScreen } from "@/ui/screens/ResultsScreen";

export default function Page() {
  return (
    <AppShell active="score">
      <Suspense fallback={<p className="eyebrow">Loading…</p>}>
        <ResultsScreen />
      </Suspense>
    </AppShell>
  );
}
```

- [ ] **Step 3: Create the Diff route.** Create `web/src/app/diff/page.tsx`:

```tsx
"use client";
import { Suspense } from "react";
import { AppShell } from "@/ui/AppShell";
import { DiffScreen } from "@/ui/screens/DiffScreen";

export default function Page() {
  return (
    <AppShell active="score">
      <Suspense fallback={<p className="eyebrow">Loading…</p>}>
        <DiffScreen />
      </Suspense>
    </AppShell>
  );
}
```

- [ ] **Step 4: Create the History route.** Create `web/src/app/history/page.tsx`:

```tsx
"use client";
import { AppShell } from "@/ui/AppShell";
import { HistoryScreen } from "@/ui/screens/HistoryScreen";

export default function Page() {
  return (
    <AppShell active="history">
      <HistoryScreen />
    </AppShell>
  );
}
```

- [ ] **Step 5: Create the Settings route.** Create `web/src/app/settings/page.tsx`:

```tsx
"use client";
import { AppShell } from "@/ui/AppShell";
import { SettingsScreen } from "@/ui/screens/SettingsScreen";

export default function Page() {
  return (
    <AppShell active="settings">
      <SettingsScreen />
    </AppShell>
  );
}
```

- [ ] **Step 6: Build-verify the full static export.** Run: `cd web && npm run build` — Expected: static export succeeds and the route list includes `/`, `/results`, `/diff`, `/history`, `/settings` (each emitted as a static page).

- [ ] **Step 7: Run the full unit suite to confirm nothing regressed.** Run: `cd web && npm run test` — Expected: PASS (existing lib tests + the new `Delta.test.tsx`).

- [ ] **Step 8: Commit.**

```bash
git add web/src/app/page.tsx web/src/app/results/page.tsx web/src/app/diff/page.tsx web/src/app/history/page.tsx web/src/app/settings/page.tsx
git commit -m "feat(web): add routes wiring AppShell and screen stubs"
```


## Phase H — Score screen (upload, pipeline, progress, errors)

This phase replaces the placeholder `ScoreScreen` stub with the real upload-and-score experience: a drag-and-drop PDF dropzone, a gated "no key" notice that links to Settings, a live vertical progress list driven by the pipeline's `onProgress` stages, friendly error mapping, persistence of the resulting `RunRecord` (with its source `pdfBlob`) to IndexedDB, and a redirect to the results route. It introduces one pure, fully-TDD helper (`errorMessage`), one styled presentational component (`Dropzone`), and the wired screen itself. All work imports the already-built Part 1 engine (`runScoreWithRealDeps`), store (`saveRun`), settings (`toPipelineSettings`, `useSettings`), and error classes — nothing is recreated.

### Task 1: `errorMessage` pure helper (TDD)

**Files:**
- Create: `web/src/lib/errorMessage.ts`
- Test: `web/src/lib/errorMessage.test.ts`

- [ ] **Step 1: Write the failing test.** Create `web/src/lib/errorMessage.test.ts`:
  ```ts
  import { describe, it, expect } from "vitest";
  import { errorMessage } from "./errorMessage";
  import {
    MissingKeyError,
    NoTextError,
    RateLimitError,
    ModelOutputError,
  } from "./errors";

  describe("errorMessage", () => {
    it("maps MissingKeyError to a Settings hint", () => {
      expect(errorMessage(new MissingKeyError())).toBe(
        "Add your Gemini API key in Settings before scoring.",
      );
    });

    it("maps NoTextError to an image-only-PDF hint", () => {
      expect(errorMessage(new NoTextError())).toBe(
        "This PDF has no selectable text. Image-only or scanned PDFs aren't supported — export a text PDF and try again.",
      );
    });

    it("maps RateLimitError to a slow-down hint", () => {
      expect(errorMessage(new RateLimitError())).toBe(
        "Gemini is rate-limiting requests. Wait a moment and try again.",
      );
    });

    it("maps ModelOutputError to an invalid-output hint", () => {
      expect(errorMessage(new ModelOutputError("{bad"))).toBe(
        "The model returned output we couldn't read. Try again — this is usually transient.",
      );
    });

    it("falls back to a generic Error's message when present", () => {
      expect(errorMessage(new Error("boom"))).toBe("boom");
    });

    it("uses a generic fallback for an empty Error message", () => {
      expect(errorMessage(new Error(""))).toBe("Something went wrong. Please try again.");
    });

    it("uses a generic fallback for non-Error values", () => {
      expect(errorMessage("nope")).toBe("Something went wrong. Please try again.");
      expect(errorMessage(undefined)).toBe("Something went wrong. Please try again.");
    });
  });
  ```

- [ ] **Step 2: Run the test (expect FAIL).** Run: `cd web && npx vitest run src/lib/errorMessage.test.ts` — Expected: FAIL (module `./errorMessage` does not exist / `errorMessage` is not exported).

- [ ] **Step 3: Implement the helper.** Create `web/src/lib/errorMessage.ts`:
  ```ts
  import {
    MissingKeyError,
    NoTextError,
    RateLimitError,
    ModelOutputError,
  } from "./errors";

  const GENERIC = "Something went wrong. Please try again.";

  /** Map any thrown value to user-facing copy for the Score screen. PURE. */
  export function errorMessage(err: unknown): string {
    if (err instanceof MissingKeyError) {
      return "Add your Gemini API key in Settings before scoring.";
    }
    if (err instanceof NoTextError) {
      return "This PDF has no selectable text. Image-only or scanned PDFs aren't supported — export a text PDF and try again.";
    }
    if (err instanceof RateLimitError) {
      return "Gemini is rate-limiting requests. Wait a moment and try again.";
    }
    if (err instanceof ModelOutputError) {
      return "The model returned output we couldn't read. Try again — this is usually transient.";
    }
    if (err instanceof Error && err.message.trim().length > 0) {
      return err.message;
    }
    return GENERIC;
  }
  ```

- [ ] **Step 4: Run the test (expect PASS).** Run: `cd web && npx vitest run src/lib/errorMessage.test.ts` — Expected: PASS (7 assertions green).

- [ ] **Step 5: Commit.** Run: `cd web && git add src/lib/errorMessage.ts src/lib/errorMessage.test.ts && git commit -m "feat(web): errorMessage helper maps pipeline errors to friendly copy"`

### Task 2: `Dropzone` component

**Files:**
- Create: `web/src/ui/Dropzone.tsx`

- [ ] **Step 1: Write the component.** Create `web/src/ui/Dropzone.tsx` (drag-and-drop + click-to-pick PDF input, `accept="application/pdf"`, scoped `<style>`, calls `onFile(file)`):
  ```tsx
  "use client";
  import { useRef, useState } from "react";

  function firstPdf(list: FileList | null): File | null {
    if (!list) return null;
    for (const f of Array.from(list)) {
      if (f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")) return f;
    }
    return null;
  }

  export function Dropzone({
    onFile,
    disabled = false,
  }: {
    onFile: (file: File) => void;
    disabled?: boolean;
  }) {
    const inputRef = useRef<HTMLInputElement>(null);
    const [over, setOver] = useState(false);

    function pick() {
      if (!disabled) inputRef.current?.click();
    }

    function onDrop(e: React.DragEvent) {
      e.preventDefault();
      setOver(false);
      if (disabled) return;
      const file = firstPdf(e.dataTransfer.files);
      if (file) onFile(file);
    }

    return (
      <div
        className={`ha-dz${over ? " over" : ""}${disabled ? " off" : ""}`}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled}
        aria-label="Upload a resume PDF"
        onClick={pick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            pick();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={onDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          hidden
          onChange={(e) => {
            const file = firstPdf(e.target.files);
            if (file) onFile(file);
            e.target.value = "";
          }}
        />
        <svg className="ha-dz-ico" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 16V4M7 9l5-5 5 5" />
          <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
        </svg>
        <div className="ha-dz-title serif">Drop your resume PDF</div>
        <div className="ha-dz-sub mono">or click to browse · stays in your browser</div>
        <style>{`
          .ha-dz{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;
            min-height:240px;padding:40px 24px;border:1.5px dashed var(--rule);border-radius:16px;
            background:var(--panel);color:var(--ink-soft);cursor:pointer;text-align:center;
            transition:border-color .18s ease,background .18s ease,transform .18s ease}
          .ha-dz:hover{border-color:var(--brand);background:var(--brand-tint)}
          .ha-dz.over{border-color:var(--brand);background:var(--brand-tint);transform:scale(1.005)}
          .ha-dz:focus-visible{outline:2px solid var(--brand);outline-offset:3px}
          .ha-dz.off{cursor:not-allowed;opacity:.55}
          .ha-dz.off:hover{border-color:var(--rule);background:var(--panel);transform:none}
          .ha-dz-ico{width:34px;height:34px;color:var(--brand-ink)}
          .ha-dz-title{font-size:22px;color:var(--ink)}
          .ha-dz-sub{font-size:12px;color:var(--ink-soft)}
          @media (prefers-reduced-motion: reduce){ .ha-dz{transition:none} .ha-dz.over{transform:none} }
        `}</style>
      </div>
    );
  }
  ```

- [ ] **Step 2: Build-verify.** Run: `cd web && npm run build` — Expected: static export succeeds (no type errors; `Dropzone` compiles).

- [ ] **Step 3: Commit.** Run: `cd web && git add src/ui/Dropzone.tsx && git commit -m "feat(web): drag-and-drop PDF Dropzone component"`

### Task 3: Wire the real `ScoreScreen`

**Files:**
- Modify (replace stub): `web/src/ui/screens/ScoreScreen.tsx`

- [ ] **Step 1: Replace the screen.** Overwrite `web/src/ui/screens/ScoreScreen.tsx` with the real implementation. It gates on `hasKey`, renders the `Dropzone`, drives the staged progress list via `setStage`, persists the run (`pdfBlob` attached) with `saveRun`, and redirects to `/results?run=<id>`:
  ```tsx
  "use client";
  import { useState } from "react";
  import Link from "next/link";
  import { useRouter } from "next/navigation";
  import { Dropzone } from "@/ui/Dropzone";
  import { useSettings } from "@/ui/SettingsProvider";
  import { toPipelineSettings } from "@/lib/settings";
  import { runScoreWithRealDeps } from "@/lib/runScore";
  import { saveRun } from "@/lib/store";
  import { errorMessage } from "@/lib/errorMessage";

  const STAGES = [
    "Reading PDF",
    "Extracting resume",
    "Enriching from GitHub",
    "Scoring",
    "Coaching",
  ] as const;

  export function ScoreScreen() {
    const router = useRouter();
    const { settings, hasKey } = useSettings();
    const [stage, setStage] = useState<string | null>(null);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function handleFile(file: File) {
      setError(null);
      setBusy(true);
      setStage(STAGES[0]);
      try {
        const run = await runScoreWithRealDeps(
          file,
          toPipelineSettings(settings),
          setStage,
        );
        run.pdfBlob = file;
        await saveRun(run);
        router.push("/results?run=" + run.id);
      } catch (err) {
        setError(errorMessage(err));
        setStage(null);
        setBusy(false);
      }
    }

    if (!hasKey) {
      return (
        <section className="ha-score">
          <p className="eyebrow">Score a resume</p>
          <h1 className="serif ha-score-h1">Add your key to begin</h1>
          <div className="ha-notice" role="note">
            <p>
              You need a Gemini API key before scoring. Everything runs in your
              browser — your key and resume never leave this device.
            </p>
            <Link href="/settings" className="ha-notice-link mono">
              Go to Settings →
            </Link>
          </div>
          <style>{styles}</style>
        </section>
      );
    }

    const activeIdx = stage ? STAGES.indexOf(stage as (typeof STAGES)[number]) : -1;

    return (
      <section className="ha-score">
        <p className="eyebrow">Score a resume</p>
        <h1 className="serif ha-score-h1">Drop a resume, get an honest read</h1>

        <Dropzone onFile={handleFile} disabled={busy} />

        {error && (
          <div className="ha-error mono" role="alert">
            {error}
          </div>
        )}

        {busy && (
          <ol className="ha-stages" aria-live="polite">
            {STAGES.map((s, i) => {
              const state =
                i < activeIdx ? "done" : i === activeIdx ? "active" : "pending";
              return (
                <li key={s} className={`ha-stage ${state}`}>
                  <span className="ha-stage-dot" aria-hidden="true" />
                  <span className="mono">{s}</span>
                </li>
              );
            })}
          </ol>
        )}

        <style>{styles}</style>
      </section>
    );
  }

  const styles = `
    .ha-score{max-width:680px;margin:0 auto}
    .ha-score-h1{font-size:34px;line-height:1.1;margin:6px 0 22px;color:var(--ink)}
    .ha-notice{border:1px solid var(--rule);border-radius:12px;background:var(--panel-2);
      padding:20px 22px;display:flex;flex-direction:column;gap:14px}
    .ha-notice p{margin:0;color:var(--ink-soft);font-size:15px;line-height:1.5}
    .ha-notice-link{align-self:flex-start;font-size:13px;font-weight:600;color:var(--brand-ink);
      text-decoration:none;border-bottom:1px solid var(--brand);padding-bottom:1px}
    .ha-notice-link:focus-visible{outline:2px solid var(--brand);outline-offset:3px}
    .ha-error{margin-top:18px;border:1px solid var(--bad);border-radius:10px;
      background:var(--bad-tint);color:var(--ink);padding:12px 14px;font-size:13px}
    .ha-stages{list-style:none;margin:24px 0 0;padding:0;display:flex;flex-direction:column;gap:2px}
    .ha-stage{display:flex;align-items:center;gap:12px;padding:9px 4px;font-size:13px;color:var(--ink-soft)}
    .ha-stage-dot{width:10px;height:10px;border-radius:50%;flex:none;
      border:2px solid var(--rule);background:transparent;transition:background .2s ease,border-color .2s ease}
    .ha-stage.done{color:var(--ink-soft)}
    .ha-stage.done .ha-stage-dot{background:var(--good);border-color:var(--good)}
    .ha-stage.active{color:var(--ink);font-weight:600}
    .ha-stage.active .ha-stage-dot{background:var(--brand);border-color:var(--brand);
      box-shadow:0 0 0 4px var(--brand-tint);animation:ha-pulse 1.1s ease-in-out infinite}
    @keyframes ha-pulse{0%,100%{opacity:1}50%{opacity:.45}}
    @media (prefers-reduced-motion: reduce){ .ha-stage.active .ha-stage-dot{animation:none} }
  `;
  ```

- [ ] **Step 2: Build-verify.** Run: `cd web && npm run build` — Expected: static export succeeds. (Confirms `useSettings`, `toPipelineSettings`, `saveRun`, `runScoreWithRealDeps`, `errorMessage`, and `Dropzone` all resolve and the screen type-checks. `RunRecord.pdfBlob` is the optional `Blob` field added in schemas; assigning a `File` is valid since `File extends Blob`.)

- [ ] **Step 3: Run the unit suite (regression check).** Run: `cd web && npm test` — Expected: PASS (existing suite + `errorMessage.test.ts` all green; no screen-level unit tests — covered by the Phase L Playwright smoke).

- [ ] **Step 4: Commit.** Run: `cd web && git add src/ui/screens/ScoreScreen.tsx && git commit -m "feat(web): real Score screen with upload, staged progress, and error handling"`


## Phase I — Results screen + revision rail + coach + diff

This phase turns the stub Results and Diff routes into the real editorial scorecard from `results-direction-v5.html`. It delivers three reusable presentational components — `CategoryRow` (one scored category line with bar + status + delta), `RevisionRail` (the signature commit-log of past runs with per-run deltas and a diff link), and `CoachSection` (the "biggest score left on the table" fixes plus "small boosts") — then assembles them in a replaced `ResultsScreen` (two-column `[rail | report]` grid driven by `?run=<id>`, with previous-run lookup + `diffRuns` deltas) and a compact `DiffScreen` (`?a&b`). All screen-specific CSS lives in scoped `<style>` blocks; everything imports the real Part 1 helpers (`cappedCategory`, `CATEGORY_MAX`, `statusFor`, `statusLabel`, `computeTotal`, `diffRuns`, store accessors, `Delta`). These are presentational components covered by the Phase L Playwright smoke; verification here is `npm run build`.

### Task 1: CategoryRow component

**Files:**
- Create: `web/src/ui/CategoryRow.tsx`

- [ ] **Step 1: Write the component.** Full code below. Props are exactly `{ ckey: CategoryKey; ev: Evaluation; delta: number | null }`. Status is derived from `statusFor(cappedCategory, CATEGORY_MAX[ckey])`; bar width is `Math.round(capped / CATEGORY_MAX[ckey] * 100)`; fill class is `b-${status}`, status-word class is `s-${status}`, word text is `statusLabel(status)`. The scoped style is adapted from the `.cat` block in the mockup (the `.delta` / `.up` / `.down` / `.flat` colors are global utility classes from `globals.css`, so only the layout/`.cat-right .delta` rule is local).

```tsx
"use client";
import type { CategoryKey, Evaluation } from "@/lib/schemas";
import { cappedCategory, CATEGORY_MAX, statusFor, statusLabel } from "@/lib/scoring";
import { Delta } from "@/ui/Delta";

export function CategoryRow({ ckey, ev, delta }: { ckey: CategoryKey; ev: Evaluation; delta: number | null }) {
  const max = CATEGORY_MAX[ckey];
  const capped = cappedCategory(ev, ckey);
  const status = statusFor(capped, max);
  const width = Math.round((capped / max) * 100);

  return (
    <div className="cat">
      <div>
        <div className="cat-name mono">{ckey.toUpperCase()}</div>
        <div className="cat-ev">{ev.scores[ckey].evidence}</div>
        <div className="track">
          <div className={`fill b-${status}`} style={{ width: `${width}%` }} />
        </div>
      </div>
      <div className="cat-right">
        <span className="cat-score mono">
          {capped}
          <small>/{max}</small>
        </span>
        <span className={`status mono s-${status}`}>{statusLabel(status)}</span>
        <Delta value={delta} />
      </div>
      <style>{`
        .cat{display:grid;grid-template-columns:1fr 150px;gap:18px;align-items:center;padding:16px 2px;border-top:1px solid var(--rule)}
        .cat:first-child{border-top:none}
        .cat-name{font-size:12px;letter-spacing:.06em;font-weight:500}
        .cat-ev{color:var(--ink-soft);font-size:13px;margin-top:3px;max-width:46ch}
        .track{height:8px;border-radius:6px;background:var(--rule);overflow:hidden;margin-top:10px}
        .fill{height:100%;border-radius:6px}
        .b-good{background:var(--good)} .b-warn{background:var(--warn)} .b-bad{background:var(--bad)}
        .cat-right{text-align:right}
        .cat-score{font-weight:700;font-size:16px}
        .cat-score small{color:var(--ink-soft);font-weight:500}
        .status{font-size:11px;letter-spacing:.05em;text-transform:uppercase;display:block;margin-top:2px}
        .s-good{color:var(--good)} .s-warn{color:var(--warn)} .s-bad{color:var(--bad)}
        .cat-right .delta{display:block;margin-top:4px}
      `}</style>
    </div>
  );
}
```

- [ ] **Step 2: Build-verify.** Run: `cd web && npm run build` — Expected: static export succeeds (the new file typechecks even though nothing imports it yet).
- [ ] **Step 3: Commit.** Run: `cd web && git add src/ui/CategoryRow.tsx && git commit -m "feat(web): CategoryRow scored category line with bar, status, delta"`

### Task 2: RevisionRail component

**Files:**
- Create: `web/src/ui/RevisionRail.tsx`

- [ ] **Step 1: Write the component.** Full code below. Props are exactly `{ runs: RunRecord[]; currentId: string }`. It sorts a local copy ascending by `createdAt`, computes each run's `computeTotal` and its delta versus the chronologically-previous run, then renders newest-first (reversed) as the `.runs` commit log. The current run gets `.cur`; only the current run (when it has a previous) shows the dashed `.compare` diff link to `/diff?a=<currentId>&b=<prevId>`. Date formatting is an inline pure formatter (not exported, so no separate unit test). `.delta` / `.up` / `.down` / `.flat` come from global utilities; `Delta` supplies the arrow + number and we append the `<total>/120` as a `.soft` span.

```tsx
"use client";
import Link from "next/link";
import type { RunRecord } from "@/lib/schemas";
import { computeTotal, MAX_TOTAL } from "@/lib/scoring";
import { Delta } from "@/ui/Delta";

function fmtDate(ms: number): string {
  const d = new Date(ms);
  const now = new Date();
  const time = d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", hour12: false });
  const sameDay =
    d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
  const day = sameDay ? "today" : d.toLocaleDateString(undefined, { month: "short", day: "2-digit" });
  return `${day} · ${time}`;
}

export function RevisionRail({ runs, currentId }: { runs: RunRecord[]; currentId: string }) {
  const ascending = [...runs].sort((a, b) => a.createdAt - b.createdAt);
  const rows = ascending.map((run, i) => {
    const prev = i > 0 ? ascending[i - 1] : null;
    const total = computeTotal(run.evaluation);
    const delta = prev ? total - computeTotal(prev.evaluation) : null;
    return { run, prev, total, delta };
  });

  return (
    <aside className="rail">
      <div className="eyebrow">Revisions</div>
      <div className="runs">
        {[...rows].reverse().map(({ run, prev, total, delta }) => {
          const isCur = run.id === currentId;
          return (
            <div key={run.id} className={isCur ? "run cur" : "run"}>
              <div className="run-v mono">{run.label || run.fileName}</div>
              <div className="run-meta mono">{fmtDate(run.createdAt)}</div>
              <div className="run-delta">
                <Delta value={delta} />
                <span className="soft mono">
                  &nbsp;{total}/{MAX_TOTAL}
                </span>
              </div>
              {isCur && prev && (
                <Link className="compare mono" href={`/diff?a=${run.id}&b=${prev.id}`}>
                  ⇄ diff
                </Link>
              )}
            </div>
          );
        })}
      </div>
      <style>{`
        .rail .eyebrow{margin-bottom:16px}
        .runs{position:relative;padding-left:18px}
        .runs:before{content:"";position:absolute;left:4px;top:6px;bottom:14px;width:2px;background:var(--rule)}
        .run{position:relative;padding:0 0 18px 4px}
        .run:before{content:"";position:absolute;left:-18px;top:4px;width:9px;height:9px;border-radius:50%;background:var(--paper);border:2px solid var(--ink-soft)}
        .run.cur:before{background:var(--brand);border-color:var(--brand);box-shadow:0 0 0 4px var(--brand-tint)}
        .run-v{font-weight:500;font-size:13px}
        .run.cur .run-v{color:var(--brand-ink)}
        .run-meta{font-size:11px;color:var(--ink-soft);margin-top:1px}
        .run-delta{margin-top:2px;font-size:11px}
        .soft{color:var(--ink-soft);font-weight:500}
        .compare{display:inline-block;margin-top:6px;font-size:11px;color:var(--brand-ink);border:1px dashed var(--brand);border-radius:7px;padding:7px 9px;background:var(--brand-tint);text-decoration:none}
        .compare:focus-visible{outline:2px solid var(--brand);outline-offset:2px}
        @media(max-width:760px){ .runs:before{display:none} }
      `}</style>
    </aside>
  );
}
```

- [ ] **Step 2: Build-verify.** Run: `cd web && npm run build` — Expected: static export succeeds.
- [ ] **Step 3: Commit.** Run: `cd web && git add src/ui/RevisionRail.tsx && git commit -m "feat(web): RevisionRail commit-log rail with per-run deltas and diff link"`

### Task 3: CoachSection component

**Files:**
- Create: `web/src/ui/CoachSection.tsx`

- [ ] **Step 1: Write the component.** Full code below. Props are exactly `{ coach: Coach; evaluation: Evaluation }`. The fixes render the "Biggest score left on the table" block: each `.fix` row's `--accent` is the **boosted category's status color** — `var(--${statusFor(cappedCategory(evaluation, fix.category), CATEGORY_MAX[fix.category])})` (good→`--good`, warn→`--warn`, bad→`--bad`) — matching the mockup where weak categories accent in clay/ochre and strong ones in emerald. Then the meta line `Priority 0N · boosts <CATEGORY>` with the category bolded, the serif `.fix-title`, the `.fix-text` detail, and the gain as `<Delta value={fix.estGain} />`. The boosts render the compact "Small boosts" block: `.boost-tag` is `category.toUpperCase()`, `.boost-text` is the text, gain is `<Delta value={b.estGain} />`. Priority is zero-padded to two digits.

```tsx
"use client";
import type { Coach, Evaluation } from "@/lib/schemas";
import { cappedCategory, CATEGORY_MAX, statusFor } from "@/lib/scoring";
import { Delta } from "@/ui/Delta";

export function CoachSection({ coach, evaluation }: { coach: Coach; evaluation: Evaluation }) {
  return (
    <section className="coach">
      <div className="eyebrow">Coach · what to fix next</div>
      <h2 className="coach-sub serif">Biggest score left on the table</h2>
      <p className="coach-note">High-impact fixes, in priority order.</p>

      {coach.fixes.map((fix, i) => (
        <div
          className="fix"
          key={i}
          style={{
            ["--accent" as string]: `var(--${statusFor(cappedCategory(evaluation, fix.category), CATEGORY_MAX[fix.category])})`,
          }}
        >
          <div className="fix-rule" />
          <div>
            <div className="fix-meta mono">
              Priority {String(fix.priority).padStart(2, "0")} · boosts <b>{fix.category.toUpperCase()}</b>
            </div>
            <h3 className="fix-title serif">{fix.title}</h3>
            <p className="fix-text">{fix.detail}</p>
          </div>
          <div className="gain">
            <Delta value={fix.estGain} />
          </div>
        </div>
      ))}

      {coach.boosts.length > 0 && (
        <div className="boosts">
          <h2 className="coach-sub serif">Small boosts</h2>
          <p className="coach-note">Polish for categories that are already strong — a point or two each.</p>
          {coach.boosts.map((b, i) => (
            <div className="boost" key={i}>
              <span className="boost-tag mono">{b.category.toUpperCase()}</span>
              <span className="boost-text serif">{b.text}</span>
              <span className="boost-gain">
                <Delta value={b.estGain} />
              </span>
            </div>
          ))}
        </div>
      )}

      <style>{`
        .coach{margin-top:36px}
        .coach .eyebrow{margin-bottom:6px}
        .coach-sub{font-size:25px;margin:0 0 4px}
        .coach-note{color:var(--ink-soft);font-size:13.5px;margin:0 0 14px}
        .fix{display:grid;grid-template-columns:3px 1fr auto;gap:18px;align-items:start;padding:18px 0;border-top:1px solid var(--rule)}
        .fix-rule{width:3px;border-radius:3px;background:var(--accent,var(--brand));align-self:stretch;min-height:46px}
        .fix-meta{font-size:11px;letter-spacing:.09em;text-transform:uppercase;color:var(--ink-soft)}
        .fix-meta b{color:var(--accent,var(--brand));font-weight:700}
        .fix-title{font-weight:400;font-size:23px;line-height:1.12;margin:2px 0 5px}
        .fix-text{margin:0;color:var(--ink-soft);font-size:14px;max-width:62ch}
        .gain{padding-top:2px}
        .gain .delta{font-size:14px;white-space:nowrap}
        .boosts{margin-top:32px}
        .boost{display:grid;grid-template-columns:138px 1fr auto;gap:16px;align-items:baseline;padding:14px 0;border-top:1px solid var(--rule)}
        .boost-tag{font-size:11px;letter-spacing:.05em;font-weight:700;color:var(--ink-soft)}
        .boost-text{font-size:17px;line-height:1.3;color:var(--ink)}
        .boost-gain .delta{font-size:13px;white-space:nowrap}
      `}</style>
    </section>
  );
}
```

- [ ] **Step 2: Build-verify.** Run: `cd web && npm run build` — Expected: static export succeeds.
- [ ] **Step 3: Commit.** Run: `cd web && git add src/ui/CoachSection.tsx && git commit -m "feat(web): CoachSection fixes and small boosts from coach output"`

### Task 4: ResultsScreen — assemble the report

**Files:**
- Modify (replace stub): `web/src/ui/screens/ResultsScreen.tsx`

- [ ] **Step 1: Replace the stub with the full screen.** Full code below. The component reads `?run=<id>` via `useSearchParams` (the route already wraps it in `<Suspense>` — Phase G). On mount it loads `getRun(id)` and `listRuns()`, finds the immediately-previous run (the latest run whose `createdAt` is strictly less than the current run's), computes `diffRuns(run, prev)`, and renders the `[RevisionRail | report]` grid. The report head is the eyebrow line + serif verdict (`coach.verdict`); the `.scorebar` shows `computeTotal` and the total delta via `<Delta>` with a `vs. <prev label>` label; the four `CategoryRow`s pull their per-category delta from `diff.byCategory`; then `CoachSection`. Missing id / run-not-found render a friendly message with a link to `/`.

```tsx
"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import type { RunRecord } from "@/lib/schemas";
import { CATEGORY_KEYS } from "@/lib/schemas";
import { computeTotal, MAX_TOTAL } from "@/lib/scoring";
import { diffRuns } from "@/lib/diff";
import { getRun, listRuns } from "@/lib/store";
import { CategoryRow } from "@/ui/CategoryRow";
import { RevisionRail } from "@/ui/RevisionRail";
import { CoachSection } from "@/ui/CoachSection";
import { Delta } from "@/ui/Delta";

export function ResultsScreen() {
  const params = useSearchParams();
  const id = params.get("run");
  const [loading, setLoading] = useState(true);
  const [run, setRun] = useState<RunRecord | null>(null);
  const [prev, setPrev] = useState<RunRecord | null>(null);
  const [runs, setRuns] = useState<RunRecord[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      if (!id) {
        if (!cancelled) {
          setRun(null);
          setLoading(false);
        }
        return;
      }
      const [cur, all] = await Promise.all([getRun(id), listRuns()]);
      if (cancelled) return;
      const earlier = cur ? all.filter((r) => r.createdAt < cur.createdAt) : [];
      setRun(cur ?? null);
      setPrev(earlier.length ? earlier[earlier.length - 1] : null);
      setRuns(all);
      setLoading(false);
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading) {
    return <p className="empty">Loading score report…</p>;
  }

  if (!run) {
    return (
      <div className="empty">
        <p>That score report could not be found.</p>
        <Link className="empty-link" href="/">
          ← Score a resume
        </Link>
        <style>{`
          .empty{color:var(--ink-soft);margin-top:40px}
          .empty-link{color:var(--brand-ink);text-decoration:underline;text-underline-offset:2px}
        `}</style>
      </div>
    );
  }

  const diff = diffRuns(run, prev);
  const total = computeTotal(run.evaluation);
  const prevLabel = prev ? prev.label || prev.fileName : null;

  return (
    <div className="layout">
      <RevisionRail runs={runs} currentId={run.id} />

      <main className="report">
        <div className="report-head">
          <div className="eyebrow">Score report · {run.label || run.fileName}</div>
          <h1 className="verdict serif">{run.coach.verdict}</h1>
        </div>

        <div className="scorebar">
          <div className="total mono">
            {total}
            <small>/{MAX_TOTAL}</small>
          </div>
          <div className="total-side">
            <span className="lbl mono">{prevLabel ? `vs. ${prevLabel}` : "first run"}</span>
            <Delta value={diff.total} />
          </div>
        </div>

        <div className="cats">
          {CATEGORY_KEYS.map((k) => (
            <CategoryRow key={k} ckey={k} ev={run.evaluation} delta={diff.byCategory[k]} />
          ))}
        </div>

        <CoachSection coach={run.coach} evaluation={run.evaluation} />
      </main>

      <style>{`
        .layout{display:grid;grid-template-columns:212px 1fr;gap:30px;margin-top:26px}
        .report-head .eyebrow{margin-bottom:10px}
        .verdict{font-weight:400;font-size:clamp(30px,4vw,46px);line-height:1.08;letter-spacing:.1px;margin:0 0 4px;max-width:18ch}
        .verdict em{font-style:italic;color:var(--brand-ink)}
        .scorebar{display:flex;align-items:flex-end;gap:18px;margin:22px 0 28px;padding:18px 20px;background:var(--panel);border:1px solid var(--rule);border-radius:14px;box-shadow:var(--shadow);position:relative;overflow:hidden;background-image:linear-gradient(var(--rule) 1px,transparent 1px),linear-gradient(90deg,var(--rule) 1px,transparent 1px);background-size:22px 22px;background-position:right -1px bottom -1px}
        .scorebar:after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,var(--panel) 52%,transparent)}
        .scorebar > *{position:relative;z-index:1}
        .total{font-weight:700;font-size:54px;line-height:.9;letter-spacing:-.02em}
        .total small{font-size:20px;color:var(--ink-soft);font-weight:500}
        .total-side{padding-bottom:6px}
        .total-side .lbl{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-soft);display:block}
        .total-side .delta{font-size:18px;margin-top:2px;display:block}
        @media(max-width:760px){ .layout{grid-template-columns:1fr} }
      `}</style>
    </div>
  );
}
```

- [ ] **Step 2: Build-verify.** Run: `cd web && npm run build` — Expected: static export succeeds (`/results` prerenders the Suspense shell).
- [ ] **Step 3: Commit.** Run: `cd web && git add src/ui/screens/ResultsScreen.tsx && git commit -m "feat(web): real ResultsScreen with rail, scorebar, categories, coach"`

### Task 5: DiffScreen — compact a-vs-b comparison

**Files:**
- Modify (replace stub): `web/src/ui/screens/DiffScreen.tsx`

- [ ] **Step 1: Replace the stub with the full screen.** Full code below. The component reads `?a=<id>&b=<id>` via `useSearchParams`, loads both runs with `getRun`, and renders a compact comparison: the two run labels with their totals, then per-category deltas from `diffRuns(a, b)` (treating `a` as current and `b` as the baseline). Missing/unfound runs render a friendly message + link to `/`.

```tsx
"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import type { RunRecord } from "@/lib/schemas";
import { CATEGORY_KEYS } from "@/lib/schemas";
import { computeTotal, cappedCategory, CATEGORY_MAX, MAX_TOTAL } from "@/lib/scoring";
import { diffRuns } from "@/lib/diff";
import { getRun } from "@/lib/store";
import { Delta } from "@/ui/Delta";

export function DiffScreen() {
  const params = useSearchParams();
  const aId = params.get("a");
  const bId = params.get("b");
  const [loading, setLoading] = useState(true);
  const [a, setA] = useState<RunRecord | null>(null);
  const [b, setB] = useState<RunRecord | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      const [ra, rb] = await Promise.all([
        aId ? getRun(aId) : Promise.resolve(undefined),
        bId ? getRun(bId) : Promise.resolve(undefined),
      ]);
      if (cancelled) return;
      setA(ra ?? null);
      setB(rb ?? null);
      setLoading(false);
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [aId, bId]);

  if (loading) {
    return <p className="empty">Loading comparison…</p>;
  }

  if (!a || !b) {
    return (
      <div className="empty">
        <p>Both runs are needed to compare. One could not be found.</p>
        <Link className="empty-link" href="/">
          ← Score a resume
        </Link>
        <style>{`
          .empty{color:var(--ink-soft);margin-top:40px}
          .empty-link{color:var(--brand-ink);text-decoration:underline;text-underline-offset:2px}
        `}</style>
      </div>
    );
  }

  const diff = diffRuns(a, b);
  const aLabel = a.label || a.fileName;
  const bLabel = b.label || b.fileName;

  return (
    <div className="diff">
      <div className="eyebrow">Compare revisions</div>
      <h1 className="diff-title serif">
        {aLabel} <span className="vs">vs.</span> {bLabel}
      </h1>

      <div className="totals">
        <div className="tcol">
          <span className="tlbl mono">{aLabel}</span>
          <span className="tval mono">
            {computeTotal(a.evaluation)}
            <small>/{MAX_TOTAL}</small>
          </span>
        </div>
        <div className="tcol">
          <span className="tlbl mono">{bLabel}</span>
          <span className="tval mono">
            {computeTotal(b.evaluation)}
            <small>/{MAX_TOTAL}</small>
          </span>
        </div>
        <div className="tcol">
          <span className="tlbl mono">Δ total</span>
          <Delta value={diff.total} />
        </div>
      </div>

      <div className="rows">
        {CATEGORY_KEYS.map((k) => (
          <div className="drow" key={k}>
            <span className="dname mono">{k.toUpperCase()}</span>
            <span className="dval mono">
              {cappedCategory(a.evaluation, k)}/{CATEGORY_MAX[k]}
            </span>
            <span className="dval mono soft">
              {cappedCategory(b.evaluation, k)}/{CATEGORY_MAX[k]}
            </span>
            <Delta value={diff.byCategory[k]} />
          </div>
        ))}
      </div>

      <style>{`
        .diff{margin-top:26px;max-width:680px}
        .diff-title{font-weight:400;font-size:clamp(26px,3.4vw,38px);line-height:1.1;margin:8px 0 22px}
        .vs{font-style:italic;color:var(--ink-soft)}
        .totals{display:grid;grid-template-columns:1fr 1fr auto;gap:18px;padding:18px 20px;background:var(--panel);border:1px solid var(--rule);border-radius:14px;box-shadow:var(--shadow);margin-bottom:24px}
        .tcol{display:flex;flex-direction:column;gap:4px}
        .tlbl{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-soft)}
        .tval{font-weight:700;font-size:32px;line-height:1}
        .tval small{font-size:14px;color:var(--ink-soft);font-weight:500}
        .totals .delta{font-size:18px}
        .drow{display:grid;grid-template-columns:1fr 70px 70px 70px;gap:14px;align-items:center;padding:14px 2px;border-top:1px solid var(--rule)}
        .dname{font-size:12px;letter-spacing:.06em;font-weight:500}
        .dval{font-weight:700;font-size:14px;text-align:right}
        .soft{color:var(--ink-soft);font-weight:500}
        .drow .delta{text-align:right}
        @media(max-width:760px){ .totals{grid-template-columns:1fr 1fr} }
      `}</style>
    </div>
  );
}
```

- [ ] **Step 2: Build-verify.** Run: `cd web && npm run build` — Expected: static export succeeds (`/diff` prerenders the Suspense shell).
- [ ] **Step 3: Commit.** Run: `cd web && git add src/ui/screens/DiffScreen.tsx && git commit -m "feat(web): compact DiffScreen comparing two runs by total and category"`


## Phase J — History & Trends screen (stats, chart, sparklines, changelog)

This phase replaces the `HistoryScreen` stub with the full History & Trends dashboard from `trends-dashboard.html`. It delivers three presentational components — `TotalChart` (SVG line+area of total score over time, drawn from `buildLinePath`), `Sparkline` (per-category mini-trend from `buildSparkPath`, colored by `Status`), and `HistoryTable` (newest-first changelog with inline rename, View, Diff, and delete) — then wires them together in `HistoryScreen`, which loads runs from the IndexedDB store, computes `summaryStats`/`totalSeries`/`categorySeries` from the pure `trends.ts` module, and re-loads after every mutation. The three components carry no practical unit test (pure-helper-free, SVG/DOM presentation), so each is verified by a green static-export build; all data math is already TDD-covered in `trends.ts`. Empty history renders a friendly call-to-action linking back to the Score route.

### Task 1: TotalChart component

**Files:**
- Create: `web/src/ui/TotalChart.tsx`

- [ ] **Step 1: Write the component.** Full code — coordinate system is chosen so the five y-gridlines land exactly on `buildLinePath`'s node y-positions (same `yForValue` formula, `maxY:120`).

```tsx
// web/src/ui/TotalChart.tsx
"use client";
import type { SeriesPoint } from "../lib/trends";
import { buildLinePath } from "../lib/trends";

const W = 720;
const H = 260;
const PAD = 40;
const MAX_Y = 120;
const GRID_VALUES = [0, 30, 60, 90, 120];

// Same vertical mapping buildLinePath uses, so gridlines align with nodes.
function yForValue(v: number): number {
  return H - PAD - (v / MAX_Y) * (H - 2 * PAD);
}

function formatAxisDate(ts: number): string {
  return new Date(ts).toLocaleDateString("en-US", { month: "short", day: "2-digit" });
}

export function TotalChart({ series }: { series: SeriesPoint[] }) {
  const values = series.map((p) => p.total);
  const { line, area, points } = buildLinePath(values, { w: W, h: H, pad: PAD, maxY: MAX_Y });
  const first = series[0]?.total ?? 0;
  const last = series[series.length - 1]?.total ?? 0;
  const label =
    series.length === 0
      ? "Total score over time (no runs yet)"
      : `Total score over time, from ${first} to ${last} out of 120`;

  return (
    <svg className="ha-chart" viewBox={`0 0 ${W} ${H + 12}`} role="img" aria-label={label}>
      {GRID_VALUES.map((v) => {
        const y = yForValue(v);
        return (
          <g key={v}>
            <line className="ha-gridline" x1={PAD} y1={y} x2={W - PAD} y2={y} />
            <text className="ha-axis-lbl" x={PAD - 10} y={y + 4} textAnchor="end">
              {v}
            </text>
          </g>
        );
      })}
      {area && <path className="ha-area" d={area} />}
      {line && <path className="ha-line" d={line} />}
      {points.map((pt, i) => (
        <g key={series[i]?.id ?? i}>
          <circle className="ha-node" cx={pt.x} cy={pt.y} r={4.5} />
          <text className="ha-node-lbl" x={pt.x} y={pt.y - 12} textAnchor="middle">
            {values[i]}
          </text>
          <text className="ha-x-lbl" x={pt.x} y={H + 6} textAnchor="middle">
            {formatAxisDate(series[i].createdAt)}
          </text>
        </g>
      ))}
      <style>{`
        .ha-chart{width:100%;height:auto;display:block;margin-top:8px}
        .ha-gridline{stroke:var(--rule);stroke-width:1}
        .ha-axis-lbl{fill:var(--ink-soft);font-family:var(--font-jetbrains-mono),monospace;font-size:10px}
        .ha-x-lbl{fill:var(--ink-soft);font-family:var(--font-jetbrains-mono),monospace;font-size:10.5px}
        .ha-area{fill:var(--brand-tint)}
        .ha-line{fill:none;stroke:var(--brand);stroke-width:2.5;stroke-linejoin:round;stroke-linecap:round}
        .ha-node{fill:var(--panel);stroke:var(--brand);stroke-width:2.5}
        .ha-node-lbl{fill:var(--ink);font-family:var(--font-jetbrains-mono),monospace;font-weight:700;font-size:12px}
      `}</style>
    </svg>
  );
}
```

- [ ] **Step 2: Build-verify.** Run: `cd web && npm run build` — Expected: static export succeeds (compiles with no type errors; `SeriesPoint`/`buildLinePath` resolve from `../lib/trends`).
- [ ] **Step 3: Commit.**
  - `git add web/src/ui/TotalChart.tsx`
  - `git commit -m "feat(web): TotalChart SVG line chart from buildLinePath"`

### Task 2: Sparkline component

**Files:**
- Create: `web/src/ui/Sparkline.tsx`

- [ ] **Step 1: Write the component.** Full code — stroke/fill chosen from the `Status` via the existing color vars; `aria-hidden` because the numeric value + Delta beside it already convey the data.

```tsx
// web/src/ui/Sparkline.tsx
"use client";
import type { Status } from "../lib/scoring";
import { buildSparkPath } from "../lib/trends";

const W = 220;
const H = 44;

const COLOR: Record<Status, { stroke: string; fill: string }> = {
  good: { stroke: "var(--good)", fill: "var(--good-tint)" },
  warn: { stroke: "var(--warn)", fill: "var(--warn-tint)" },
  bad: { stroke: "var(--bad)", fill: "var(--bad-tint)" },
};

export function Sparkline({ values, status }: { values: number[]; status: Status }) {
  const { line, area } = buildSparkPath(values, { w: W, h: H });
  const c = COLOR[status];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden="true">
      {area && <path d={area} fill={c.fill} />}
      {line && (
        <path
          d={line}
          fill="none"
          stroke={c.stroke}
          strokeWidth={2.5}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      )}
    </svg>
  );
}
```

- [ ] **Step 2: Build-verify.** Run: `cd web && npm run build` — Expected: static export succeeds (`Status` from `../lib/scoring`, `buildSparkPath` from `../lib/trends` resolve).
- [ ] **Step 3: Commit.**
  - `git add web/src/ui/Sparkline.tsx`
  - `git commit -m "feat(web): Sparkline SVG from buildSparkPath, status-colored"`

### Task 3: HistoryTable component

**Files:**
- Create: `web/src/ui/HistoryTable.tsx`

- [ ] **Step 1: Write the component.** Full code — `runs` arrive ascending by `createdAt`; we pair each with its previous (older) run for the delta, then reverse for newest-first display. Diff link is omitted for the oldest run (no `prev`). Rename uses `window.prompt`; delete uses `window.confirm`.

```tsx
// web/src/ui/HistoryTable.tsx
"use client";
import Link from "next/link";
import type { RunRecord } from "../lib/schemas";
import { computeTotal } from "../lib/scoring";
import { diffRuns } from "../lib/diff";
import { Delta } from "./Delta";

function formatDateTime(ts: number): string {
  const d = new Date(ts);
  const date = d.toLocaleDateString("en-US", { month: "short", day: "2-digit" });
  const time = d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
  return `${date} · ${time}`;
}

export function HistoryTable({
  runs,
  onRename,
  onDelete,
}: {
  runs: RunRecord[];
  onRename: (id: string, label: string) => void;
  onDelete: (id: string) => void;
}) {
  // ascending in -> pair with previous (older) -> reverse to newest-first.
  const rows = runs.map((run, i) => ({ run, prev: i > 0 ? runs[i - 1] : null }));
  rows.reverse();

  function handleRename(run: RunRecord) {
    const next = window.prompt("Label for this revision", run.label ?? "");
    if (next === null) return;
    onRename(run.id, next.trim());
  }

  function handleDelete(run: RunRecord) {
    if (window.confirm(`Delete "${run.label || run.fileName}"? This cannot be undone.`)) {
      onDelete(run.id);
    }
  }

  return (
    <table className="ha-htable">
      <thead>
        <tr>
          <th>Revision</th>
          <th className="hide">Date</th>
          <th className="r">Score</th>
          <th className="r">Δ</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {rows.map(({ run, prev }) => {
          const d = diffRuns(run, prev);
          return (
            <tr key={run.id}>
              <td>
                <span className="ha-h-name">{run.fileName}</span>
                {run.label && <span className="ha-h-label">{run.label}</span>}
                <button className="ha-h-rename" onClick={() => handleRename(run)}>
                  rename
                </button>
              </td>
              <td className="ha-h-date hide">{formatDateTime(run.createdAt)}</td>
              <td className="r ha-h-total">{computeTotal(run.evaluation)}</td>
              <td className="r">
                <Delta value={d.total} />
              </td>
              <td className="r">
                <Link className="ha-h-act" href={`/results?run=${run.id}`}>
                  View
                </Link>{" "}
                {prev && (
                  <>
                    <Link className="ha-h-act diff" href={`/diff?a=${run.id}&b=${prev.id}`}>
                      Diff
                    </Link>{" "}
                  </>
                )}
                <button className="ha-h-act del" onClick={() => handleDelete(run)}>
                  Delete
                </button>
              </td>
            </tr>
          );
        })}
      </tbody>
      <style>{`
        .ha-htable{width:100%;border-collapse:collapse}
        .ha-htable th{font-family:var(--font-jetbrains-mono),monospace;font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-soft);text-align:left;font-weight:500;padding:0 12px 10px;border-bottom:1px solid var(--rule)}
        .ha-htable th.r,.ha-htable td.r{text-align:right}
        .ha-htable td{padding:14px 12px;border-bottom:1px solid var(--rule);vertical-align:middle}
        .ha-htable tr:hover td{background:var(--panel-2)}
        .ha-h-name{font-family:var(--font-jetbrains-mono),monospace;font-weight:500;font-size:13.5px}
        .ha-h-label{display:inline-block;font-family:var(--font-archivo),sans-serif;font-size:11px;color:var(--brand-ink);background:var(--brand-tint);border-radius:6px;padding:1px 7px;margin-left:8px}
        .ha-h-rename{font-family:var(--font-archivo),sans-serif;color:var(--ink-soft);font-size:11px;margin-left:8px;background:transparent;border:none;border-bottom:1px dotted var(--ink-soft);padding:0;cursor:pointer;opacity:0;transition:opacity .15s}
        .ha-htable tr:hover .ha-h-rename{opacity:1}
        .ha-h-date{font-family:var(--font-jetbrains-mono),monospace;color:var(--ink-soft);font-size:12.5px}
        .ha-h-total{font-family:var(--font-jetbrains-mono),monospace;font-weight:700;font-size:15px}
        .ha-h-act{font-family:var(--font-jetbrains-mono),monospace;font-size:11.5px;color:var(--ink);text-decoration:none;background:transparent;border:1px solid var(--rule);padding:5px 10px;border-radius:7px;cursor:pointer}
        .ha-h-act:hover{border-color:var(--brand);color:var(--brand-ink)}
        .ha-h-act.diff{color:var(--ink-soft)}
        .ha-h-act.del{color:var(--bad)}
        .ha-h-act.del:hover{border-color:var(--bad);color:var(--bad)}
        @media(max-width:760px){.ha-h-date.hide,.ha-htable .hide{display:none}}
        @media (prefers-reduced-motion: reduce){.ha-h-rename{transition:none}}
      `}</style>
    </table>
  );
}
```

- [ ] **Step 2: Build-verify.** Run: `cd web && npm run build` — Expected: static export succeeds (`diffRuns`, `computeTotal`, `Delta`, `RunRecord` all resolve; `next/link` ok under output:"export").
- [ ] **Step 3: Commit.**
  - `git add web/src/ui/HistoryTable.tsx`
  - `git commit -m "feat(web): HistoryTable changelog with rename/view/diff/delete"`

### Task 4: HistoryScreen wiring

**Files:**
- Modify (replace stub): `web/src/ui/screens/HistoryScreen.tsx`

- [ ] **Step 1: Replace the stub.** Full code — loads `listRuns()` on mount, computes `summaryStats`/`totalSeries`/`categorySeries`, renders the four stat cards, the `TotalChart`, the four per-category `Sparkline`s (latest value + `Delta`), and the wired `HistoryTable`. Mutations call `renameRun`/`deleteRun` then re-load. Empty history shows a CTA to `/`.

```tsx
// web/src/ui/screens/HistoryScreen.tsx
"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import type { RunRecord } from "../../lib/schemas";
import { CATEGORY_KEYS } from "../../lib/schemas";
import { listRuns, renameRun, deleteRun } from "../../lib/store";
import { totalSeries, categorySeries, summaryStats } from "../../lib/trends";
import { CATEGORY_MAX, statusFor } from "../../lib/scoring";
import { TotalChart } from "../TotalChart";
import { Sparkline } from "../Sparkline";
import { HistoryTable } from "../HistoryTable";
import { Delta } from "../Delta";

function formatShort(ts: number | null): string {
  if (ts === null) return "—";
  return new Date(ts).toLocaleDateString("en-US", { month: "short", day: "2-digit" });
}

export function HistoryScreen() {
  const [runs, setRuns] = useState<RunRecord[] | null>(null);

  const reload = useCallback(async () => {
    setRuns(await listRuns());
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const handleRename = useCallback(
    async (id: string, label: string) => {
      await renameRun(id, label);
      await reload();
    },
    [reload],
  );

  const handleDelete = useCallback(
    async (id: string) => {
      await deleteRun(id);
      await reload();
    },
    [reload],
  );

  if (runs === null) return null;

  if (runs.length === 0) {
    return (
      <div className="ha-empty">
        <div className="eyebrow">History &amp; Trends</div>
        <h1 className="serif ha-empty-title">No runs yet.</h1>
        <p className="ha-empty-text">Score a resume to start tracking your progress over time.</p>
        <Link href="/" className="ha-empty-cta">
          Score a resume →
        </Link>
        <style>{`
          .ha-empty{margin:60px auto;max-width:480px;text-align:center}
          .ha-empty-title{font-weight:400;font-size:clamp(28px,3.6vw,40px);line-height:1.05;margin:6px 0 10px}
          .ha-empty-text{color:var(--ink-soft);margin:0 0 22px}
          .ha-empty-cta{font-family:var(--font-jetbrains-mono),monospace;font-size:13px;color:var(--brand-ink);background:var(--brand-tint);border:1px solid color-mix(in srgb,var(--brand) 32%,transparent);padding:9px 16px;border-radius:9px;text-decoration:none}
          .ha-empty-cta:hover{border-color:var(--brand)}
        `}</style>
      </div>
    );
  }

  const series = totalSeries(runs);
  const summary = summaryStats(runs);
  const lastDelta =
    series.length >= 2 ? series[series.length - 1].total - series[series.length - 2].total : null;

  return (
    <>
      <div className="ha-page-head">
        <div>
          <div className="eyebrow">History &amp; Trends</div>
          <h1 className="serif ha-page-title">Your resume, over time.</h1>
        </div>
      </div>

      <div className="ha-stats">
        <div className="ha-stat">
          <div className="ha-stat-lbl">Latest score</div>
          <div className="ha-stat-val">
            {summary.latest}
            <small>/120</small>
          </div>
          <div className="ha-stat-sub">
            <Delta value={lastDelta} suffix="vs. last" />
          </div>
        </div>
        <div className="ha-stat">
          <div className="ha-stat-lbl">Personal best</div>
          <div className="ha-stat-val">
            {summary.personalBest}
            <small>/120</small>
          </div>
          <div className="ha-stat-sub">
            {summary.personalBest === summary.latest ? "Also the latest" : "Across all runs"}
          </div>
        </div>
        <div className="ha-stat">
          <div className="ha-stat-lbl">Net change</div>
          <div className="ha-stat-val">
            <Delta value={summary.netChange} />
          </div>
          <div className="ha-stat-sub">Since your first run</div>
        </div>
        <div className="ha-stat">
          <div className="ha-stat-lbl">Runs</div>
          <div className="ha-stat-val">{summary.runCount}</div>
          <div className="ha-stat-sub">
            {formatShort(summary.firstAt)} → {formatShort(summary.lastAt)}
          </div>
        </div>
      </div>

      <div className="ha-panel">
        <div className="ha-panel-head">
          <div className="ha-panel-title serif">Total score</div>
          <div className="ha-panel-note">
            {summary.runCount} {summary.runCount === 1 ? "run" : "runs"} · out of 120
          </div>
        </div>
        <TotalChart series={series} />
      </div>

      <div className="ha-spark-grid">
        {CATEGORY_KEYS.map((key) => {
          const values = categorySeries(runs, key);
          const latest = values.length > 0 ? values[values.length - 1] : 0;
          const catDelta = values.length >= 2 ? latest - values[values.length - 2] : null;
          const status = statusFor(latest, CATEGORY_MAX[key]);
          return (
            <div className="ha-spark" key={key}>
              <div className="ha-spark-name">{key.toUpperCase()}</div>
              <div className="ha-spark-row">
                <span className="ha-spark-val">
                  {latest}
                  <small>/{CATEGORY_MAX[key]}</small>
                </span>
                <Delta value={catDelta} />
              </div>
              <Sparkline values={values} status={status} />
            </div>
          );
        })}
      </div>

      <div className="ha-history">
        <div className="eyebrow ha-history-eyebrow">Run history</div>
        <HistoryTable runs={runs} onRename={handleRename} onDelete={handleDelete} />
      </div>

      <style>{`
        .ha-page-head{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;margin:26px 0 22px;flex-wrap:wrap}
        .ha-page-title{font-weight:400;font-size:clamp(28px,3.6vw,40px);line-height:1.05;margin:6px 0 0}
        .ha-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}
        .ha-stat{background:var(--panel);border:1px solid var(--rule);border-radius:12px;padding:15px 16px;box-shadow:var(--shadow)}
        .ha-stat-lbl{font-family:var(--font-jetbrains-mono),monospace;font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-soft)}
        .ha-stat-val{font-family:var(--font-jetbrains-mono),monospace;font-weight:700;font-size:27px;margin-top:7px;letter-spacing:-.01em}
        .ha-stat-val small{font-size:14px;color:var(--ink-soft);font-weight:500}
        .ha-stat-sub{font-family:var(--font-jetbrains-mono),monospace;font-size:11px;margin-top:3px;color:var(--ink-soft)}
        .ha-panel{background:var(--panel);border:1px solid var(--rule);border-radius:14px;box-shadow:var(--shadow);padding:20px 22px}
        .ha-panel-head{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-bottom:6px}
        .ha-panel-title{font-size:22px}
        .ha-panel-note{font-family:var(--font-jetbrains-mono),monospace;font-size:11px;color:var(--ink-soft)}
        .ha-spark-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:16px}
        .ha-spark{background:var(--panel);border:1px solid var(--rule);border-radius:12px;padding:15px 16px;box-shadow:var(--shadow)}
        .ha-spark-name{font-family:var(--font-jetbrains-mono),monospace;font-size:11px;letter-spacing:.05em;font-weight:500;color:var(--ink-soft)}
        .ha-spark-row{display:flex;align-items:baseline;justify-content:space-between;margin-top:8px}
        .ha-spark-val{font-family:var(--font-jetbrains-mono),monospace;font-weight:700;font-size:19px}
        .ha-spark-val small{font-size:12px;color:var(--ink-soft);font-weight:500}
        .ha-spark svg{width:100%;height:40px;margin-top:10px;display:block}
        .ha-history{margin-top:26px}
        .ha-history-eyebrow{margin-bottom:12px}
        @media(max-width:760px){.ha-stats{grid-template-columns:repeat(2,1fr)}.ha-spark-grid{grid-template-columns:repeat(2,1fr)}}
      `}</style>
    </>
  );
}
```

- [ ] **Step 2: Build-verify.** Run: `cd web && npm run build` — Expected: static export succeeds; `/history` prerenders. Imports `listRuns`/`renameRun`/`deleteRun` (store), `totalSeries`/`categorySeries`/`summaryStats` (trends), `CATEGORY_MAX`/`statusFor` (scoring), and the three new components all resolve.
- [ ] **Step 3: Commit.**
  - `git add web/src/ui/screens/HistoryScreen.tsx`
  - `git commit -m "feat(web): wire HistoryScreen — stats, chart, sparklines, changelog"`


## Phase K — Settings screen

This phase replaces the `SettingsScreen` placeholder stub with the real settings surface backed by `useSettings()`. It exposes the Gemini key (required), an optional GitHub token, the GitHub-enrichment toggle, an optional model override (placeholder `DEFAULT_MODEL`), the privacy-defining "remember keys on this device" toggle, a theme row (reusing `<ThemeToggle/>`), and a "Clear all data" control that confirms then calls `clearAllData()`. Every edit flows through `update({...})`, shows an inline "Saved" affirmation, and the remember toggle's helper text makes the privacy tradeoff explicit (keys are kept only for the session when off). The screen is plain-CSS with a scoped `<style>` block per the Part 1 convention, supports light/dark via the existing CSS vars, and respects visible focus and `prefers-reduced-motion`. There is no practical unit test for this component (it is exercised by the Phase L Playwright smoke), so the task ends with a build-verify and commit.

### Task 1: Replace the SettingsScreen stub with the real settings surface

**Files:**
- Modify (replace whole file): `web/src/ui/screens/SettingsScreen.tsx`

- [ ] **Step 1: Write the full component.** Replace the entire contents of `web/src/ui/screens/SettingsScreen.tsx` with the code below. It imports the real exports only: `useSettings` from `../SettingsProvider`, `DEFAULT_MODEL` from `../../lib/gemini`, `clearAllData` from `../../lib/settings`, `StoredSettings` from `../../lib/schemas`, and `ThemeToggle` from `../ThemeToggle`. Every field edit calls `edit(...)` which wraps `update(...)` and flashes the "Saved" affirmation; the remember toggle's hint text changes based on `settings.rememberKeys` to make the session-only-vs-persisted tradeoff explicit.

```tsx
"use client";
import { useCallback, useRef, useState } from "react";
import type { StoredSettings } from "../../lib/schemas";
import { DEFAULT_MODEL } from "../../lib/gemini";
import { clearAllData } from "../../lib/settings";
import { useSettings } from "../SettingsProvider";
import { ThemeToggle } from "../ThemeToggle";

export function SettingsScreen() {
  const { settings, update } = useSettings();
  const [saved, setSaved] = useState(false);
  const [cleared, setCleared] = useState(false);
  const savedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const edit = useCallback(
    (patch: Partial<StoredSettings>) => {
      update(patch);
      setSaved(true);
      setCleared(false);
      if (savedTimer.current) clearTimeout(savedTimer.current);
      savedTimer.current = setTimeout(() => setSaved(false), 1600);
    },
    [update]
  );

  const onClear = useCallback(async () => {
    const ok = window.confirm(
      "Erase all saved runs, resumes, and settings from this browser? This cannot be undone."
    );
    if (!ok) return;
    await clearAllData();
    setCleared(true);
  }, []);

  return (
    <section className="ha-settings">
      <header className="ha-set-head">
        <div className="eyebrow">Settings</div>
        <h1 className="serif ha-set-title">Keys, privacy &amp; appearance.</h1>
        <p className="ha-set-sub">
          Everything below is stored only in this browser. Nothing is sent to a server of ours.
        </p>
      </header>

      <div className="ha-card">
        <label className="ha-field" htmlFor="ha-gemini-key">
          <span className="ha-flabel">
            Gemini API key <span className="ha-req">required</span>
          </span>
          <input
            id="ha-gemini-key"
            type="password"
            className="ha-input mono"
            placeholder="AIza…"
            autoComplete="off"
            spellCheck={false}
            value={settings.geminiKey}
            onChange={(e) => edit({ geminiKey: e.target.value })}
          />
          <span className="ha-hint">
            Scoring calls Google Gemini directly from your browser with this key. Create one at
            aistudio.google.com — it never leaves this device.
          </span>
        </label>

        <label className="ha-field" htmlFor="ha-github-token">
          <span className="ha-flabel">
            GitHub token <span className="ha-opt">optional</span>
          </span>
          <input
            id="ha-github-token"
            type="password"
            className="ha-input mono"
            placeholder="ghp_…"
            autoComplete="off"
            spellCheck={false}
            value={settings.githubToken}
            onChange={(e) => edit({ githubToken: e.target.value })}
          />
          <span className="ha-hint">
            Lets the scorer read your public GitHub signal and raises the rate limit from 60 to
            5,000 requests/hour. Used only when GitHub enrichment is on.
          </span>
        </label>

        <div className="ha-row">
          <div className="ha-row-text">
            <span className="ha-flabel">GitHub enrichment</span>
            <span className="ha-hint">Pull repositories and contributions into the score.</span>
          </div>
          <input
            type="checkbox"
            className="ha-check"
            role="switch"
            aria-label="Enable GitHub enrichment"
            checked={settings.enableGitHub}
            onChange={(e) => edit({ enableGitHub: e.target.checked })}
          />
        </div>

        <label className="ha-field" htmlFor="ha-model">
          <span className="ha-flabel">
            Model <span className="ha-opt">optional</span>
          </span>
          <input
            id="ha-model"
            type="text"
            className="ha-input mono"
            placeholder={DEFAULT_MODEL}
            autoComplete="off"
            spellCheck={false}
            value={settings.model}
            onChange={(e) => edit({ model: e.target.value })}
          />
          <span className="ha-hint">Defaults to {DEFAULT_MODEL}.</span>
        </label>
      </div>

      <div className="ha-card">
        <div className="ha-row">
          <div className="ha-row-text">
            <span className="ha-flabel">Remember keys on this device</span>
            <span className="ha-hint">
              {settings.rememberKeys
                ? "Keys are saved in this browser's localStorage so you don't re-enter them."
                : "Keys are kept only for this session (in memory) and cleared when you close the tab."}
            </span>
          </div>
          <input
            type="checkbox"
            className="ha-check"
            role="switch"
            aria-label="Remember keys on this device"
            checked={settings.rememberKeys}
            onChange={(e) => edit({ rememberKeys: e.target.checked })}
          />
        </div>

        <div className="ha-row">
          <div className="ha-row-text">
            <span className="ha-flabel">Theme</span>
            <span className="ha-hint">Light or dark. Saved on this device.</span>
          </div>
          <ThemeToggle />
        </div>
      </div>

      <div className="ha-card ha-danger">
        <div className="ha-row">
          <div className="ha-row-text">
            <span className="ha-flabel">Clear all data</span>
            <span className="ha-hint">
              Erase every saved run, resume, and setting from this browser. Your theme is kept.
            </span>
          </div>
          <button type="button" className="ha-btn-danger" onClick={onClear}>
            Clear all data
          </button>
        </div>
        {cleared && (
          <p className="ha-cleared mono" role="status">
            ✓ All data cleared.
          </p>
        )}
      </div>

      <div className="ha-saved mono" aria-live="polite">
        {saved ? "✓ Saved" : ""}
      </div>

      <style>{`
        .ha-settings{display:flex;flex-direction:column;gap:18px;max-width:680px;margin:0 auto;padding:8px 0 40px}
        .ha-set-head{display:flex;flex-direction:column;gap:6px}
        .ha-set-title{font-weight:400;font-size:34px;line-height:1.1;margin:2px 0 0}
        .ha-set-sub{margin:0;font-size:14px;color:var(--ink-soft);line-height:1.5}
        .ha-card{background:var(--panel);border:1px solid var(--rule);border-radius:14px;padding:20px;display:flex;flex-direction:column;gap:20px;box-shadow:var(--shadow)}
        .ha-field{display:flex;flex-direction:column;gap:7px}
        .ha-flabel{font-size:13.5px;font-weight:600;color:var(--ink);display:flex;align-items:center;gap:8px}
        .ha-req{font-size:11px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--bad);background:var(--bad-tint);border-radius:999px;padding:2px 8px}
        .ha-opt{font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--ink-soft);background:var(--panel-2);border-radius:999px;padding:2px 8px}
        .ha-input{width:100%;box-sizing:border-box;background:var(--panel-2);border:1px solid var(--rule);border-radius:10px;padding:11px 13px;font-size:14px;color:var(--ink)}
        .ha-input::placeholder{color:var(--ink-soft);opacity:.7}
        .ha-input:focus-visible{outline:2px solid var(--brand);outline-offset:2px;border-color:var(--brand)}
        .ha-hint{font-size:12.5px;color:var(--ink-soft);line-height:1.5}
        .ha-row{display:flex;align-items:flex-start;justify-content:space-between;gap:18px}
        .ha-row-text{display:flex;flex-direction:column;gap:5px;flex:1}
        .ha-check{appearance:none;-webkit-appearance:none;position:relative;width:46px;height:26px;border-radius:999px;border:1px solid var(--rule);background:var(--panel-2);cursor:pointer;flex:none;margin-top:2px;transition:background .18s ease}
        .ha-check::after{content:"";position:absolute;top:2px;left:2px;width:20px;height:20px;border-radius:50%;background:var(--panel);box-shadow:var(--shadow);transition:left .18s ease}
        .ha-check:checked{background:var(--brand)}
        .ha-check:checked::after{left:22px}
        .ha-check:focus-visible{outline:2px solid var(--brand);outline-offset:3px}
        .ha-danger{border-color:var(--bad-tint)}
        .ha-btn-danger{flex:none;background:var(--bad-tint);color:var(--bad);border:1px solid var(--bad);border-radius:10px;padding:9px 15px;font-size:13px;font-weight:600;cursor:pointer}
        .ha-btn-danger:hover{background:var(--bad);color:var(--paper)}
        .ha-btn-danger:focus-visible{outline:2px solid var(--bad);outline-offset:3px}
        .ha-cleared{margin:0;font-size:12.5px;color:var(--good)}
        .ha-saved{min-height:18px;font-size:12.5px;color:var(--good);text-align:right;transition:opacity .2s ease}
        @media (prefers-reduced-motion: reduce){
          .ha-check,.ha-check::after,.ha-saved{transition:none}
        }
        @media (max-width:560px){
          .ha-set-title{font-size:28px}
          .ha-card{padding:16px}
        }
      `}</style>
    </section>
  );
}
```

- [ ] **Step 2: Build-verify the static export.** Run: `cd web && npm run build` — Expected: the Next.js static export succeeds with no TypeScript errors and `/settings` is emitted as a static route. (This is the verification gate for the component; the interactive behavior is covered by the Phase L Playwright smoke.)

- [ ] **Step 3: Commit.** Run:
  - `git add web/src/ui/screens/SettingsScreen.tsx`
  - `git commit -m "feat(web): real Settings screen with keys, remember-key privacy toggle, and clear-all-data"`


## Phase L — Playwright smoke, Vercel deploy & pdf worker

This phase makes the app deploy-ready and proves the end-to-end happy path with an offline smoke test. It ships the pdfjs worker as a static asset under `/public` (so both `next dev` and the static export resolve it identically), adds a committed sample-PDF generator, wires a Playwright Chromium smoke that stubs every `generativelanguage.googleapis.com` call with schema-valid canned JSON, and lands Vercel config plus a `README.md` documenting runtime-key usage and the "scores are indicative" caveat. No application logic depends on Part 2 screens beyond their existence; the smoke asserts the Results screen renders a total and a category name.

### Task 1: Ship the pdfjs worker as a static `/public` asset

The current `pdf.ts` resolves `workerSrc` from the module URL (`new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url)`), which is brittle under `output: "export"`. We copy the worker into `web/public/` at install/build time and point `workerSrc` at the stable `/pdf.worker.min.mjs` path so dev, export, and Playwright all behave the same.

**Files:**
- Create: `web/scripts/copy-pdf-worker.mjs`
- Modify: `web/package.json` (scripts block, lines 6–14)
- Modify: `web/src/lib/pdf.ts` (lines 12–16)
- Modify: `web/.gitignore` (or repo root `.gitignore`) — ignore the generated worker
- Create: `web/public/.gitkeep`

Steps:

- [ ] **Step 1: Write the copy script.** Create `web/scripts/copy-pdf-worker.mjs`:

```js
// Copies the pdfjs-dist web worker into web/public so it ships as a static
// asset at /pdf.worker.min.mjs under both `next dev` and `output: "export"`.
// Runs automatically via the predev/prebuild npm hooks; safe to run by hand.
import { existsSync, mkdirSync, copyFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(here, "..");
const src = resolve(webRoot, "node_modules/pdfjs-dist/build/pdf.worker.min.mjs");
const destDir = resolve(webRoot, "public");
const dest = resolve(destDir, "pdf.worker.min.mjs");

if (!existsSync(src)) {
  console.error(`[copy-pdf-worker] missing source: ${src}\nRun \`npm install\` first.`);
  process.exit(1);
}
mkdirSync(destDir, { recursive: true });
copyFileSync(src, dest);
console.log(`[copy-pdf-worker] copied -> ${dest}`);
```

- [ ] **Step 2: Add a `public/.gitkeep`.** Create `web/public/.gitkeep` (empty file) so the directory exists in a fresh clone before the worker is copied.

- [ ] **Step 3: Wire the npm hooks.** Edit `web/package.json` scripts block so the worker is copied before dev/build/e2e and after install. Replace the scripts object:

```json
  "scripts": {
    "predev": "node scripts/copy-pdf-worker.mjs",
    "dev": "next dev",
    "prebuild": "node scripts/copy-pdf-worker.mjs",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest run",
    "test:watch": "vitest",
    "pree2e": "node scripts/copy-pdf-worker.mjs",
    "e2e": "playwright test",
    "copy:pdf-worker": "node scripts/copy-pdf-worker.mjs"
  },
```

- [ ] **Step 4: Point `workerSrc` at the static path.** Edit `web/src/lib/pdf.ts` lines 12–16 to reference the copied asset, keeping the module-URL resolution as a fallback for non-browser/test contexts:

```ts
  // Worker is copied to /public by scripts/copy-pdf-worker.mjs and served at a
  // stable path under both `next dev` and `output: "export"`. Fall back to the
  // bundler-resolved module URL if the static asset is unavailable.
  (pdfjs as any).GlobalWorkerOptions.workerSrc =
    typeof window !== "undefined"
      ? "/pdf.worker.min.mjs"
      : new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();
```

- [ ] **Step 5: Ignore the generated worker.** Append to `web/.gitignore` (create the file if it does not exist):

```gitignore
# Generated by scripts/copy-pdf-worker.mjs
public/pdf.worker.min.mjs
```

- [ ] **Step 6: Generate the worker and build-verify.** Run: `cd web && npm run copy:pdf-worker && npm run build` — Expected: the script logs `copied -> .../public/pdf.worker.min.mjs` and the Next.js static export succeeds (an `out/` directory is produced with `pdf.worker.min.mjs` present). Confirm: `cd web && test -f out/pdf.worker.min.mjs && echo OK`.

- [ ] **Step 7: Commit.**
  - `git add web/scripts/copy-pdf-worker.mjs web/public/.gitkeep web/package.json web/src/lib/pdf.ts web/.gitignore`
  - `git commit -m "chore(web): ship pdfjs worker as static /public asset"`

### Task 2: Playwright config

A single Chromium project that boots `next dev` on port 3000 and reuses an already-running server locally. Tests live in `web/e2e`.

**Files:**
- Create: `web/playwright.config.ts`

Steps:

- [ ] **Step 1: Write the config.** Create `web/playwright.config.ts`:

```ts
import { defineConfig, devices } from "@playwright/test";

const PORT = 3000;
const BASE_URL = `http://localhost:${PORT}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: "npm run dev",
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
```

- [ ] **Step 2: Sanity-check Playwright sees the config.** Run: `cd web && npx playwright test --list` — Expected: it parses the config without error (it will report 0 tests until Task 4 adds the spec; that is fine).

- [ ] **Step 3: Commit.**
  - `git add web/playwright.config.ts`
  - `git commit -m "chore(web): add Playwright config (Chromium, next dev server)"`

### Task 3: Committed sample-PDF fixture generator

Binary cannot be inlined in a plan, so we commit a tiny `pdfkit` generator and run it once to produce `web/test/fixtures/sample-resume.pdf`. The PDF is text-based so pdfjs extracts real text.

**Files:**
- Modify: `web/package.json` (devDependencies, lines 24–31)
- Create: `web/test/fixtures/make-sample-pdf.mjs`
- Create (generated): `web/test/fixtures/sample-resume.pdf`

Steps:

- [ ] **Step 1: Add `pdfkit` as a devDependency.** Run: `cd web && npm install --save-dev pdfkit@^0.15.0` — Expected: `pdfkit` appears under `devDependencies` in `web/package.json` and `package-lock.json` updates.

- [ ] **Step 2: Write the generator.** Create `web/test/fixtures/make-sample-pdf.mjs`:

```js
// Generates a short, text-based resume PDF for the Playwright smoke test.
// Run once and commit the output:
//   cd web && node test/fixtures/make-sample-pdf.mjs
import PDFDocument from "pdfkit";
import { createWriteStream } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "sample-resume.pdf");

const doc = new PDFDocument({ size: "LETTER", margin: 54 });
doc.pipe(createWriteStream(out));

doc.fontSize(20).text("Test Candidate");
doc.moveDown(0.5);
doc.fontSize(11).text("test@example.com  |  github.com/test-candidate");
doc.moveDown();

doc.fontSize(14).text("Experience");
doc.fontSize(11).text(
  "Software Engineer, Acme Corp (2021-2024). Built and shipped production " +
    "TypeScript services. Led migration to a typed API layer.",
);
doc.moveDown();

doc.fontSize(14).text("Projects");
doc.fontSize(11).text(
  "open-source-tool - a CLI used by 1k+ developers. Maintained tests and CI.",
);
doc.moveDown();

doc.fontSize(14).text("Skills");
doc.fontSize(11).text("TypeScript, React, Node.js, Python, PostgreSQL");

doc.end();
console.log(`[make-sample-pdf] wrote -> ${out}`);
```

- [ ] **Step 3: Generate the fixture.** Run: `cd web && node test/fixtures/make-sample-pdf.mjs` — Expected: logs `wrote -> .../test/fixtures/sample-resume.pdf`. Confirm it is a real PDF: `cd web && head -c 5 test/fixtures/sample-resume.pdf` prints `%PDF-`.

- [ ] **Step 4: Commit.** (Commit the binary fixture so CI does not need to regenerate it.)
  - `git add web/package.json web/package-lock.json web/test/fixtures/make-sample-pdf.mjs web/test/fixtures/sample-resume.pdf`
  - `git commit -m "test(web): add sample-resume PDF fixture and generator"`

### Task 4: Playwright smoke spec (stubbed Gemini, full happy path)

Intercepts every Gemini call, seeds the API key via `localStorage` (matching `settings.ts` keys), uploads the fixture PDF, and asserts the Results screen renders the total and a category name. The three Gemini calls (extraction, scoring, coach) are disambiguated by distinctive keys in the request body's `responseSchema`.

**Files:**
- Create: `web/e2e/smoke.spec.ts`

Steps:

- [ ] **Step 1: Write the smoke spec.** Create `web/e2e/smoke.spec.ts`:

```ts
import { test, expect } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const FIXTURE = resolve(here, "../test/fixtures/sample-resume.pdf");

// Schema-valid canned payloads (satisfy JSONResumeSchema / EvaluationSchema / CoachSchema).
const RESUME = {
  basics: { name: "Test Candidate", email: "test@example.com", profiles: [] },
  work: [{ name: "Acme Corp", position: "Software Engineer", highlights: ["Shipped TS services"] }],
  skills: [{ name: "TypeScript" }, { name: "React" }],
  projects: [{ name: "open-source-tool", description: "CLI used by 1k+ devs" }],
};

// open_source 28/35 + self_projects 21/30 + production 15/25 + technical_skills 8/10
// = 72, + bonus 5 - deductions 0 = total 77.
const EVAL = {
  scores: {
    open_source: { score: 28, max: 35, evidence: "Maintains a popular CLI." },
    self_projects: { score: 21, max: 30, evidence: "Several shipped side projects." },
    production: { score: 15, max: 25, evidence: "Production TS services at Acme." },
    technical_skills: { score: 8, max: 10, evidence: "Broad, current stack." },
  },
  bonus_points: { total: 5, breakdown: "Active OSS maintainer." },
  deductions: { total: 0, reasons: "None." },
  key_strengths: ["Strong TypeScript", "Open-source maintainer"],
  areas_for_improvement: ["More production-scale ownership"],
};

const COACH = {
  verdict: "Solid mid-level engineer with strong open-source signal.",
  fixes: [
    { priority: 1, category: "open_source", title: "Land reviewed PRs in major repos", detail: "Target 3 merged PRs in widely-used projects.", estGain: 5 },
  ],
  boosts: [
    { category: "technical_skills", text: "Add a typed test suite to your CLI.", estGain: 2 },
  ],
};

function geminiBody(obj: unknown) {
  // Mimic the @google/genai generateContent REST response: the SDK reads
  // candidates[0].content.parts[*].text and exposes it as `res.text`.
  return JSON.stringify({
    candidates: [
      { content: { role: "model", parts: [{ text: JSON.stringify(obj) }] }, finishReason: "STOP" },
    ],
    usageMetadata: { promptTokenCount: 1, candidatesTokenCount: 1, totalTokenCount: 2 },
  });
}

test("scores a resume end-to-end with stubbed Gemini", async ({ page }) => {
  // Stub every Gemini call. Disambiguate by distinctive responseSchema keys.
  await page.route("https://generativelanguage.googleapis.com/**", async (route) => {
    const body = route.request().postData() ?? "";
    let payload: unknown = RESUME;
    if (body.includes('"verdict"')) payload = COACH;
    else if (body.includes('"key_strengths"')) payload = EVAL;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: geminiBody(payload),
    });
  });

  // Seed a remembered Gemini key (matches settings.ts LS keys) before app boot.
  await page.addInitScript(() => {
    localStorage.setItem("ha-remember-keys", "true");
    localStorage.setItem("ha-gemini-key", "test-key");
    localStorage.setItem("ha-github-token", "");
    localStorage.setItem("ha-model", "gemini-2.5-flash");
    localStorage.setItem("ha-enable-github", "false");
  });

  await page.goto("/");

  // Upload the fixture PDF into the (possibly hidden) file input.
  const input = page.locator('input[type="file"]');
  await expect(input).toBeAttached();
  await input.setInputFiles(FIXTURE);

  // The Score flow runs the pipeline then router.push("/results?run=<id>").
  await page.waitForURL("**/results?run=*", { timeout: 60_000 });

  // Results screen renders the total and at least one category name.
  await expect(page.getByText("OPEN_SOURCE")).toBeVisible();
  await expect(page.getByText(/\b77\b/)).toBeVisible();
});
```

- [ ] **Step 2: Install the Chromium browser (one time).** Run: `cd web && npx playwright install --with-deps chromium` — Expected: Chromium downloads/installs without error.

- [ ] **Step 3: Run the smoke.** Run: `cd web && npm run e2e` — Expected: Playwright boots `next dev`, the single test passes (the `/results` URL is reached and both assertions hold). If the Results screen markup differs, adjust only the two `getByText` assertions; the route-stub and flow are fixed.

- [ ] **Step 4: Commit.**
  - `git add web/e2e/smoke.spec.ts`
  - `git commit -m "test(web): add Playwright smoke for stubbed score-to-results flow"`

### Task 5: Vercel config and README

Deploy-readiness: a `web/vercel.json` pinning the Next.js framework (static export is automatic from `output: "export"`), plus a `web/README.md` documenting install, runtime-key entry (never env vars), local dev/build, Vercel deploy with Root Directory = `web`, and the spec caveat that the TS port's scores are indicative.

**Files:**
- Create: `web/vercel.json`
- Create: `web/README.md`

Steps:

- [ ] **Step 1: Write `web/vercel.json`.** Create `web/vercel.json`:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "outputDirectory": "out",
  "installCommand": "npm install",
  "github": { "silent": true }
}
```

- [ ] **Step 2: Write `web/README.md`.** Create `web/README.md`:

```markdown
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
```

- [ ] **Step 3: Build-verify nothing broke.** Run: `cd web && npm run build` — Expected: static export still succeeds.

- [ ] **Step 4: Commit.**
  - `git add web/vercel.json web/README.md`
  - `git commit -m "chore(web): add Vercel config and deploy README"`


---

## Self-review (coverage of Part 2 against the spec)

Checked each spec requirement against a concrete task; verified cross-phase type/name consistency against the real Part 1 exports.

| Spec requirement | Where |
|---|---|
| Four screens — Score / Results / History & Trends / Settings | Phases H · I · J · K ✓ |
| Tabbed app shell + navigation (overall-structure decision B) | Phase G (`AppShell`) ✓ |
| IndexedDB run history (`store.ts` via `idb`) + `pdfBlob` | Phase E ✓ |
| `localStorage` settings + **remember-key** session-only fallback | Phase E (`settings.ts`, `SettingsProvider`) ✓ |
| Single combined extraction → score → coach pipeline | Reuses Part 1 `runScoreWithRealDeps`; wired in Phase H ✓ |
| Results: verdict + scorecard (total /120 + delta) + 4 category rows | Phase I (`ResultsScreen`, `CategoryRow`) ✓ |
| Signature **revision rail** + run-to-run **diff** | Phase I (`RevisionRail`, `DiffScreen`) ✓ |
| Coach: "biggest score left on the table" + "small boosts" | Phase I (`CoachSection`) ✓ |
| Trends: total-score-over-time chart | Phase F (math) + Phase J (`TotalChart`) ✓ |
| Trends: per-category sparklines | Phase F + Phase J (`Sparkline`) ✓ |
| History changelog + inline **rename** + per-run **delete** | Phase J (`HistoryTable`, `renameRun`/`deleteRun`) ✓ |
| Summary strip (latest / personal best / net change / runs) | Phase F (`summaryStats`) + Phase J ✓ |
| **Clear all data** (IndexedDB + localStorage, keep theme) | Phase E (`clearAllData`) + Phase K button ✓ |
| One delta vocabulary everywhere (`▲ +N` / `▼ -N`) | Phase G (`Delta`), used by I & J ✓ |
| Persistent 100% PRIVATE chip + modal; theme toggle | Reused from Part 1 via `AppShell` ✓ |
| Error handling (missing key, 429, image-only, invalid output, GitHub degrade) | Phase H (`errorMessage`) over Part 1 errors/pipeline ✓ |
| Playwright smoke (mocked Gemini, upload → results render) | Phase L ✓ |
| Vercel static deploy + pdf.js worker asset + README | Phase L ✓ |
| Visual fidelity to v5 Results / Trends mockups | Phases I & J (scoped styles copied from mockups) ✓ |

**No spec gaps. No type mismatches** against Part 1 (`CoachSchema`, `Evaluation.scores[k].evidence`, `cappedCategory`/`CATEGORY_MAX`/`statusFor`/`statusLabel`/`computeTotal`/`MAX_TOTAL`, `diffRuns(cur, prev|null)`, `runScoreWithRealDeps(file, Settings, onProgress)`), verified by an adversarial audit pass and re-checked here.

**Adjusted during review (baked into the tasks above):**
- `AppShell` renders a **single** `.wrap` container (top bar + content) instead of a doubled max-width wrapper.
- `CoachSection` colors each fix's accent rule by the **boosted category's status** (`statusFor` → `--good`/`--warn`/`--bad`), matching the mockup, rather than a flat brand accent — its prop is now `{ coach, evaluation }`.

**Known minor refinements (non-blocking; left for the executor's judgment):**
1. The Score progress list is a fixed five stages; when GitHub enrichment is skipped (no token / no profile), "Enriching from GitHub" momentarily reads as done. Make `STAGES` conditional on `enableGitHub` if you want it exact.
2. `RevisionRail` shows `label || fileName`; `HistoryTable` shows `fileName` with `label` as a badge — deliberate per context (compact rail vs. detailed table), but unify if a single convention is preferred.
3. A few Phase L file-line references (`package.json`, `pdf.ts`) shift once Phase E adds dev-deps; the edits there are content-based (search/replace), so treat line numbers as hints.

---

## Execution

**REQUIRED SUB-SKILL when executing:** Use `superpowers:subagent-driven-development` (recommended — fresh subagent per task with review between) or `superpowers:executing-plans` (inline, batched with checkpoints). Phases are independently committable and ordered so **every commit builds green**: E → F → G → H → I → J → K → L.


