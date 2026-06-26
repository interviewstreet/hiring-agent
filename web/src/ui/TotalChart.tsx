// web/src/ui/TotalChart.tsx
"use client";
import type { SeriesPoint } from "../lib/trends";
import { buildLinePath } from "../lib/trends";

const W = 720;
const H = 260;
const PAD = 40;
const MAX_Y = 120;
const GRID_VALUES = [0, 30, 60, 90, 120];

// Same vertical mapping buildLinePath uses, so gridlines align with nodes.
function yForValue(v: number): number {
  return H - PAD - (v / MAX_Y) * (H - 2 * PAD);
}

function formatAxisDate(ts: number): string {
  return new Date(ts).toLocaleDateString("en-US", { month: "short", day: "2-digit" });
}

export function TotalChart({ series }: { series: SeriesPoint[] }) {
  const values = series.map((p) => p.total);
  const { line, area, points } = buildLinePath(values, { w: W, h: H, pad: PAD, maxY: MAX_Y });
  const first = series[0]?.total ?? 0;
  const last = series[series.length - 1]?.total ?? 0;
  const label =
    series.length === 0
      ? "Total score over time (no runs yet)"
      : `Total score over time, from ${first} to ${last} out of 120`;

  return (
    <svg className="ha-chart" viewBox={`0 0 ${W} ${H + 12}`} role="img" aria-label={label}>
      {GRID_VALUES.map((v) => {
        const y = yForValue(v);
        return (
          <g key={v}>
            <line className="ha-gridline" x1={PAD} y1={y} x2={W - PAD} y2={y} />
            <text className="ha-axis-lbl" x={PAD - 10} y={y + 4} textAnchor="end">
              {v}
            </text>
          </g>
        );
      })}
      {area && <path className="ha-area" d={area} />}
      {line && <path className="ha-line" d={line} />}
      {points.map((pt, i) => (
        <g key={series[i]?.id ?? i}>
          <circle className="ha-node" cx={pt.x} cy={pt.y} r={4.5} />
          <text className="ha-node-lbl" x={pt.x} y={pt.y - 12} textAnchor="middle">
            {values[i]}
          </text>
          <text className="ha-x-lbl" x={pt.x} y={H + 6} textAnchor="middle">
            {formatAxisDate(series[i].createdAt)}
          </text>
        </g>
      ))}
      <style>{`
        .ha-chart{width:100%;height:auto;display:block;margin-top:8px}
        .ha-gridline{stroke:var(--rule);stroke-width:1}
        .ha-axis-lbl{fill:var(--ink-soft);font-family:var(--font-jetbrains-mono),monospace;font-size:10px}
        .ha-x-lbl{fill:var(--ink-soft);font-family:var(--font-jetbrains-mono),monospace;font-size:10.5px}
        .ha-area{fill:var(--brand-tint)}
        .ha-line{fill:none;stroke:var(--brand);stroke-width:2.5;stroke-linejoin:round;stroke-linecap:round}
        .ha-node{fill:var(--panel);stroke:var(--brand);stroke-width:2.5}
        .ha-node-lbl{fill:var(--ink);font-family:var(--font-jetbrains-mono),monospace;font-weight:700;font-size:12px}
      `}</style>
    </svg>
  );
}
