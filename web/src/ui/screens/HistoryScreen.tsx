// web/src/ui/screens/HistoryScreen.tsx
"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import type { RunRecord } from "../../lib/schemas";
import { CATEGORY_KEYS } from "../../lib/schemas";
import { listRuns, renameRun, deleteRun } from "../../lib/store";
import { totalSeries, categorySeries, summaryStats } from "../../lib/trends";
import { CATEGORY_MAX, statusFor } from "../../lib/scoring";
import { shortDate } from "../../lib/format";
import { TotalChart } from "../TotalChart";
import { Sparkline } from "../Sparkline";
import { HistoryTable } from "../HistoryTable";
import { EmptyState } from "../EmptyState";
import { Delta } from "../Delta";

function formatShort(ts: number | null): string {
  return ts === null ? "—" : shortDate(ts);
}

const LOAD_ERROR = "Could not load your history. Your browser may be blocking local storage.";

export function HistoryScreen() {
  const [runs, setRuns] = useState<RunRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      setRuns(await listRuns());
    } catch {
      setError(LOAD_ERROR);
      setRuns([]); // leave the loading state even on failure
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const handleRename = useCallback(
    async (id: string, label: string) => {
      try {
        await renameRun(id, label);
        await reload();
      } catch {
        setError(LOAD_ERROR);
      }
    },
    [reload],
  );

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await deleteRun(id);
        await reload();
      } catch {
        setError(LOAD_ERROR);
      }
    },
    [reload],
  );

  if (error) {
    return <EmptyState message={error} />;
  }

  if (runs === null) return null;

  if (runs.length === 0) {
    return (
      <div className="ha-empty">
        <div className="eyebrow">History &amp; Trends</div>
        <h1 className="serif ha-empty-title">No runs yet.</h1>
        <p className="ha-empty-text">Score a resume to start tracking your progress over time.</p>
        <Link href="/" className="ha-empty-cta">
          Score a resume →
        </Link>
        <style>{`
          .ha-empty{margin:60px auto;max-width:480px;text-align:center}
          .ha-empty-title{font-weight:400;font-size:clamp(28px,3.6vw,40px);line-height:1.05;margin:6px 0 10px}
          .ha-empty-text{color:var(--ink-soft);margin:0 0 22px}
          .ha-empty-cta{font-family:var(--font-jetbrains-mono),monospace;font-size:13px;color:var(--brand-ink);background:var(--brand-tint);border:1px solid color-mix(in srgb,var(--brand) 32%,transparent);padding:9px 16px;border-radius:9px;text-decoration:none}
          .ha-empty-cta:hover{border-color:var(--brand)}
        `}</style>
      </div>
    );
  }

  const series = totalSeries(runs);
  const summary = summaryStats(runs);
  const lastDelta =
    series.length >= 2 ? series[series.length - 1].total - series[series.length - 2].total : null;

  return (
    <>
      <div className="ha-page-head">
        <div>
          <div className="eyebrow">History &amp; Trends</div>
          <h1 className="serif ha-page-title">Your resume, over time.</h1>
        </div>
      </div>

      <div className="ha-stats">
        <div className="ha-stat">
          <div className="ha-stat-lbl">Latest score</div>
          <div className="ha-stat-val">
            {summary.latest}
            <small>/120</small>
          </div>
          <div className="ha-stat-sub">
            <Delta value={lastDelta} suffix="vs. last" />
          </div>
        </div>
        <div className="ha-stat">
          <div className="ha-stat-lbl">Personal best</div>
          <div className="ha-stat-val">
            {summary.personalBest}
            <small>/120</small>
          </div>
          <div className="ha-stat-sub">
            {summary.personalBest === summary.latest ? "Also the latest" : "Across all runs"}
          </div>
        </div>
        <div className="ha-stat">
          <div className="ha-stat-lbl">Net change</div>
          <div className="ha-stat-val">
            <Delta value={summary.netChange} />
          </div>
          <div className="ha-stat-sub">Since your first run</div>
        </div>
        <div className="ha-stat">
          <div className="ha-stat-lbl">Runs</div>
          <div className="ha-stat-val">{summary.runCount}</div>
          <div className="ha-stat-sub">
            {formatShort(summary.firstAt)} → {formatShort(summary.lastAt)}
          </div>
        </div>
      </div>

      <div className="ha-panel">
        <div className="ha-panel-head">
          <div className="ha-panel-title serif">Total score</div>
          <div className="ha-panel-note">
            {summary.runCount} {summary.runCount === 1 ? "run" : "runs"} · out of 120
          </div>
        </div>
        <TotalChart series={series} />
      </div>

      <div className="ha-spark-grid">
        {CATEGORY_KEYS.map((key) => {
          const values = categorySeries(runs, key);
          const latest = values.length > 0 ? values[values.length - 1] : 0;
          const catDelta = values.length >= 2 ? latest - values[values.length - 2] : null;
          const status = statusFor(latest, CATEGORY_MAX[key]);
          return (
            <div className="ha-spark" key={key}>
              <div className="ha-spark-name">{key.toUpperCase()}</div>
              <div className="ha-spark-row">
                <span className="ha-spark-val">
                  {latest}
                  <small>/{CATEGORY_MAX[key]}</small>
                </span>
                <Delta value={catDelta} />
              </div>
              <Sparkline values={values} status={status} />
            </div>
          );
        })}
      </div>

      <div className="ha-history">
        <div className="eyebrow ha-history-eyebrow">Run history</div>
        <HistoryTable runs={runs} onRename={handleRename} onDelete={handleDelete} />
      </div>

      <style>{`
        .ha-page-head{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;margin:26px 0 22px;flex-wrap:wrap}
        .ha-page-title{font-weight:400;font-size:clamp(28px,3.6vw,40px);line-height:1.05;margin:6px 0 0}
        .ha-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}
        .ha-stat{background:var(--panel);border:1px solid var(--rule);border-radius:12px;padding:15px 16px;box-shadow:var(--shadow)}
        .ha-stat-lbl{font-family:var(--font-jetbrains-mono),monospace;font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-soft)}
        .ha-stat-val{font-family:var(--font-jetbrains-mono),monospace;font-weight:700;font-size:27px;margin-top:7px;letter-spacing:-.01em}
        .ha-stat-val small{font-size:14px;color:var(--ink-soft);font-weight:500}
        .ha-stat-sub{font-family:var(--font-jetbrains-mono),monospace;font-size:11px;margin-top:3px;color:var(--ink-soft)}
        .ha-panel{background:var(--panel);border:1px solid var(--rule);border-radius:14px;box-shadow:var(--shadow);padding:20px 22px}
        .ha-panel-head{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-bottom:6px}
        .ha-panel-title{font-size:22px}
        .ha-panel-note{font-family:var(--font-jetbrains-mono),monospace;font-size:11px;color:var(--ink-soft)}
        .ha-spark-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:16px}
        .ha-spark{background:var(--panel);border:1px solid var(--rule);border-radius:12px;padding:15px 16px;box-shadow:var(--shadow)}
        .ha-spark-name{font-family:var(--font-jetbrains-mono),monospace;font-size:11px;letter-spacing:.05em;font-weight:500;color:var(--ink-soft)}
        .ha-spark-row{display:flex;align-items:baseline;justify-content:space-between;margin-top:8px}
        .ha-spark-val{font-family:var(--font-jetbrains-mono),monospace;font-weight:700;font-size:19px}
        .ha-spark-val small{font-size:12px;color:var(--ink-soft);font-weight:500}
        .ha-spark svg{width:100%;height:40px;margin-top:10px;display:block}
        .ha-history{margin-top:26px}
        .ha-history-eyebrow{margin-bottom:12px}
        @media(max-width:760px){.ha-stats{grid-template-columns:repeat(2,1fr)}.ha-spark-grid{grid-template-columns:repeat(2,1fr)}}
      `}</style>
    </>
  );
}
