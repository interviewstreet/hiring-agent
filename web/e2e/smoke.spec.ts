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
  // Scope to specific containers: "OPEN_SOURCE" also appears in the coach fix
  // header, and "77/120" also appears in the revision rail, so unscoped text
  // locators would resolve to 2 elements (Playwright strict-mode violation).
  await expect(page.locator(".cats")).toContainText("OPEN_SOURCE");
  await expect(page.locator(".scorebar .total")).toContainText("77");
});
