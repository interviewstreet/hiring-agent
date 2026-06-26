"use client";
import Link from "next/link";
import type { RunRecord } from "@/lib/schemas";
import { computeTotal, MAX_TOTAL } from "@/lib/scoring";
import { Delta } from "@/ui/Delta";

function fmtDate(ms: number): string {
  const d = new Date(ms);
  const now = new Date();
  const time = d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", hour12: false });
  const sameDay =
    d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
  const day = sameDay ? "today" : d.toLocaleDateString(undefined, { month: "short", day: "2-digit" });
  return `${day} · ${time}`;
}

export function RevisionRail({ runs, currentId }: { runs: RunRecord[]; currentId: string }) {
  const ascending = [...runs].sort((a, b) => a.createdAt - b.createdAt);
  const rows = ascending.map((run, i) => {
    const prev = i > 0 ? ascending[i - 1] : null;
    const total = computeTotal(run.evaluation);
    const delta = prev ? total - computeTotal(prev.evaluation) : null;
    return { run, prev, total, delta };
  });

  return (
    <aside className="rail">
      <div className="eyebrow">Revisions</div>
      <div className="runs">
        {[...rows].reverse().map(({ run, prev, total, delta }) => {
          const isCur = run.id === currentId;
          return (
            <div key={run.id} className={isCur ? "run cur" : "run"}>
              <div className="run-v mono">{run.label || run.fileName}</div>
              <div className="run-meta mono">{fmtDate(run.createdAt)}</div>
              <div className="run-delta">
                <Delta value={delta} />
                <span className="soft mono">
                  &nbsp;{total}/{MAX_TOTAL}
                </span>
              </div>
              {isCur && prev && (
                <Link
                  className="compare mono"
                  href={`/diff?a=${run.id}&b=${prev.id}`}
                  aria-label="Compare with previous revision"
                >
                  <span aria-hidden="true">⇄</span> diff
                </Link>
              )}
            </div>
          );
        })}
      </div>
      <style>{`
        .rail .eyebrow{margin-bottom:16px}
        .runs{position:relative;padding-left:18px}
        .runs:before{content:"";position:absolute;left:4px;top:6px;bottom:14px;width:2px;background:var(--rule)}
        .run{position:relative;padding:0 0 18px 4px}
        .run:before{content:"";position:absolute;left:-18px;top:4px;width:9px;height:9px;border-radius:50%;background:var(--paper);border:2px solid var(--ink-soft)}
        .run.cur:before{background:var(--brand);border-color:var(--brand);box-shadow:0 0 0 4px var(--brand-tint)}
        .run-v{font-weight:500;font-size:13px}
        .run.cur .run-v{color:var(--brand-ink)}
        .run-meta{font-size:11px;color:var(--ink-soft);margin-top:1px}
        .run-delta{margin-top:2px;font-size:11px}
        .soft{color:var(--ink-soft);font-weight:500}
        .compare{display:inline-block;margin-top:6px;font-size:11px;color:var(--brand-ink);border:1px dashed var(--brand);border-radius:7px;padding:7px 9px;background:var(--brand-tint);text-decoration:none}
        .compare:focus-visible{outline:2px solid var(--brand);outline-offset:2px}
        @media(max-width:760px){ .runs:before{display:none} }
      `}</style>
    </aside>
  );
}
