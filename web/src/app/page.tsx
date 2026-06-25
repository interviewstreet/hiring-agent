"use client";
import { useState } from "react";
import { ThemeToggle } from "@/ui/ThemeToggle";
import { PrivacyChip } from "@/ui/PrivacyChip";
import { runScoreWithRealDeps } from "@/lib/runScore";
import { DEFAULT_MODEL } from "@/lib/gemini";

export default function Home() {
  const [key, setKey] = useState("");
  const [out, setOut] = useState<string>("");
  const [status, setStatus] = useState("");

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setOut(""); setStatus("starting…");
    try {
      const rec = await runScoreWithRealDeps(file, { geminiKey: key, githubToken: null, model: DEFAULT_MODEL, enableGitHub: false }, setStatus);
      setOut(JSON.stringify({ total: rec.evaluation.scores, coach: rec.coach.verdict }, null, 2));
      setStatus("done");
    } catch (err) {
      setStatus("error: " + (err as Error).message);
    }
  }

  return (
    <main style={{ maxWidth: 1080, margin: "0 auto", padding: "26px 28px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--rule)", paddingBottom: 20 }}>
        <div className="serif" style={{ fontSize: 26 }}>Hiring <i>Agent</i></div>
        <div style={{ display: "flex", gap: 20, alignItems: "center" }}><ThemeToggle /><PrivacyChip /></div>
      </div>
      <p className="eyebrow" style={{ marginTop: 24 }}>Dev harness (replaced by real screens in Part 2)</p>
      <input className="mono" placeholder="Gemini API key" value={key} onChange={(e) => setKey(e.target.value)} style={{ display: "block", width: 360, padding: 8, marginTop: 12 }} />
      <input type="file" accept="application/pdf" onChange={onFile} style={{ marginTop: 12 }} />
      <p className="mono" style={{ marginTop: 12, color: "var(--ink-soft)" }}>{status}</p>
      <pre className="mono" style={{ whiteSpace: "pre-wrap", marginTop: 12 }}>{out}</pre>
    </main>
  );
}
