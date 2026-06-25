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
      <div className="top">
        <div className="mark serif">
          Hiring <b>Agent</b>
        </div>
        <div className="nav">
          <Link href="/" className={active === "score" ? "on" : undefined}>
            Score
          </Link>
          <Link href="/history" className={active === "history" ? "on" : undefined}>
            History &amp; Trends
          </Link>
          <Link href="/settings" className={active === "settings" ? "on" : undefined}>
            Settings
          </Link>
          <ThemeToggle />
          <PrivacyChip />
        </div>
      </div>
      <main>{children}</main>
    </div>
  );
}
