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
  it("computes negative deltas when the score drops", () => {
    const prev = make({ open_source: 28 });
    const cur = make({ open_source: 18 });
    const d = diffRuns(cur, prev);
    expect(d.total).toBe(-10);
    expect(d.byCategory.open_source).toBe(-10);
  });
  it("reflects a bonus change in the total delta", () => {
    const prev = make({});
    const cur = make({});
    cur.evaluation.bonus_points.total = 8;
    const d = diffRuns(cur, prev);
    expect(d.total).toBe(8);
  });
});
