"use client";
import { Suspense } from "react";
import { AppShell } from "@/ui/AppShell";
import { ResultsScreen } from "@/ui/screens/ResultsScreen";

export default function Page() {
  return (
    <AppShell active="score">
      <Suspense fallback={<p className="eyebrow">Loading…</p>}>
        <ResultsScreen />
      </Suspense>
    </AppShell>
  );
}
