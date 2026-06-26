"use client";
import { useRef, useState } from "react";

function firstPdf(list: FileList | null): File | null {
  if (!list) return null;
  for (const f of Array.from(list)) {
    if (f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")) return f;
  }
  return null;
}

export function Dropzone({
  onFile,
  onReject,
  disabled = false,
}: {
  onFile: (file: File) => void;
  onReject?: (reason: string) => void;
  disabled?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  function pick() {
    if (!disabled) inputRef.current?.click();
  }

  function accept(list: FileList | null) {
    const file = firstPdf(list);
    if (file) {
      onFile(file);
    } else if (list && list.length > 0) {
      onReject?.("Please choose a PDF file.");
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setOver(false);
    if (disabled) return;
    accept(e.dataTransfer.files);
  }

  return (
    <div
      className={`ha-dz${over ? " over" : ""}${disabled ? " off" : ""}`}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      aria-label="Upload a resume PDF"
      onClick={pick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          pick();
        }
      }}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setOver(true);
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node)) setOver(false);
      }}
      onDrop={onDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        hidden
        onChange={(e) => {
          accept(e.target.files);
          e.target.value = "";
        }}
      />
      <svg className="ha-dz-ico" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 16V4M7 9l5-5 5 5" />
        <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
      </svg>
      <div className="ha-dz-title serif">Drop your resume PDF</div>
      <div className="ha-dz-sub mono">or click to browse · stays in your browser</div>
      <style>{`
        .ha-dz{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;
          min-height:240px;padding:40px 24px;border:1.5px dashed var(--rule);border-radius:16px;
          background:var(--panel);color:var(--ink-soft);cursor:pointer;text-align:center;
          transition:border-color .18s ease,background .18s ease,transform .18s ease}
        .ha-dz:hover{border-color:var(--brand);background:var(--brand-tint)}
        .ha-dz.over{border-color:var(--brand);background:var(--brand-tint);transform:scale(1.005)}
        .ha-dz:focus-visible{outline:2px solid var(--brand);outline-offset:3px}
        .ha-dz.off{cursor:not-allowed;opacity:.55}
        .ha-dz.off:hover{border-color:var(--rule);background:var(--panel);transform:none}
        .ha-dz-ico{width:34px;height:34px;color:var(--brand-ink)}
        .ha-dz-title{font-size:22px;color:var(--ink)}
        .ha-dz-sub{font-size:12px;color:var(--ink-soft)}
        @media (prefers-reduced-motion: reduce){ .ha-dz{transition:none} .ha-dz.over{transform:none} }
      `}</style>
    </div>
  );
}
