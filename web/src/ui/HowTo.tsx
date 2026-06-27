"use client";
import { useEffect, useId, useState, type ReactNode } from "react";

/**
 * A small "how?" link that opens a modal with numbered, step-by-step
 * instructions. Reuses the shared .ha-overlay/.ha-modal/.ha-plist styles
 * (globals.css) so it matches the PrivacyChip dialog exactly.
 */
export function HowTo({
  eyebrow,
  title,
  steps,
  foot,
  label = "how?",
}: {
  eyebrow: string;
  title: string;
  steps: ReactNode[];
  foot?: string;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const titleId = useId();

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button
        type="button"
        className="ha-how"
        aria-haspopup="dialog"
        onClick={() => setOpen(true)}
      >
        {label}
      </button>
      {open && (
        <div
          className="ha-overlay"
          onClick={(e) => {
            if (e.target === e.currentTarget) setOpen(false);
          }}
        >
          <div className="ha-modal" role="dialog" aria-modal="true" aria-labelledby={titleId}>
            <button className="ha-modal-x" aria-label="Close" onClick={() => setOpen(false)}>
              ×
            </button>
            <div className="eyebrow">{eyebrow}</div>
            <h3 id={titleId} className="serif ha-modal-title">
              {title}
            </h3>
            <ul className="ha-plist">
              {steps.map((step, i) => (
                <li key={i}>
                  <span className="ha-pk mono">{String(i + 1).padStart(2, "0")}</span>
                  <span>{step}</span>
                </li>
              ))}
            </ul>
            {foot && <p className="ha-modal-foot mono">{foot}</p>}
          </div>
        </div>
      )}
    </>
  );
}
