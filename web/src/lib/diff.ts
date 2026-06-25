/**
 * Run-to-run score diffing: total and per-category deltas between a run and
 * the previous one. Reuses the capping/total logic in scoring.ts so deltas
 * reflect the same numbers shown elsewhere in the UI.
 */
import type { RunRecord, CategoryKey } from "./schemas";
import { CATEGORY_KEYS } from "./schemas";
import { cappedCategory, computeTotal } from "./scoring";

export type RunDiff =
  | { total: null; byCategory: Record<CategoryKey, null> }
  | { total: number; byCategory: Record<CategoryKey, number> };

export function diffRuns(cur: RunRecord, prev: RunRecord | null): RunDiff {
  if (!prev) {
    return {
      total: null,
      byCategory: { open_source: null, self_projects: null, production: null, technical_skills: null },
    };
  }
  const byCategory = {} as Record<CategoryKey, number>;
  for (const k of CATEGORY_KEYS) {
    byCategory[k] = cappedCategory(cur.evaluation, k) - cappedCategory(prev.evaluation, k);
  }
  return { total: computeTotal(cur.evaluation) - computeTotal(prev.evaluation), byCategory };
}
