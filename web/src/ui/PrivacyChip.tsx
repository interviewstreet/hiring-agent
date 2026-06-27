"use client";
import { useEffect, useState } from "react";

export function PrivacyChip() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

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
        </div>
      )}
    </>
  );
}
