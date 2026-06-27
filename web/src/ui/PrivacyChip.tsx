"use client";
import { HowTo } from "./HowTo";

export function PrivacyChip() {
  return (
    <HowTo
      eyebrow="Privacy"
      title="Private by design — no server, no account."
      steps={[
        <>Everything runs in your browser. There&apos;s no backend of ours for your resume to pass through.</>,
        <>Scoring goes straight from your browser to Google Gemini with your own API key. We never see the key or the resume.</>,
        <>Your scores and past resumes are saved in this browser&apos;s local cache — not a database.</>,
        <>Clearing your browser data, or Settings → Clear all data, erases everything instantly.</>,
      ]}
      foot="No tracking · No sign-in · Works offline once loaded"
      trigger={(open) => (
        <button className="chip" aria-haspopup="dialog" onClick={open}>
          <span className="dot" />100% PRIVATE{" "}
          <span style={{ textDecoration: "underline", textUnderlineOffset: 2, opacity: 0.85 }}>how?</span>
        </button>
      )}
    />
  );
}
