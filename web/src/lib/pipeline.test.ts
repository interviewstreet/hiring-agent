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
    expect((d.runScoring as any).mock.calls[0][0]).toContain("=== GITHUB DATA ===");
  });

  it("skips github enrichment when enabled but no github profile is present", async () => {
    const d = deps({
      settings: { geminiKey: "k", githubToken: "t", model: "m", enableGitHub: true },
      runExtraction: vi.fn(async () => ({ basics: { name: "NoGit", profiles: [] } })),
    });
    const rec = await scoreResume(new ArrayBuffer(0), d as any);
    expect(d.fetchGitHub).not.toHaveBeenCalled();
    expect(rec.githubSummary).toBeNull();
  });
});
