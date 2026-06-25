"use client";
import { useEffect, useState } from "react";

export function PrivacyChip() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  return (
    <>
      <button className="chip" aria-haspopup="dialog" onClick={() => setOpen(true)}>
        <span className="dot" />100% PRIVATE <span style={{ textDecoration: "underline", textUnderlineOffset: 2, opacity: 0.85 }}>how?</span>
      </button>
      {open && (
        <div className="ha-overlay" onClick={(e) => { if (e.target === e.currentTarget) setOpen(false); }}>
          <div className="ha-modal" role="dialog" aria-modal="true" aria-labelledby="ha-privacy-title">
            <button className="ha-modal-x" aria-label="Close" onClick={() => setOpen(false)}>×</button>
            <div className="eyebrow">Privacy</div>
            <h3 id="ha-privacy-title" className="serif ha-modal-title">Private by design — no server, no account.</h3>
            <ul className="ha-plist">
              <li><span className="ha-pk mono">01</span><span>Everything runs in your browser. There&apos;s no backend of ours for your resume to pass through.</span></li>
              <li><span className="ha-pk mono">02</span><span>Scoring goes straight from your browser to Google Gemini with your own API key. We never see the key or the resume.</span></li>
              <li><span className="ha-pk mono">03</span><span>Your scores and past resumes are saved in this browser&apos;s local cache — not a database.</span></li>
              <li><span className="ha-pk mono">04</span><span>Clearing your browser data, or Settings → Clear all data, erases everything instantly.</span></li>
            </ul>
            <p className="ha-modal-foot mono">No tracking · No sign-in · Works offline once loaded</p>
          </div>
          <style>{`
            .ha-overlay{position:fixed;inset:0;background:rgba(10,12,18,.55);backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center;padding:24px;z-index:50}
            .ha-modal{background:var(--panel);border:1px solid var(--rule);border-radius:16px;max-width:460px;width:100%;padding:26px 26px 22px;box-shadow:0 24px 60px rgba(0,0,0,.35);position:relative}
            .ha-modal-x{position:absolute;top:14px;right:14px;border:none;background:transparent;color:var(--ink-soft);font-size:22px;line-height:1;cursor:pointer;padding:4px}
            .ha-modal-title{font-weight:400;font-size:27px;line-height:1.12;margin:8px 0 14px}
            .ha-plist{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:12px}
            .ha-plist li{display:grid;grid-template-columns:18px 1fr;gap:11px;font-size:14px;color:var(--ink);line-height:1.5}
            .ha-pk{color:var(--good);font-weight:700}
            .ha-modal-foot{margin:16px 0 0;padding-top:14px;border-top:1px solid var(--rule);font-size:12.5px;color:var(--ink-soft);letter-spacing:.02em}
          `}</style>
        </div>
      )}
    </>
  );
}
