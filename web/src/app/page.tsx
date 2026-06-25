import { ThemeToggle } from "@/ui/ThemeToggle";
import { PrivacyChip } from "@/ui/PrivacyChip";

export default function Home() {
  return (
    <main style={{ maxWidth: 1080, margin: "0 auto", padding: "26px 28px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--rule)", paddingBottom: 20 }}>
        <div className="serif" style={{ fontSize: 26 }}>Hiring <i>Agent</i></div>
        <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
          <ThemeToggle />
          <PrivacyChip />
        </div>
      </div>
      <p className="eyebrow" style={{ marginTop: 24 }}>Scaffold + design system ready</p>
    </main>
  );
}
