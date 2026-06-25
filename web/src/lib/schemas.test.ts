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

  it("accepts a JSONResume profile with a null network field", () => {
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
