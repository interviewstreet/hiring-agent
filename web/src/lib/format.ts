/** Shared date/time formatting. en-US to match the rest of the UI. */
export function shortDate(ts: number): string {
  return new Date(ts).toLocaleDateString("en-US", { month: "short", day: "2-digit" });
}

export function dateTime(ts: number): string {
  const time = new Date(ts).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
  return `${shortDate(ts)} · ${time}`;
}
