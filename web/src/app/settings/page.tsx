"use client";
import { AppShell } from "@/ui/AppShell";
import { SettingsScreen } from "@/ui/screens/SettingsScreen";

export default function Page() {
  return (
    <AppShell active="settings">
      <SettingsScreen />
    </AppShell>
  );
}
