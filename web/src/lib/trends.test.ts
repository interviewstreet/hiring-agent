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
      yFor: expect.any(Function),
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
