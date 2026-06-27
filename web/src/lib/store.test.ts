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

  it("keeps a run retrievable in memory even if the DB write is rejected", async () => {
    const run = makeRun("r1", 100);
    // A function field can't be structured-cloned, so the IndexedDB write
    // rejects — standing in for the real failure (e.g. a Blob in a private
    // window, or an exceeded quota) where db.put cannot persist the record.
    (run as unknown as { unclonable: () => void }).unclonable = () => {};

    await expect(saveRun(run)).rejects.toThrow();

    // The run was mirrored in memory before the failed write, so a completed
    // run is never discarded — it still loads for the rest of this session.
    expect((await getRun("r1"))?.id).toBe("r1");
  });

  it("deleteRun also drops the in-memory mirror", async () => {
    const run = makeRun("r1", 100);
    (run as unknown as { unclonable: () => void }).unclonable = () => {};
    await expect(saveRun(run)).rejects.toThrow();

    await deleteRun("r1");
    expect(await getRun("r1")).toBeUndefined();
  });
});
