// web/src/ui/HistoryTable.tsx
"use client";
import Link from "next/link";
import type { RunRecord } from "../lib/schemas";
import { computeTotal } from "../lib/scoring";
import { diffRuns } from "../lib/diff";
import { dateTime } from "../lib/format";
import { Delta } from "./Delta";

export function HistoryTable({
  runs,
  onRename,
  onDelete,
}: {
  runs: RunRecord[];
  onRename: (id: string, label: string) => void;
  onDelete: (id: string) => void;
}) {
  // ascending in -> pair with previous (older) -> reverse to newest-first.
  const rows = runs.map((run, i) => ({ run, prev: i > 0 ? runs[i - 1] : null }));
  rows.reverse();

  function handleRename(run: RunRecord) {
    const result = window.prompt("Label for this revision", run.label ?? "");
    const next = result?.trim();
    // cancel (null) = no-op; empty/whitespace = no-op; non-empty = rename.
    if (result !== null && next) onRename(run.id, next);
  }

  function handleDelete(run: RunRecord) {
    if (window.confirm(`Delete "${run.label || run.fileName}"? This cannot be undone.`)) {
      onDelete(run.id);
    }
  }

  return (
    <table className="ha-htable">
      <thead>
        <tr>
          <th>Revision</th>
          <th className="hide">Date</th>
          <th className="r">Score</th>
          <th className="r">Δ</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {rows.map(({ run, prev }) => {
          const d = diffRuns(run, prev);
          return (
            <tr key={run.id}>
              <td>
                <span className="ha-h-name">{run.fileName}</span>
                {run.label && <span className="ha-h-label">{run.label}</span>}
                <button className="ha-h-rename" onClick={() => handleRename(run)}>
                  rename
                </button>
              </td>
              <td className="ha-h-date hide">{dateTime(run.createdAt)}</td>
              <td className="r ha-h-total">{computeTotal(run.evaluation)}</td>
              <td className="r">
                <Delta value={d.total} />
              </td>
              <td className="r">
                <Link className="ha-h-act" href={`/results?run=${run.id}`}>
                  View
                </Link>{" "}
                {prev && (
                  <>
                    <Link className="ha-h-act diff" href={`/diff?a=${run.id}&b=${prev.id}`}>
                      Diff
                    </Link>{" "}
                  </>
                )}
                <button className="ha-h-act del" onClick={() => handleDelete(run)}>
                  Delete
                </button>
              </td>
            </tr>
          );
        })}
      </tbody>
      <style>{`
        .ha-htable{width:100%;border-collapse:collapse}
        .ha-htable th{font-family:var(--font-jetbrains-mono),monospace;font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-soft);text-align:left;font-weight:500;padding:0 12px 10px;border-bottom:1px solid var(--rule)}
        .ha-htable th.r,.ha-htable td.r{text-align:right}
        .ha-htable td{padding:14px 12px;border-bottom:1px solid var(--rule);vertical-align:middle}
        .ha-htable tr:hover td{background:var(--panel-2)}
        .ha-h-name{font-family:var(--font-jetbrains-mono),monospace;font-weight:500;font-size:13.5px}
        .ha-h-label{display:inline-block;font-family:var(--font-archivo),sans-serif;font-size:11px;color:var(--brand-ink);background:var(--brand-tint);border-radius:6px;padding:1px 7px;margin-left:8px}
        .ha-h-rename{font-family:var(--font-archivo),sans-serif;color:var(--ink-soft);font-size:11px;margin-left:8px;background:transparent;border:none;border-bottom:1px dotted var(--ink-soft);padding:0;cursor:pointer;opacity:0;transition:opacity .15s}
        .ha-htable tr:hover .ha-h-rename,
        .ha-h-rename:focus-visible{opacity:1}
        .ha-h-date{font-family:var(--font-jetbrains-mono),monospace;color:var(--ink-soft);font-size:12.5px}
        .ha-h-total{font-family:var(--font-jetbrains-mono),monospace;font-weight:700;font-size:15px}
        .ha-h-act{font-family:var(--font-jetbrains-mono),monospace;font-size:11.5px;color:var(--ink);text-decoration:none;background:transparent;border:1px solid var(--rule);padding:5px 10px;border-radius:7px;cursor:pointer}
        .ha-h-act:hover{border-color:var(--brand);color:var(--brand-ink)}
        .ha-h-act.diff{color:var(--ink-soft)}
        .ha-h-act.del{color:var(--bad)}
        .ha-h-act.del:hover{border-color:var(--bad);color:var(--bad)}
        @media(max-width:760px){.ha-h-date.hide,.ha-htable .hide{display:none}}
        @media (prefers-reduced-motion: reduce){.ha-h-rename{transition:none}}
      `}</style>
    </table>
  );
}
