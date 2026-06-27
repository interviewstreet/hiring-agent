"use client";
import type { CategoryKey, Evaluation } from "@/lib/schemas";
import { cappedCategory, CATEGORY_MAX, statusFor, statusLabel } from "@/lib/scoring";
import { Delta } from "@/ui/Delta";

export function CategoryRow({ ckey, ev, delta }: { ckey: CategoryKey; ev: Evaluation; delta: number | null }) {
  const max = CATEGORY_MAX[ckey];
  const capped = cappedCategory(ev, ckey);
  const status = statusFor(capped, max);
  const width = Math.round((capped / max) * 100);

  return (
    <div className="cat">
      <div>
        <div className="cat-name mono">{ckey.toUpperCase()}</div>
        <div className="cat-ev">{ev.scores[ckey].evidence}</div>
        <div className="track">
          <div className={`fill b-${status}`} style={{ width: `${width}%` }} />
        </div>
      </div>
      <div className="cat-right">
        <span className="cat-score mono">
          {capped}
          <small>/{max}</small>
        </span>
        <span className={`status mono s-${status}`}>{statusLabel(status)}</span>
        <Delta value={delta} />
      </div>
      <style>{`
        .cat{display:grid;grid-template-columns:1fr 150px;gap:18px;align-items:center;padding:16px 2px;border-top:1px solid var(--rule)}
        .cat:first-child{border-top:none}
        .cat-name{font-size:12px;letter-spacing:.06em;font-weight:500}
        .cat-ev{color:var(--ink-soft);font-size:13px;margin-top:3px;max-width:80ch}
        .track{height:8px;border-radius:6px;background:var(--rule);overflow:hidden;margin-top:10px}
        .fill{height:100%;border-radius:6px}
        .b-good{background:var(--good)} .b-warn{background:var(--warn)} .b-bad{background:var(--bad)}
        .cat-right{text-align:right}
        .cat-score{font-weight:700;font-size:16px}
        .cat-score small{color:var(--ink-soft);font-weight:500}
        .status{font-size:11px;letter-spacing:.05em;text-transform:uppercase;display:block;margin-top:2px}
        .s-good{color:var(--good)} .s-warn{color:var(--warn)} .s-bad{color:var(--bad)}
        .cat-right .delta{display:block;margin-top:4px}
      `}</style>
    </div>
  );
}
