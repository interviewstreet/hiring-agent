"use client";
import Link from "next/link";
import { ThemeToggle } from "@/ui/ThemeToggle";
import { PrivacyChip } from "@/ui/PrivacyChip";

export function AppShell({
  active,
  children,
}: {
  active: "score" | "history" | "settings";
  children: React.ReactNode;
}) {
  return (
    <div className="wrap">
      <header className="top">
        <div className="mark">
          Hiring <i>Agent</i>
        </div>
        <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
          <nav className="nav" aria-label="Primary">
            <Link
              href="/"
              className={active === "score" ? "on" : undefined}
              aria-current={active === "score" ? "page" : undefined}
            >
              Score
            </Link>
            <Link
              href="/history"
              className={active === "history" ? "on" : undefined}
              aria-current={active === "history" ? "page" : undefined}
            >
              History &amp; Trends
            </Link>
            <Link
              href="/settings"
              className={active === "settings" ? "on" : undefined}
              aria-current={active === "settings" ? "page" : undefined}
            >
              Settings
            </Link>
          </nav>
          <ThemeToggle />
          <PrivacyChip />
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
}
