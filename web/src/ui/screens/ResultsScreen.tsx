"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import type { RunRecord } from "@/lib/schemas";
import { CATEGORY_KEYS } from "@/lib/schemas";
import { computeTotal, MAX_TOTAL } from "@/lib/scoring";
import { diffRuns } from "@/lib/diff";
import { getRun, listRuns } from "@/lib/store";
import { CategoryRow } from "@/ui/CategoryRow";
import { RevisionRail } from "@/ui/RevisionRail";
import { CoachSection } from "@/ui/CoachSection";
import { EmptyState } from "@/ui/EmptyState";
import { Delta } from "@/ui/Delta";

export function ResultsScreen() {
  const params = useSearchParams();
  const id = params.get("run");
  const [loading, setLoading] = useState(true);
  const [run, setRun] = useState<RunRecord | null>(null);
  const [prev, setPrev] = useState<RunRecord | null>(null);
  const [runs, setRuns] = useState<RunRecord[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      if (!id) {
        if (!cancelled) {
          setRun(null);
          setPrev(null);
          setRuns([]);
          setLoading(false);
        }
        return;
      }
      const [cur, all] = await Promise.all([getRun(id), listRuns()]);
      if (cancelled) return;
      // listRuns() returns runs ascending by createdAt; pick the positional
      // previous element so the scorebar delta matches RevisionRail's by construction.
      const idx = cur ? all.findIndex((r) => r.id === cur.id) : -1;
      setRun(cur ?? null);
      setPrev(idx > 0 ? all[idx - 1] : null);
      setRuns(all);
      setLoading(false);
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading) {
    return <p className="empty">Loading score report…</p>;
  }

  if (!run) {
    return <EmptyState message="That score report could not be found." />;
  }

  const diff = diffRuns(run, prev);
  const total = computeTotal(run.evaluation);
  const prevLabel = prev ? prev.label || prev.fileName : null;

  return (
    <div className="layout">
      <RevisionRail runs={runs} currentId={run.id} />

      <div className="report">
        <div className="report-head">
          <div className="eyebrow">Score report · {run.label || run.fileName}</div>
          <h1 className="verdict serif">{run.coach.verdict}</h1>
        </div>

        <div className="scorebar">
          <div className="total mono">
            {total}
            <small>/{MAX_TOTAL}</small>
          </div>
          <div className="total-side">
            <span className="lbl mono">{prevLabel ? `vs. ${prevLabel}` : "first run"}</span>
            <Delta value={diff.total} />
          </div>
        </div>

        <div className="cats">
          {CATEGORY_KEYS.map((k) => (
            <CategoryRow key={k} ckey={k} ev={run.evaluation} delta={diff.byCategory[k]} />
          ))}
        </div>

        <CoachSection coach={run.coach} evaluation={run.evaluation} />
      </div>

      <style>{`
        .layout{display:grid;grid-template-columns:212px 1fr;gap:30px;margin-top:26px}
        .report-head .eyebrow{margin-bottom:10px}
        .verdict{font-weight:400;font-size:clamp(26px,3.2vw,38px);line-height:1.16;letter-spacing:.1px;margin:0 0 4px;max-width:42ch}
        .verdict em{font-style:italic;color:var(--brand-ink)}
        .scorebar{display:flex;align-items:flex-end;gap:18px;margin:22px 0 28px;padding:18px 20px;background:var(--panel);border:1px solid var(--rule);border-radius:14px;box-shadow:var(--shadow);position:relative;overflow:hidden;background-image:linear-gradient(var(--rule) 1px,transparent 1px),linear-gradient(90deg,var(--rule) 1px,transparent 1px);background-size:22px 22px;background-position:right -1px bottom -1px}
        .scorebar:after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,var(--panel) 52%,transparent)}
        .scorebar > *{position:relative;z-index:1}
        .total{font-weight:700;font-size:54px;line-height:.9;letter-spacing:-.02em}
        .total small{font-size:20px;color:var(--ink-soft);font-weight:500}
        .total-side{padding-bottom:6px}
        .total-side .lbl{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-soft);display:block}
        .total-side .delta{font-size:18px;margin-top:2px;display:block}
        @media(max-width:760px){ .layout{grid-template-columns:1fr} }
      `}</style>
    </div>
  );
}
