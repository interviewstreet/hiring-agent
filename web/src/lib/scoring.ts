import type { Evaluation, CategoryKey } from "./schemas";
import { CATEGORY_KEYS } from "./schemas";

export const CATEGORY_MAX: Record<CategoryKey, number> = {
  open_source: 35,
  self_projects: 30,
  production: 25,
  technical_skills: 10,
};

export const MAX_TOTAL = 120;
export type Status = "good" | "warn" | "bad";

export function cappedCategory(ev: Evaluation, key: CategoryKey): number {
  const s = ev.scores[key];
  return Math.min(s.score, CATEGORY_MAX[key]);
}

export function computeTotal(ev: Evaluation): number {
  const categories = CATEGORY_KEYS.reduce((sum, k) => sum + cappedCategory(ev, k), 0);
  const raw = categories + ev.bonus_points.total - ev.deductions.total;
  // Clamp to [0, 120] per the scoring spec. Python's evaluator.py defines
  // MIN_FINAL_SCORE = -20 but never enforces it (dead code), so 0 is the
  // effective floor in score.py's reporting.
  return Math.max(0, Math.min(MAX_TOTAL, raw));
}

export function statusFor(score: number, max: number): Status {
  const ratio = max > 0 ? score / max : 0;
  if (ratio >= 0.7) return "good";
  if (ratio >= 0.4) return "warn";
  return "bad";
}
