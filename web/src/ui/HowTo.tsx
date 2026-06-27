"use client";
import { useEffect, useId, useState, type ReactNode } from "react";

/**
 * A modal with numbered, step-by-step instructions, opened by a trigger. The
 * default trigger is a small "how?" link; pass `trigger` to supply your own
 * (e.g. PrivacyChip's chip button) and reuse the whole dialog.
 */
export function HowTo({
  eyebrow,
  title,
  steps,
  foot,
  trigger,
}: {
  eyebrow: string;
  title: string;
  steps: ReactNode[];
  foot?: string;
  trigger?: (open: () => void) => ReactNode;
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
      {trigger ? (
        trigger(() => setOpen(true))
      ) : (
        <button
          type="button"
          className="ha-how"
          aria-haspopup="dialog"
          onClick={() => setOpen(true)}
        >
          how?
        </button>
      )}
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
