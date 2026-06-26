"use client";
import type { Coach, Evaluation } from "@/lib/schemas";
import { cappedCategory, CATEGORY_MAX, statusFor } from "@/lib/scoring";
import { Delta } from "@/ui/Delta";

export function CoachSection({ coach, evaluation }: { coach: Coach; evaluation: Evaluation }) {
  return (
    <section className="coach">
      <div className="eyebrow">Coach · what to fix next</div>
      <h2 className="coach-sub serif">Biggest score left on the table</h2>
      <p className="coach-note">High-impact fixes, in priority order.</p>

      {coach.fixes.map((fix, i) => (
        <div
          className="fix"
          key={i}
          style={{
            ["--accent" as string]: `var(--${statusFor(cappedCategory(evaluation, fix.category), CATEGORY_MAX[fix.category])})`,
          }}
        >
          <div className="fix-rule" />
          <div>
            <div className="fix-meta mono">
              Priority {String(fix.priority).padStart(2, "0")} · boosts <b>{fix.category.toUpperCase()}</b>
            </div>
            <h3 className="fix-title serif">{fix.title}</h3>
            <p className="fix-text">{fix.detail}</p>
          </div>
          <div className="gain">
            <Delta value={fix.estGain} />
          </div>
        </div>
      ))}

      {coach.boosts.length > 0 && (
        <div className="boosts">
          <h2 className="coach-sub serif">Small boosts</h2>
          <p className="coach-note">Polish for categories that are already strong — a point or two each.</p>
          {coach.boosts.map((b, i) => (
            <div className="boost" key={i}>
              <span className="boost-tag mono">{b.category.toUpperCase()}</span>
              <span className="boost-text serif">{b.text}</span>
              <span className="boost-gain">
                <Delta value={b.estGain} />
              </span>
            </div>
          ))}
        </div>
      )}

      <style>{`
        .coach{margin-top:36px}
        .coach .eyebrow{margin-bottom:6px}
        .coach-sub{font-size:25px;margin:0 0 4px}
        .coach-note{color:var(--ink-soft);font-size:13.5px;margin:0 0 14px}
        .fix{display:grid;grid-template-columns:3px 1fr auto;gap:18px;align-items:start;padding:18px 0;border-top:1px solid var(--rule)}
        .fix-rule{width:3px;border-radius:3px;background:var(--accent,var(--brand));align-self:stretch;min-height:46px}
        .fix-meta{font-size:11px;letter-spacing:.09em;text-transform:uppercase;color:var(--ink-soft)}
        .fix-meta b{color:var(--accent,var(--brand));font-weight:700}
        .fix-title{font-weight:400;font-size:23px;line-height:1.12;margin:2px 0 5px}
        .fix-text{margin:0;color:var(--ink-soft);font-size:14px;max-width:62ch}
        .gain{padding-top:2px}
        .gain .delta{font-size:14px;white-space:nowrap}
        .boosts{margin-top:32px}
        .boost{display:grid;grid-template-columns:138px 1fr auto;gap:16px;align-items:baseline;padding:14px 0;border-top:1px solid var(--rule)}
        .boost-tag{font-size:11px;letter-spacing:.05em;font-weight:700;color:var(--ink-soft)}
        .boost-text{font-size:17px;line-height:1.3;color:var(--ink)}
        .boost-gain .delta{font-size:13px;white-space:nowrap}
      `}</style>
    </section>
  );
}
