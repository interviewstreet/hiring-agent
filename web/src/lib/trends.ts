/**
 * Pure math for the Trends screen: per-run series, aggregate stats, and SVG
 * path builders. No DOM/IndexedDB/React — everything here is deterministic and
 * unit-tested. Totals/caps come from scoring.ts so trend numbers match the
 * rest of the UI exactly.
 */
import type { RunRecord, CategoryKey } from "./schemas";
import { computeTotal, cappedCategory } from "./scoring";

export type SeriesPoint = {
  id: string;
  createdAt: number;
  label: string;
  total: number;
};

function byCreatedAtAsc(runs: RunRecord[]): RunRecord[] {
  return [...runs].sort((a, b) => a.createdAt - b.createdAt);
}

// Render path coordinates as clean strings (drop float noise like 49.99999).
function fmt(n: number): string {
  return Number.isInteger(n) ? String(n) : String(Math.round(n * 1000) / 1000);
}

export function totalSeries(runs: RunRecord[]): SeriesPoint[] {
  return byCreatedAtAsc(runs).map((r) => ({
    id: r.id,
    createdAt: r.createdAt,
    label: r.label || r.fileName,
    total: computeTotal(r.evaluation),
  }));
}

export function categorySeries(runs: RunRecord[], key: CategoryKey): number[] {
  return byCreatedAtAsc(runs).map((r) => cappedCategory(r.evaluation, key));
}

export type TrendSummary = {
  latest: number;
  personalBest: number;
  netChange: number;
  runCount: number;
  firstAt: number | null;
  lastAt: number | null;
};

export function summaryStats(runs: RunRecord[]): TrendSummary {
  if (runs.length === 0) {
    return {
      latest: 0,
      personalBest: 0,
      netChange: 0,
      runCount: 0,
      firstAt: null,
      lastAt: null,
    };
  }
  const sorted = byCreatedAtAsc(runs);
  const totals = sorted.map((r) => computeTotal(r.evaluation));
  const first = totals[0];
  const last = totals[totals.length - 1];
  return {
    latest: last,
    personalBest: Math.max(...totals),
    netChange: last - first,
    runCount: sorted.length,
    firstAt: sorted[0].createdAt,
    lastAt: sorted[sorted.length - 1].createdAt,
  };
}

export function buildLinePath(
  values: number[],
  opts: { w: number; h: number; pad: number; maxY: number }
): { line: string; area: string; points: { x: number; y: number }[]; yFor: (v: number) => number } {
  const { w, h, pad, maxY } = opts;
  const innerH = h - 2 * pad;
  const yFor = (v: number): number => h - pad - (maxY > 0 ? v / maxY : 0) * innerH;
  if (values.length === 0) return { line: "", area: "", points: [], yFor };

  const n = values.length;
  const xFor = (i: number): number => (n === 1 ? w / 2 : pad + (i * (w - 2 * pad)) / (n - 1));

  const points = values.map((v, i) => ({ x: xFor(i), y: yFor(v) }));
  const line = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${fmt(p.x)} ${fmt(p.y)}`)
    .join(" ");

  const baseY = h - pad;
  const first = points[0];
  const last = points[points.length - 1];
  const area = `${line} L${fmt(last.x)} ${fmt(baseY)} L${fmt(first.x)} ${fmt(baseY)} Z`;

  return { line, area, points, yFor };
}

export function buildSparkPath(
  values: number[],
  opts: { w: number; h: number }
): { line: string; area: string } {
  const { w, h } = opts;
  if (values.length === 0) return { line: "", area: "" };

  const padY = h * 0.1;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const n = values.length;
  const xFor = (i: number): number => (n === 1 ? w / 2 : (i * w) / (n - 1));
  const yFor = (v: number): number => {
    if (max === min) return h / 2; // flat series => mid-line
    return h - padY - ((v - min) / (max - min)) * (h - 2 * padY);
  };

  const points = values.map((v, i) => ({ x: xFor(i), y: yFor(v) }));
  const line = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${fmt(p.x)} ${fmt(p.y)}`)
    .join(" ");

  const first = points[0];
  const last = points[points.length - 1];
  const area = `${line} L${fmt(last.x)} ${fmt(h)} L${fmt(first.x)} ${fmt(h)} Z`;

  return { line, area };
}
