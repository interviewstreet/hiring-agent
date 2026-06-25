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
