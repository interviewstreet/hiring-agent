"use client";
import { useTheme } from "./ThemeProvider";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      onClick={toggle}
      role="switch"
      aria-checked={theme === "dark"}
      aria-label="Toggle light or dark theme"
      title="Light / dark"
      className="ha-theme"
    >
      <svg aria-hidden="true" className="ha-ico ha-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
      <svg aria-hidden="true" className="ha-ico ha-moon" viewBox="0 0 24 24" fill="currentColor"><path d="M21 12.8A8.5 8.5 0 1 1 11.2 3a6.6 6.6 0 0 0 9.8 9.8z"/></svg>
      <span className="ha-knob" />
      <style>{`
        .ha-theme{position:relative;width:60px;height:28px;border-radius:999px;border:1px solid var(--rule);background:var(--panel-2);cursor:pointer;padding:0;flex:none}
        .ha-theme:focus-visible{outline:2px solid var(--brand);outline-offset:3px}
        .ha-ico{position:absolute;top:50%;transform:translateY(-50%);width:15px;height:15px;z-index:2}
        .ha-sun{left:7px;color:var(--warn)} .ha-moon{right:7px;color:var(--ink-soft)}
        .ha-knob{position:absolute;top:2px;left:2px;width:22px;height:22px;border-radius:50%;background:var(--panel);box-shadow:var(--shadow);transition:left .22s ease;z-index:1}
        [data-theme="dark"] .ha-knob{left:34px}
        [data-theme="dark"] .ha-moon{color:var(--brand-ink)} [data-theme="dark"] .ha-sun{color:var(--ink-soft)}
        @media (prefers-reduced-motion: reduce){ .ha-knob{transition:none} }
      `}</style>
    </button>
  );
}
