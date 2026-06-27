"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { StoredSettings } from "../../lib/schemas";
import { DEFAULT_MODEL, GEMINI_MODELS } from "../../lib/gemini";
import { clearAllData } from "../../lib/settings";
import { useSettings } from "../SettingsProvider";
import { ThemeToggle } from "../ThemeToggle";
import { HowTo } from "../HowTo";

export function SettingsScreen() {
  const { settings, update, reset } = useSettings();
  const [saved, setSaved] = useState(false);
  const [cleared, setCleared] = useState(false);
  const [busy, setBusy] = useState(false);
  const savedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear the pending "Saved" timer if we unmount before it fires.
  useEffect(() => () => {
    if (savedTimer.current) clearTimeout(savedTimer.current);
  }, []);

  const edit = useCallback(
    (patch: Partial<StoredSettings>) => {
      update(patch);
      setSaved(true);
      setCleared(false);
      if (savedTimer.current) clearTimeout(savedTimer.current);
      savedTimer.current = setTimeout(() => setSaved(false), 1600);
    },
    [update]
  );

  const onClear = useCallback(async () => {
    const ok = window.confirm(
      "Erase all saved runs, resumes, and settings from this browser? This cannot be undone."
    );
    if (!ok) return;
    setBusy(true);
    try {
      await clearAllData();
      reset();
      setCleared(true);
    } finally {
      setBusy(false);
    }
  }, [reset]);

  return (
    <section className="ha-settings">
      <header className="ha-set-head">
        <div className="eyebrow">Settings</div>
        <h1 className="serif ha-set-title">Keys, privacy &amp; appearance.</h1>
        <p className="ha-set-sub">
          Everything below is stored only in this browser. Nothing is sent to a server of ours.
        </p>
      </header>

      <div className="ha-card">
        <label className="ha-field" htmlFor="ha-gemini-key">
          <span className="ha-flabel">
            Gemini API key <span className="ha-req">required</span>
            <HowTo
              eyebrow="Gemini API key"
              title="Get a Gemini API key in about a minute."
              steps={[
                <>
                  Open{" "}
                  <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer">
                    aistudio.google.com/apikey
                  </a>{" "}
                  and sign in with your Google account.
                </>,
                <>Click <b>Create API key</b>, then pick (or let it create) a Google Cloud project.</>,
                <>Copy the generated key — it begins with <code>AIza…</code>.</>,
                <>Paste it into the field here. It is stored only in this browser.</>,
              ]}
              foot="Free tier available · the key is sent only to Google, never to us"
            />
          </span>
          <input
            id="ha-gemini-key"
            type="password"
            className="ha-input mono"
            placeholder="AIza…"
            autoComplete="off"
            spellCheck={false}
            value={settings.geminiKey}
            onChange={(e) => edit({ geminiKey: e.target.value })}
          />
          <span className="ha-hint">
            Scoring calls Google Gemini directly from your browser with this key. Create one at
            aistudio.google.com — it never leaves this device.
          </span>
        </label>

        <label className="ha-field" htmlFor="ha-github-token">
          <span className="ha-flabel">
            GitHub token <span className="ha-opt">optional</span>
            <HowTo
              eyebrow="GitHub token · permissions"
              title="Create a read-only GitHub token."
              steps={[
                <>
                  Go to{" "}
                  <a
                    href="https://github.com/settings/tokens?type=beta"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Settings → Developer settings → Personal access tokens
                  </a>
                  .
                </>,
                <>
                  This app reads only <b>public</b> profile and repository data, so it needs no
                  private scopes. For a fine-grained token, set <b>Repository access</b> to
                  {" "}
                  <b>Public repositories (read-only)</b> and add no account permissions.
                </>,
                <>
                  A classic token works too — leave every scope <b>unchecked</b> (or tick only{" "}
                  <code>public_repo</code>). The token just lifts the rate limit from 60 to 5,000
                  requests/hour.
                </>,
                <>Generate it, copy the value (classic tokens start with <code>ghp_…</code>), and paste it here.</>,
              ]}
              foot="Optional · used only when GitHub enrichment is on"
            />
          </span>
          <input
            id="ha-github-token"
            type="password"
            className="ha-input mono"
            placeholder="ghp_…"
            autoComplete="off"
            spellCheck={false}
            value={settings.githubToken}
            onChange={(e) => edit({ githubToken: e.target.value })}
          />
          <span className="ha-hint">
            Lets the scorer read your public GitHub signal and raises the rate limit from 60 to
            5,000 requests/hour. Used only when GitHub enrichment is on.
          </span>
        </label>

        <div className="ha-row">
          <div className="ha-row-text">
            <span className="ha-flabel">GitHub enrichment</span>
            <span className="ha-hint">Pull repositories and contributions into the score.</span>
          </div>
          <input
            type="checkbox"
            className="ha-check"
            role="switch"
            aria-label="Enable GitHub enrichment"
            checked={settings.enableGitHub}
            onChange={(e) => edit({ enableGitHub: e.target.checked })}
          />
        </div>

        <label className="ha-field" htmlFor="ha-model">
          <span className="ha-flabel">
            Model <span className="ha-opt">optional</span>
          </span>
          <select
            id="ha-model"
            className="ha-select mono"
            value={settings.model}
            onChange={(e) => edit({ model: e.target.value })}
          >
            {/* Round-trip a previously-saved model that isn't on the list. */}
            {!GEMINI_MODELS.some((m) => m.id === settings.model) && (
              <option value={settings.model}>{settings.model}</option>
            )}
            {GEMINI_MODELS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
          <span className="ha-hint">Defaults to {DEFAULT_MODEL}. All options support JSON output.</span>
        </label>
      </div>

      <div className="ha-card">
        <div className="ha-row">
          <div className="ha-row-text">
            <span className="ha-flabel">Remember keys on this device</span>
            <span className="ha-hint" id="ha-remember-hint">
              {settings.rememberKeys
                ? "Keys are saved in this browser's localStorage so you don't re-enter them."
                : "Keys are kept only for this session (in memory) and cleared when you close the tab."}
            </span>
          </div>
          <input
            type="checkbox"
            className="ha-check"
            role="switch"
            aria-label="Remember keys on this device"
            aria-describedby="ha-remember-hint"
            checked={settings.rememberKeys}
            onChange={(e) => edit({ rememberKeys: e.target.checked })}
          />
        </div>

        <div className="ha-row">
          <div className="ha-row-text">
            <span className="ha-flabel">Theme</span>
            <span className="ha-hint">Light or dark. Saved on this device.</span>
          </div>
          <ThemeToggle />
        </div>
      </div>

      <div className="ha-card ha-danger">
        <div className="ha-row">
          <div className="ha-row-text">
            <span className="ha-flabel">Clear all data</span>
            <span className="ha-hint">
              Erase every saved run, resume, and setting from this browser. Your theme is kept.
            </span>
          </div>
          <button type="button" className="ha-btn-danger" onClick={onClear} disabled={busy}>
            {busy ? "Clearing…" : "Clear all data"}
          </button>
        </div>
        <p className="ha-cleared mono" role="status" aria-live="polite">
          {cleared ? "✓ All data cleared." : ""}
        </p>
      </div>

      <div className="ha-saved mono" aria-live="polite">
        {saved ? "✓ Saved" : ""}
      </div>

      <style>{`
        .ha-settings{display:flex;flex-direction:column;gap:18px;max-width:680px;margin:0 auto;padding:8px 0 40px}
        .ha-set-head{display:flex;flex-direction:column;gap:6px}
        .ha-set-title{font-weight:400;font-size:34px;line-height:1.1;margin:2px 0 0}
        .ha-set-sub{margin:0;font-size:14px;color:var(--ink-soft);line-height:1.5}
        .ha-card{background:var(--panel);border:1px solid var(--rule);border-radius:14px;padding:20px;display:flex;flex-direction:column;gap:20px;box-shadow:var(--shadow)}
        .ha-field{display:flex;flex-direction:column;gap:7px}
        .ha-flabel{font-size:13.5px;font-weight:600;color:var(--ink);display:flex;align-items:center;gap:8px}
        .ha-req{font-size:11px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--bad);background:var(--bad-tint);border-radius:999px;padding:2px 8px}
        .ha-opt{font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--ink-soft);background:var(--panel-2);border-radius:999px;padding:2px 8px}
        .ha-input{width:100%;box-sizing:border-box;background:var(--panel-2);border:1px solid var(--rule);border-radius:10px;padding:11px 13px;font-size:14px;color:var(--ink)}
        .ha-input::placeholder{color:var(--ink-soft);opacity:.7}
        .ha-input:focus-visible{outline:2px solid var(--brand);outline-offset:2px;border-color:var(--brand)}
        .ha-select{width:100%;box-sizing:border-box;background:var(--panel-2);border:1px solid var(--rule);border-radius:10px;padding:11px 36px 11px 13px;font-size:14px;color:var(--ink);cursor:pointer;appearance:none;-webkit-appearance:none;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 12'><path d='M2 4l4 4 4-4' fill='none' stroke='%238A93A3' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/></svg>");background-repeat:no-repeat;background-position:right 13px center;background-size:12px}
        .ha-select:focus-visible{outline:2px solid var(--brand);outline-offset:2px;border-color:var(--brand)}
        .ha-hint{font-size:12.5px;color:var(--ink-soft);line-height:1.5}
        .ha-row{display:flex;align-items:flex-start;justify-content:space-between;gap:18px}
        .ha-row-text{display:flex;flex-direction:column;gap:5px;flex:1}
        .ha-check{appearance:none;-webkit-appearance:none;position:relative;width:46px;height:26px;border-radius:999px;border:1px solid var(--rule);background:var(--panel-2);cursor:pointer;flex:none;margin-top:2px;transition:background .18s ease}
        .ha-check::after{content:"";position:absolute;top:2px;left:2px;width:20px;height:20px;border-radius:50%;background:var(--panel);box-shadow:var(--shadow);transition:left .18s ease}
        .ha-check:checked{background:var(--brand)}
        .ha-check:checked::after{left:22px}
        .ha-check:focus-visible{outline:2px solid var(--brand);outline-offset:3px}
        .ha-danger{border-color:var(--bad-tint)}
        .ha-btn-danger{flex:none;background:var(--bad-tint);color:var(--bad);border:1px solid var(--bad);border-radius:10px;padding:9px 15px;font-size:13px;font-weight:600;cursor:pointer}
        .ha-btn-danger:hover{background:var(--bad);color:var(--paper)}
        .ha-btn-danger:focus-visible{outline:2px solid var(--bad);outline-offset:3px}
        .ha-cleared{margin:0;font-size:12.5px;color:var(--good)}
        .ha-saved{min-height:18px;font-size:12.5px;color:var(--good);text-align:right;transition:opacity .2s ease}
        @media (prefers-reduced-motion: reduce){
          .ha-check,.ha-check::after,.ha-saved{transition:none}
        }
        @media (max-width:560px){
          .ha-set-title{font-size:28px}
          .ha-card{padding:16px}
        }
      `}</style>
    </section>
  );
}
