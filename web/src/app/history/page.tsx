"use client";
import { AppShell } from "@/ui/AppShell";
import { HistoryScreen } from "@/ui/screens/HistoryScreen";

export default function Page() {
  return (
    <AppShell active="history">
      <HistoryScreen />
    </AppShell>
  );
}
