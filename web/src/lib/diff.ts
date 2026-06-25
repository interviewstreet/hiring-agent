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
